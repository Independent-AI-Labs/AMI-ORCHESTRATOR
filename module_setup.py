#!/usr/bin/env python
"""AMI Orchestrator (root) module setup.

Goals:
- Treat root like any other module: its own .venv, configs, hooks
- Delegate to base/module_setup.py (stdlib only)
- Replicate critical configs from base/templates for root
"""

from __future__ import annotations

import argparse
import difflib
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
    "node",
    "streams",
    "ux",
]


def check_uv() -> bool:
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        logger.error("uv is not installed or not on PATH.")
        logger.info("Install uv: https://docs.astral.sh/uv/")
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
    # For submodules, hooks may run from the superproject parent
    if is_windows:
        inner = (
            f"cd .. && if exist {module_name}\\backend "
            f"( {module_name}\\.venv\\Scripts\\python.exe -m mypy "
            f"{module_name}\\backend --config-file={module_name}\\mypy.ini ) "
            f"else ( echo skip-mypy )"
        )
        return f'cmd /c "{inner}"'
    return (
        f"bash -lc 'cd .. && if [ -d {module_name}/backend ]; then "
        f"{module_name}/.venv/bin/python -m mypy {module_name}/backend --config-file={module_name}/mypy.ini; "
        f"else echo skip-mypy; fi'"
    )


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
    args = parser.parse_args()

    if not check_uv():
        return 1
    ensure_uv_python("3.12")

    # Delegate to Base to create venv and sync deps (if any)
    rc = call_base_setup(args.project_name)
    if rc != 0:
        return rc

    # Replicate configs for root from base templates
    replicate_configs_from_base()

    if args.audit_configs or args.apply_configs:
        audit_and_optionally_apply_configs(apply=args.apply_configs)

    logger.info("Root module setup complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
