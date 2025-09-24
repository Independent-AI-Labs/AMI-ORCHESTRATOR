#!/usr/bin/env python
"""AMI Orchestrator (root) module setup.

Goals:
- Treat root like any other module: its own .venv, configs, hooks
- Delegate to base/module_setup.py (stdlib only)
- Optionally replicate critical configs from base/templates for root
"""

from __future__ import annotations

import argparse
import difflib
import importlib
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
SUBMODULES = [
    "base",
    "browser",
    "compliance",
    "domains",
    "files",
    "nodes",
    "streams",
    "ux",
]


def _dotenv_values(path: Path) -> dict[str, str]:
    """Return key/value pairs from a .env file using python-dotenv if available."""
    if not path.exists():
        return {}
    try:
        dotenv_module = importlib.import_module("dotenv")
        loader = getattr(dotenv_module, "dotenv_values", None)
        if callable(loader):
            try:
                values = loader(path)
                return {k: v for k, v in values.items() if isinstance(k, str) and isinstance(v, str)}
            except Exception as exc:  # noqa: BLE001 - fall back to manual parsing
                logger.debug("dotenv loader failed (%s); falling back to manual parser", exc)
    except ModuleNotFoundError:
        pass

    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            data[key] = value
    return data


def _resolve_sudo_password() -> str | None:
    """Resolve sudo password from env or .env files.

    Priority: explicit env vars, then browser/.env, then root .env.
    """
    for key in ("SUDO_PASS", "SUDO_PASSWORD"):
        direct = os.environ.get(key)
        if direct:
            return direct

    browser_env = _dotenv_values(ROOT / "browser" / ".env")
    for key in ("SUDO_PASS", "SUDO_PASSWORD"):
        if key in browser_env and browser_env[key]:
            return browser_env[key]

    root_env = _dotenv_values(ROOT / ".env")
    for key in ("SUDO_PASS", "SUDO_PASSWORD"):
        if key in root_env and root_env[key]:
            return root_env[key]

    return None


def _run(cmd: list[str], cwd: Path | None = None, check: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command with text output, returning the CompletedProcess.

    Logs the command for transparency. Does not raise unless check=True.
    """
    where = str(cwd or ROOT)
    logger.info("$ %s (cwd=%s)", " ".join(cmd), where)
    return subprocess.run(cmd, cwd=where, text=True, capture_output=True, check=check, env=env)


def _submodules_from_gitmodules() -> list[tuple[str, str]]:
    """Return list of (path, url) from .gitmodules if present."""
    gm = ROOT / ".gitmodules"
    if not gm.exists():
        return []
    path: str | None = None
    url: str | None = None
    results: list[tuple[str, str]] = []
    for raw_line in gm.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("[submodule "):
            if path and url:
                results.append((path, url))
            path, url = None, None
        elif line.startswith("path = "):
            path = line.split("=", 1)[1].strip()
        elif line.startswith("url = "):
            url = line.split("=", 1)[1].strip()
    if path and url:
        results.append((path, url))
    return results


def _to_https(url: str) -> str:
    """Convert SSH GitHub URL to HTTPS if applicable."""
    if url.startswith("git@github.com:"):
        return "https://github.com/" + url.split(":", 1)[1]
    return url


def ensure_git_submodules() -> None:
    """Initialize and update git submodules, retrying via HTTPS if SSH fails.

    This modifies submodule remote URLs in local git config if SSH auth fails,
    but does not edit .gitmodules on disk.
    """
    if not (ROOT / ".git").exists():
        logger.warning("No .git directory found; skipping submodule init.")
        return

    logger.info("Initializing git submodules (recursive)…")
    res = _run(["git", "submodule", "update", "--init", "--recursive"])
    if res.returncode == 0:
        logger.info("Submodules are initialized.")
        return

    stderr = res.stderr or ""
    if "Permission denied (publickey)" in stderr or "fatal: Could not read from remote repository" in stderr:
        logger.warning("SSH auth failed for submodules; attempting HTTPS fallback.")
        subs = _submodules_from_gitmodules()
        changed = False
        for path, url in subs:
            https_url = _to_https(url)
            if https_url == url:
                continue
            _run(["git", "submodule", "set-url", path, https_url])
            changed = True
        if changed:
            _run(["git", "submodule", "sync", "--recursive"])  # sync local config
        # Retry update
        res2 = _run(["git", "submodule", "update", "--init", "--recursive"])
        if res2.returncode == 0:
            logger.info("Submodules initialized via HTTPS.")
            return
        logger.error("Submodule init still failing. stderr=\n%s", res2.stderr)
        return

    # Other failure: surface stderr for clarity
    if res.stderr:
        logger.error("Submodule init failed:\n%s", res.stderr)
    else:
        logger.error("Submodule init failed with exit code %s", res.returncode)


def check_uv() -> bool:
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        logger.warning("uv is not installed or not on PATH. Attempting bootstrap…")
        bootstrap = ROOT / "scripts" / "bootstrap_uv_python.py"
        if not bootstrap.exists():
            logger.error("Missing scripts/bootstrap_uv_python.py. Please install uv manually: https://docs.astral.sh/uv/")
            return False
        # Best-effort bootstrap (user-local install); do not raise on failure
        subprocess.run([sys.executable, str(bootstrap), "--auto", "--only-uv"], check=False)
        try:
            subprocess.run(["uv", "--version"], capture_output=True, check=True)
            logger.info("uv installed successfully.")
            return True
        except Exception:
            # Also try common install locations in case PATH wasn't updated yet
            for cand in ("~/.cargo/bin/uv", "~/.local/bin/uv"):
                cand_path = str(Path(cand).expanduser())
                try:
                    subprocess.run([cand_path, "--version"], capture_output=True, check=True)
                    os.environ["PATH"] = f"{str(Path(cand_path).parent)}{os.pathsep}" + os.environ.get("PATH", "")
                    logger.info(f"uv found at {cand_path} and added to PATH for this process.")
                    return True
                except Exception as exc:
                    logger.debug("uv probe failed at %s: %s", cand_path, exc)
                    continue
            logger.error("Failed to install uv automatically. See https://docs.astral.sh/uv/ for manual installation.")
            return False


def ensure_uv_python(version: str = "3.12") -> None:
    find = subprocess.run(["uv", "python", "find", version], capture_output=True, text=True, check=False)
    if find.returncode != 0 or not find.stdout.strip():
        logger.info(f"Installing Python {version} toolchain via uv...")
        subprocess.run(["uv", "python", "install", version], check=False)


def call_base_setup(project_name: str) -> int:
    base_setup = ROOT / "base" / "module_setup.py"
    if not base_setup.exists():
        logger.error("Cannot find base/module_setup.py")
        return 1
    cmd = [sys.executable, str(base_setup), "--project-dir", str(ROOT), "--project-name", project_name]
    logger.info("Delegating to base/module_setup.py …")
    result = subprocess.run(cmd, check=False)
    return result.returncode


def _mypy_entry_for(module_name: str, is_root: bool) -> str:
    is_windows = platform.system().lower().startswith("win")
    if is_root or module_name == "base":
        # Running hooks at the module root itself
        if is_windows:
            return ".venv/Scripts/python.exe -m mypy backend --config-file=mypy.ini"
        return ".venv/bin/python -m mypy backend --config-file=mypy.ini"
    # Determine target directory to type-check
    module_root = ROOT / module_name
    if (module_root / "backend").exists():
        target = f"{module_name}/backend"
    elif (module_root / "scripts").exists():
        target = f"{module_name}/scripts"
    else:
        # Fall back to module root; mypy.ini `files` will constrain scope
        target = module_name
    # For submodules, hooks may run from the superproject parent
    if is_windows:
        target_win = target.replace("/", "\\")
        inner = f"cd .. && {module_name}\\.venv\\Scripts\\python.exe -m mypy " f"{target_win} --config-file={module_name}\\mypy.ini"
        return f'cmd /c "{inner}"'
    return f"bash -lc 'cd .. && {module_name}/.venv/bin/python -m mypy {target} --config-file={module_name}/mypy.ini'"


def replicate_configs_from_base() -> None:
    base_configs = ROOT / "base" / "configs"
    if not base_configs.exists():
        logger.warning("base/configs not found; skipping config replication")
        return

    module_name = ROOT.name
    is_root = True

    # 1) Generate mypy.ini from template
    pyver_file = ROOT / "python.ver"
    python_version = pyver_file.read_text(encoding="utf-8").strip() if pyver_file.exists() else "3.12"
    template_file = base_configs / "mypy.ini.template"
    if template_file.exists():
        content = template_file.read_text(encoding="utf-8")
        content = content.replace("{{PYTHON_VERSION}}", python_version)
        # Root needs access to all submodules for cross-module imports
        path_sep = os.pathsep
        mypy_roots = SUBMODULES + ["."]
        mypy_path = path_sep.join(mypy_roots)
        content = content.replace("{{MYPY_PATH}}", mypy_path)
        (ROOT / "mypy.ini").write_text(content, encoding="utf-8")
        logger.info("Generated mypy.ini from base template")
    else:
        logger.warning("mypy.ini.template not found; skipping mypy.ini generation")

    # 2) Copy platform-specific pre-commit config and fill placeholders
    source_cfg = base_configs / ".pre-commit-config.win.yaml" if platform.system().lower().startswith("win") else base_configs / ".pre-commit-config.unix.yaml"

    if source_cfg.exists():
        cfg = source_cfg.read_text(encoding="utf-8")
        cfg = cfg.replace("{{MODULE_NAME}}", module_name)
        cfg = cfg.replace("{{MYPY_ENTRY}}", _mypy_entry_for(module_name, is_root))
        # Ensure tests run inside uv environment at root
        cfg = cfg.replace("entry: python scripts/run_tests.py", "entry: uv run python scripts/run_tests.py")
        (ROOT / ".pre-commit-config.yaml").write_text(cfg, encoding="utf-8")
        logger.info("Wrote .pre-commit-config.yaml from base template")
    else:
        logger.warning("pre-commit config templates not found; skipping pre-commit config")


def _expected_configs_for_module(module_path: Path) -> tuple[str | None, str | None]:
    """Render expected pre-commit config and mypy.ini for a given module using base templates.

    Returns (precommit_text, mypy_text) where either may be None if template missing.
    """
    base_configs = ROOT / "base" / "configs"
    if not base_configs.exists():
        return None, None

    module_name = module_path.name
    # python.ver
    pyver_file = module_path / "python.ver"
    python_version = pyver_file.read_text(encoding="utf-8").strip() if pyver_file.exists() else "3.12"

    # mypy.ini
    mypy_expected = None
    mypy_tpl = base_configs / "mypy.ini.template"
    if mypy_tpl.exists():
        content = mypy_tpl.read_text(encoding="utf-8")
        content = content.replace("{{PYTHON_VERSION}}", python_version)
        # Avoid adding the whole superproject to mypy_path to prevent
        # duplicate module discovery (e.g., backend.* vs <module>.backend.*).
        # For modules that import base, include only ../base plus current dir.
        path_sep = os.pathsep
        mypy_path = "." if module_name == "base" else f"..{os.sep}base{path_sep}."
        # If module lacks backend but has scripts, adjust files target
        if not (module_path / "backend").exists() and (module_path / "scripts").exists():
            content = content.replace("files = backend/", "files = scripts/")
        content = content.replace("{{MYPY_PATH}}", mypy_path)
        mypy_expected = content

    # pre-commit
    pre_expected = None
    src = base_configs / ".pre-commit-config.win.yaml" if platform.system().lower().startswith("win") else base_configs / ".pre-commit-config.unix.yaml"
    if src.exists():
        cfg = src.read_text(encoding="utf-8")
        cfg = cfg.replace("{{MODULE_NAME}}", module_name)
        cfg = cfg.replace("{{MYPY_ENTRY}}", _mypy_entry_for(module_name, is_root=False))
        pre_expected = cfg

    return pre_expected, mypy_expected


def _show_and_optionally_write(current: str, expected: str, path: Path, label: str, apply: bool) -> bool:
    if current == expected:
        return False
    logger.info(label)
    for line in difflib.unified_diff(current.splitlines(), expected.splitlines(), fromfile="current", tofile="expected", lineterm=""):
        logger.debug(line)
    if apply:
        path.write_text(expected, encoding="utf-8")
        logger.info(f"  applied update to {path}")
    return True


def audit_and_optionally_apply_configs(apply: bool = False) -> None:
    """Audit submodule configs vs base templates, optionally apply updates.

    This does NOT modify submodules unless apply=True is explicitly passed.
    """
    logger.info("\nConfig drift audit (vs base/configs):")
    for name in SUBMODULES:
        module_path = ROOT / name
        if not module_path.exists():
            logger.info(f"- {name}: missing (skipped)")
            continue
        pre_expected, mypy_expected = _expected_configs_for_module(module_path)
        pre_path = module_path / ".pre-commit-config.yaml"
        mypy_path = module_path / "mypy.ini"

        drift = False
        if pre_expected is not None:
            current = pre_path.read_text(encoding="utf-8") if pre_path.exists() else ""
            drift |= _show_and_optionally_write(current, pre_expected, pre_path, f"- {name}: .pre-commit-config.yaml differs", apply)

        if mypy_expected is not None:
            current = mypy_path.read_text(encoding="utf-8") if mypy_path.exists() else ""
            drift |= _show_and_optionally_write(current, mypy_expected, mypy_path, f"- {name}: mypy.ini differs", apply)

        if not drift:
            logger.info(f"- {name}: in sync")


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up root Orchestrator module")
    parser.add_argument("--project-name", type=str, default="Orchestrator")
    parser.add_argument("--audit-configs", action="store_true", help="Audit submodule configs vs. base templates (dry-run)")
    parser.add_argument("--apply-configs", action="store_true", help="Apply base templates to submodules (destructive; not run without explicit ask)")
    parser.add_argument(
        "--propagate-configs",
        action="store_true",
        help="Replicate root config templates from base (combine with --apply-configs for submodules)",
    )
    args = parser.parse_args()

    # Ensure submodules are present before any delegation
    ensure_git_submodules()

    if not check_uv():
        return 1
    ensure_uv_python("3.12")

    # Delegate to Base to create venv and sync deps (if any)
    rc = call_base_setup(args.project_name)
    if rc != 0:
        return rc

    if args.propagate_configs:
        logger.info("Propagating root config templates from base …")
        replicate_configs_from_base()
    else:
        logger.info("Root config propagation disabled; run with --propagate-configs to update templates.")

    # Best-effort install of headless Chrome runtime deps for Browser module on Unix.
    # This is a convenience step; failures are non-fatal.
    try:
        browser_dir = ROOT / "browser"
        install_script = browser_dir / "scripts" / "install_chrome_deps.sh"
        if install_script.exists() and os.name == "posix":
            logger.info("Attempting to install Browser headless Chrome runtime dependencies…")
            env = {**os.environ}
            sudo_pass = _resolve_sudo_password()
            if sudo_pass:
                env.setdefault("SUDO_PASS", sudo_pass)
                env["SUDO_PASSWORD"] = sudo_pass
                logger.info("Using SUDO_PASS value from environment or .env file for Browser setup.")
            else:
                env.setdefault("SUDO_PASSWORD", "docker")
                logger.info("No SUDO_PASS found; defaulting Browser setup sudo password to 'docker'.")
            res = _run(["bash", str(install_script)], cwd=browser_dir, env=env)
            if res.returncode == 0:
                logger.info("Browser runtime dependencies installed (or already present).")
            else:
                logger.warning("Browser deps installer exited with %s.\nstdout:\n%s\nstderr:\n%s", res.returncode, res.stdout, res.stderr)
        else:
            logger.info("Skipping Browser deps install (non-posix or script missing).")
    except Exception as exc:
        logger.warning("Browser deps install step skipped due to error: %s", exc)

    if args.audit_configs or args.apply_configs:
        audit_and_optionally_apply_configs(apply=args.apply_configs)

    logger.info("Root module setup complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
