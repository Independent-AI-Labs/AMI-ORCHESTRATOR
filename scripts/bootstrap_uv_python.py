#!/usr/bin/env python
"""Bootstrap script to install uv and a Python 3.12 toolchain from trusted sources.

This script is cross-platform and follows a conservative approach:
- It prefers OS package managers when available (Homebrew, winget, apt).
- It falls back to Astral's official installer for uv (https://astral.sh/uv).
- It then uses `uv python install 3.12` to provision a local Python runtime.

By default, the script will only report instructions if changes are needed.
Pass --auto to perform installations automatically.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=False, check=check)


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def install_uv(auto: bool) -> None:
    system = platform.system().lower()

    if have("uv"):
        print("[OK] uv already installed")
        return

    print("[INFO] uv not found on PATH")

    if system == "darwin":
        if have("brew"):
            cmd = ["brew", "install", "uv"]
            print("[INFO] Installing uv via Homebrew:", " ".join(cmd))
            if auto:
                run(cmd)
            return
    if system == "windows":
        if have("winget"):
            cmd = ["winget", "install", "-e", "--id", "Astral-Software.UV"]
            print("[INFO] Installing uv via winget:", " ".join(cmd))
            if auto:
                run(cmd)
            return
        if have("choco"):
            cmd = ["choco", "install", "uv", "-y"]
            print("[INFO] Installing uv via Chocolatey:", " ".join(cmd))
            if auto:
                run(cmd)
            return

    # Fallback to Astral official installer scripts
    if system in {"linux", "darwin"}:
        cmd = [
            "sh",
            "-c",
            "curl -LsSf https://astral.sh/uv/install.sh | sh",
        ]
        print("[INFO] Installing uv via official installer (astral.sh):", cmd[-1])
        print("       This fetches signed binaries from official releases over HTTPS.")
        if auto:
            run(cmd)
        return
    if system == "windows":
        ps = (
            "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; "
            "irm https://astral.sh/uv/install.ps1 | iex"
        )
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps]
        print("[INFO] Installing uv via official installer (astral.sh) for Windows")
        if auto:
            run(cmd)
        return

    raise RuntimeError("Unsupported OS for uv installation")


def ensure_python312(auto: bool) -> None:
    # Requires uv
    if not have("uv"):
        print("[ERROR] uv is not installed; cannot provision Python toolchain.")
        return

    # Is Python 3.12 already available to uv?
    find = subprocess.run(["uv", "python", "find", "3.12"], capture_output=True, text=True)
    if find.returncode == 0 and find.stdout.strip():
        print("[OK] Python 3.12 already available to uv:")
        print(find.stdout.strip())
        return

    print("[INFO] Installing Python 3.12 toolchain via uv (python-build-standalone)")
    cmd = ["uv", "python", "install", "3.12"]
    print("       ", " ".join(cmd))
    if auto:
        run(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap uv and Python 3.12 toolchain")
    parser.add_argument("--auto", action="store_true", help="Perform installations automatically instead of printing instructions")

    args = parser.parse_args()

    try:
        install_uv(auto=args.auto)
        ensure_python312(auto=args.auto)
        print("\n[OK] Bootstrap complete. You can now run: python module_setup.py")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {' '.join(e.cmd)}")
        return 1
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

