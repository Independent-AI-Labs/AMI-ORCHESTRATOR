#!/usr/bin/env python
"""Data acquisition module setup using only stdlib + uv subprocess calls.

Contract:
- No third-party imports at top level
- No sys.path manipulation
- Each module manages its own uv venv and dependencies
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def check_uv() -> bool:
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("uv is not installed or not on PATH.")
        logger.info("Install uv: https://docs.astral.sh/uv/")
        return False


def ensure_uv_python(version: str = "3.12") -> None:
    find = subprocess.run(["uv", "python", "find", version], capture_output=True, text=True, check=False)
    if find.returncode != 0 or not find.stdout.strip():
        logger.info(f"Installing Python {version} toolchain via uv...")
        subprocess.run(["uv", "python", "install", version], check=False)


def uv_venv_sync(module_root: Path) -> bool:
    venv_dir = module_root / ".venv"
    if not venv_dir.exists():
        logger.info("Creating uv venv (Python 3.12)...")
        created = subprocess.run(["uv", "venv", "--python", "3.12"], cwd=module_root, capture_output=True, text=True, check=False)
        if created.returncode != 0:
            logger.error("uv venv creation failed")
            logger.error(created.stderr)
            return False

    logger.info("Syncing dependencies with uv (including dev)...")
    synced = subprocess.run(["uv", "sync", "--dev"], cwd=module_root, capture_output=True, text=True, check=False)
    if synced.returncode != 0:
        logger.error("uv sync failed")
        logger.error(synced.stderr)
        return False
    return True


def install_precommit(module_root: Path) -> None:
    cfg = module_root / ".pre-commit-config.yaml"
    if not cfg.exists():
        return
    logger.info("Installing pre-commit hooks...")
    subprocess.run(["uv", "run", "pre-commit", "install"], cwd=module_root, check=False)
    subprocess.run(["uv", "run", "pre-commit", "install", "--hook-type", "pre-push"], cwd=module_root, check=False)


def setup(module_root: Path, project_name: str | None) -> int:
    name = project_name or module_root.name
    logger.info("=" * 60)
    logger.info(f"Setting up {name} Development Environment")
    logger.info(f"Module root: {module_root}")
    logger.info("=" * 60)

    if not check_uv():
        return 1
    ensure_uv_python("3.12")

    pyproject = module_root / "pyproject.toml"
    if not pyproject.exists():
        logger.error("pyproject.toml is required but missing at %s", pyproject)
        logger.info("Every module must define dependencies via pyproject.toml for reproducibility.")
        return 1

    if not uv_venv_sync(module_root):
        return 1

    install_precommit(module_root)

    logger.info("=" * 60)
    logger.info(f"{name} Development Environment Setup Complete!")
    logger.info("Activate the venv:")
    if sys.platform == "win32":
        logger.info(f"  {module_root}\\.venv\\Scripts\\activate")
    else:
        logger.info(f"  source {module_root}/.venv/bin/activate")
    logger.info("Run tests:")
    logger.info("  uv run pytest -q")
    logger.info("=" * 60)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up development environment for AMI data acquisition module")
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent, help="Project directory (default: this module)")
    parser.add_argument("--project-name", type=str, help="Optional project name for display")
    args = parser.parse_args()

    return setup(args.project_dir, args.project_name)


if __name__ == "__main__":
    sys.exit(main())
