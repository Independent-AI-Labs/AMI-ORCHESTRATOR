#!/usr/bin/env python3
"""
Cross-platform bootstrap for installing `uv` and (optionally) ensuring a Python toolchain.

Goals
- Prefer trusted package managers when available (brew/winget/choco)
- Fall back to Astral's official installer over HTTPS
- Install user-local binaries when possible (no sudo required)
- Provide a stable entry point for automation via --auto

Usage
  python scripts/bootstrap_uv_python.py --auto --ensure-python 3.12

Behavior
- If `uv` is already installed, skips installation.
- After installation, tries common install locations if PATH isn't updated yet.
- Optionally installs a Python toolchain via `uv python install <version>`.

Notes
- This script uses only the Python standard library.
- Network access is required for online installation methods.
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
from pathlib import Path


def _print(msg: str) -> None:
    print(msg, flush=True)


def which_uv() -> str | None:
    """Return a resolvable path to `uv` if available, otherwise None.

    Also checks common post-install locations used by Astral's installer.
    """
    path = shutil.which("uv")
    if path:
        return path
    # Common user-local install locations
    candidates = [
        Path("~/.cargo/bin/uv").expanduser(),
        Path("~/.local/bin/uv").expanduser(),
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)
    return None


def run(cmd: list[str], check: bool = False) -> int:
    _print("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)} (rc={proc.returncode})")
    return proc.returncode


def _install_uv_via_pkg_manager(system: str) -> bool:
    """Try platform package managers.

    Returns True if an install command was executed and likely succeeded.
    """
    if system == "darwin":  # macOS
        if shutil.which("brew"):
            _print("Installing uv via Homebrew…")
            return run(["brew", "install", "uv"]) == 0
        return False
    if system == "windows":
        if shutil.which("winget"):
            _print("Installing uv via winget…")
            if run(["winget", "install", "-e", "--id", "Astral-Software.UV"]) == 0:
                return True
        if shutil.which("choco"):
            _print("Installing uv via Chocolatey…")
            return run(["choco", "install", "-y", "uv"]) == 0
        return False
    # Linux: no widely-available package manager entry yet; rely on official installer
    return False


def _install_uv_via_official(system: str) -> bool:
    """Use Astral's official installer scripts."""
    if system == "windows":
        ps_cmd = (
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "& { irm https://astral.sh/uv/install.ps1 | iex }",
        )
        _print("Installing uv via official PowerShell installer…")
        return run(list(ps_cmd)) == 0
    # Linux/macOS shell installer; user-local
    _print("Installing uv via official shell installer…")
    cmd = ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"]
    return run(cmd) == 0


def install_uv_auto() -> bool:
    """Attempt to install uv using platform-appropriate methods.

    Returns True if we likely installed uv (or it already existed), False otherwise.
    """
    if which_uv():
        _print("uv is already installed.")
        return True

    system = platform.system().lower()

    # Prefer package managers first where available
    installed = False
    try:
        installed = _install_uv_via_pkg_manager(system)
    except Exception as e:  # defensive; fall through to official installer
        _print(f"Package manager install attempt failed: {e}")

    # Official installer fallbacks
    if not installed:
        try:
            installed = _install_uv_via_official(system)
        except Exception as e:
            _print(f"Official installer attempt failed: {e}")

    # Final verification, even if installation reported success
    return which_uv() is not None


def ensure_python_with_uv(uv_path: str, version: str) -> bool:
    """Ensure the specified Python toolchain is available via uv.

    Returns True if available or installed successfully.
    """
    # Try to find first
    rc = run([uv_path, "python", "find", version])
    if rc == 0:
        return True
    _print(f"Installing Python {version} via uv…")
    rc = run([uv_path, "python", "install", version])
    return rc == 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Bootstrap installer for uv and optional Python toolchain")
    ap.add_argument("--auto", action="store_true", help="Perform installation without interactive prompts")
    ap.add_argument("--ensure-python", metavar="VERSION", default=None, help="Ensure a Python toolchain is installed via uv (e.g., 3.12)")
    ap.add_argument("--only-uv", action="store_true", help="Install uv only; skip Python toolchain")
    args = ap.parse_args()

    # Always attempt to detect uv first
    uv_path = which_uv()

    if not uv_path:
        if not args.auto:
            _print("uv not found. Re-run with --auto to install automatically or install manually.")
            return 1
        if not install_uv_auto():
            _print("Failed to install uv automatically. Please install it manually: https://docs.astral.sh/uv/")
            return 1
        uv_path = which_uv()

    if not uv_path:
        _print("uv appears installed but not found on PATH. Try adding ~/.cargo/bin or ~/.local/bin to PATH.")
        return 1

    _print(f"Using uv at: {uv_path}")

    if args.only_uv:
        return 0

    if args.ensure_python and not ensure_python_with_uv(uv_path, args.ensure_python):
        _print(f"Failed to ensure Python {args.ensure_python} via uv.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
