#!/usr/bin/env bash
""":'
exec "$(dirname "$0")/scripts/ami-run.sh" "$0" "$@"
"""

from __future__ import annotations

"""AMI Orchestrator installer - bootstraps the development environment.

This script handles one-time setup tasks:
1. Initialize git submodules (with HTTPS fallback)
2. Register ami-run and ami-uv shell aliases
3. Delegate to module_setup.py for recursive venv creation

Run this once to set up the entire orchestrator.
For updates, run module_setup.py directly.
"""

import argparse
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


def _register_aliases_in_shell(shell_rc: Path, alias_run: str, alias_uv: str) -> bool:
    """Register shell setup by sourcing setup-shell.sh. Returns True if modified."""
    content = shell_rc.read_text(encoding="utf-8")

    # Check if setup-shell.sh is already sourced
    if "setup-shell.sh" in content:
        return False

    # Auto-install by adding source line
    marker = "# AMI Orchestrator Shell Setup"
    ami_root = ROOT.resolve()
    source_line = f'[ -f "{ami_root}/scripts/setup-shell.sh" ] && . "{ami_root}/scripts/setup-shell.sh"'

    with shell_rc.open("a", encoding="utf-8") as f:
        f.write("\n")
        f.write(f"{marker}\n")
        f.write(f"{source_line}\n")

    return True


def register_shell_aliases() -> bool:
    """Auto-install shell setup by sourcing setup-shell.sh."""
    setup_script = ROOT / "scripts" / "setup-shell.sh"
    if not setup_script.exists():
        logger.warning(f"setup-shell.sh not found at {setup_script}")
        return False

    shells = _find_shell_configs()
    if not shells:
        logger.warning("No .bashrc or .zshrc found in home directory")
        return False

    # Dummy aliases for signature compatibility
    alias_run = ""
    alias_uv = ""

    installed_count = 0
    for name, shell_rc in shells:
        modified = _register_aliases_in_shell(shell_rc, alias_run, alias_uv)
        if modified:
            logger.info(f"✓ Installed AMI shell setup in ~/.{name}")
            installed_count += 1
        else:
            logger.info(f"✓ AMI shell setup already present in ~/.{name}")

    if installed_count > 0:
        logger.info("\nTo activate immediately:")
        logger.info("  source ~/.bashrc  # or: source ~/.zshrc")
        logger.info("Or restart your shell.")

    return True


def prompt_claude_install_mode() -> str:
    """Prompt user to choose Claude CLI installation mode.

    Returns:
        "local" for venv-local install, "system" for global, "skip" to skip
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("Claude CLI Installation")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Choose how to install Claude CLI:")
    logger.info("  local  - Install to .venv/node_modules/ (recommended, no sudo)")
    logger.info("  system - Install globally via npm -g (requires sudo)")
    logger.info("  skip   - Skip installation (install manually later)")
    logger.info("")

    while True:
        choice = input("Install mode [local/system/skip]: ").strip().lower()
        if choice in ("local", "system", "skip"):
            return choice
        logger.warning(f"Invalid choice: {choice}. Please enter 'local', 'system', or 'skip'.")


def main() -> int:
    parser = argparse.ArgumentParser(description="AMI Orchestrator installer")
    parser.add_argument(
        "--skip-claude-check",
        action="store_true",
        help="Skip Claude CLI installation prompt (for automated installs)",
    )
    parser.add_argument(
        "--claude-mode",
        choices=["local", "system", "skip"],
        help="Claude CLI install mode (local=venv, system=global, skip=none)",
    )
    args = parser.parse_args()

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

    # Step 3: Determine Claude CLI installation mode
    if args.skip_claude_check:
        claude_mode = "skip"
    elif args.claude_mode:
        claude_mode = args.claude_mode
    else:
        claude_mode = prompt_claude_install_mode()

    logger.info("")

    # Step 4: Run module_setup.py for recursive venv creation
    module_setup = ROOT / "module_setup.py"
    if not module_setup.exists():
        logger.error("module_setup.py not found - run propagate.py first")
        return 1

    logger.info("=" * 60)
    logger.info("Running module_setup.py for recursive venv creation...")
    logger.info("=" * 60)

    setup_cmd = [sys.executable, str(module_setup), "--claude-mode", claude_mode]
    result = subprocess.run(setup_cmd, cwd=ROOT, check=False)

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
