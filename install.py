#!/usr/bin/env python3
"""AMI Orchestrator installer - bootstraps the development environment.

This script handles one-time setup tasks:
1. Initialize git submodules (with HTTPS fallback)
2. Register ami-run and ami-uv shell aliases
3. Delegate to module_setup.py for recursive venv creation

Run this once to set up the entire orchestrator.
For updates, run module_setup.py directly.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent


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


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command with text output."""
    logger.info("$ %s", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def ensure_git_submodules() -> bool:
    """Initialize and update git submodules, retrying via HTTPS if SSH fails."""
    if not (ROOT / ".git").exists():
        logger.warning("No .git directory found; skipping submodule init.")
        return True

    logger.info("Initializing git submodules (recursive)...")
    res = _run(["git", "submodule", "update", "--init", "--recursive"])
    if res.returncode == 0:
        logger.info("✓ Submodules initialized")
        return True

    stderr = res.stderr or ""
    if "Permission denied (publickey)" in stderr or "fatal: Could not read from remote repository" in stderr:
        logger.warning("SSH auth failed for submodules; attempting HTTPS alternative...")
        subs = _submodules_from_gitmodules()
        changed = False
        for path, url in subs:
            https_url = _to_https(url)
            if https_url == url:
                continue
            _run(["git", "submodule", "set-url", path, https_url])
            changed = True
        if changed:
            _run(["git", "submodule", "sync", "--recursive"])
        # Retry update
        res2 = _run(["git", "submodule", "update", "--init", "--recursive"])
        if res2.returncode == 0:
            logger.info("✓ Submodules initialized via HTTPS")
            return True
        logger.error("Submodule init failed:\n%s", res2.stderr)
        return False

    logger.error("Submodule init failed:\n%s", res.stderr)
    return False


def _find_shell_configs() -> list[tuple[str, Path]]:
    """Return list of (name, path) for existing shell config files."""
    shells = []
    bashrc = Path.home() / ".bashrc"
    if bashrc.exists():
        shells.append(("bashrc", bashrc))
    zshrc = Path.home() / ".zshrc"
    if zshrc.exists():
        shells.append(("zshrc", zshrc))
    return shells


def _add_alias_to_shell(shell_rc: Path, alias_line: str, header_needed: bool) -> None:
    """Append alias to shell config file with optional header."""
    with shell_rc.open("a", encoding="utf-8") as f:
        if header_needed:
            f.write("\n# AMI Orchestrator - auto-registered by install.py\n")
        f.write(f"{alias_line}\n")


def _register_aliases_in_shell(shell_rc: Path, alias_run: str, alias_uv: str) -> bool:
    """Register both aliases in a single shell config file. Returns True if modified."""
    content = shell_rc.read_text(encoding="utf-8")
    modified = False

    if alias_run not in content:
        _add_alias_to_shell(shell_rc, alias_run, header_needed=True)
        modified = True

    if alias_uv not in content:
        # Re-read in case ami-run was just added
        content = shell_rc.read_text(encoding="utf-8")
        # Add header only if ami-run existed originally (wasn't just added above)
        header_needed = alias_run in content and not modified
        _add_alias_to_shell(shell_rc, alias_uv, header_needed=header_needed)
        modified = True

    return modified


def register_shell_aliases() -> bool:
    """Register ami-run and ami-uv as shell aliases in ~/.bashrc and ~/.zshrc."""
    ami_run_path = ROOT / "scripts" / "ami-run.sh"
    ami_uv_path = ROOT / "scripts" / "ami-uv"

    if not ami_run_path.exists():
        logger.warning(f"ami-run.sh not found at {ami_run_path}")
        return False
    if not ami_uv_path.exists():
        logger.warning(f"ami-uv not found at {ami_uv_path}")
        return False

    alias_run_line = f'alias ami-run="{ami_run_path}"'
    alias_uv_line = f'alias ami-uv="{ami_uv_path}"'

    shells = _find_shell_configs()
    if not shells:
        logger.warning("No .bashrc or .zshrc found in home directory")
        return False

    for name, shell_rc in shells:
        modified = _register_aliases_in_shell(shell_rc, alias_run_line, alias_uv_line)
        if modified:
            logger.info(f"✓ Registered aliases in ~/.{name}")
        else:
            logger.info(f"✓ Aliases already present in ~/.{name}")

    logger.info("\nTo use aliases immediately in this shell:")
    logger.info("  source ~/.bashrc  # or: source ~/.zshrc")
    logger.info("Or restart your shell.")
    return True


def main() -> int:
    logger.info("=" * 60)
    logger.info("AMI Orchestrator Installation")
    logger.info("=" * 60)
    logger.info("")

    # Step 1: Initialize git submodules
    if not ensure_git_submodules():
        logger.error("Failed to initialize submodules")
        return 1

    logger.info("")

    # Step 2: Register shell aliases
    if not register_shell_aliases():
        logger.warning("Failed to register shell aliases (non-fatal)")

    logger.info("")

    # Step 3: Run module_setup.py for recursive venv creation
    module_setup = ROOT / "module_setup.py"
    if not module_setup.exists():
        logger.error("module_setup.py not found - run propagate.py first")
        return 1

    logger.info("=" * 60)
    logger.info("Running module_setup.py for recursive venv creation...")
    logger.info("=" * 60)
    result = subprocess.run([sys.executable, str(module_setup)], cwd=ROOT, check=False)

    if result.returncode != 0:
        logger.error("module_setup.py failed")
        return result.returncode

    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ AMI Orchestrator installation complete!")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
