#!/usr/bin/env bash
""":'
exec "$(dirname "$0")/../scripts/ami-run.sh" "$0" "$@"
"""

from __future__ import annotations

"""Base module setup - minimal wrapper around scripts/env."""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Bootstrap sys.path - MUST come before base imports
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))

# Import consolidated environment utilities from base
from base.scripts.env.paths import setup_imports  # noqa: E402
from base.scripts.env.venv import ensure_venv  # noqa: E402


def check_uv() -> bool:
    """Check if uv is installed."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("uv is not installed or not on PATH.")
        logger.info("Install uv: https://docs.astral.sh/uv/")
        return False


def ensure_uv_python(version: str = "3.12") -> None:
    """Ensure Python version is installed via uv."""
    find = subprocess.run(["uv", "python", "find", version], capture_output=True, text=True, check=False)
    if find.returncode != 0 or not find.stdout.strip():
        logger.info(f"Installing Python {version} toolchain via uv...")
        subprocess.run(["uv", "python", "install", version], check=False)


def sync_dependencies(module_root: Path) -> bool:
    """Sync pyproject.toml dependencies with uv."""
    logger.info("Syncing dependencies with uv (including dev)...")
    synced = subprocess.run(["uv", "sync", "--dev"], cwd=module_root, capture_output=True, text=True, check=False)
    if synced.returncode != 0:
        logger.error("uv sync failed")
        logger.error(synced.stderr)
        return False
    return True


def _find_orchestrator_root(module_root: Path) -> Path:
    """Find orchestrator root by locating /base directory."""
    orchestrator_root = module_root
    while orchestrator_root.parent != orchestrator_root:
        if (orchestrator_root / "base").exists():
            return orchestrator_root
        orchestrator_root = orchestrator_root.parent
    return module_root


def _get_git_hooks_dir(module_root: Path) -> Path | None:
    """Determine git hooks directory for module."""
    git_file = module_root / ".git"
    if git_file.is_file():
        # Submodule - .git is a file pointing to parent
        git_content = git_file.read_text().strip()
        if git_content.startswith("gitdir: "):
            git_dir = git_content[8:]
            return module_root / git_dir / "hooks" if git_dir.startswith("../") else Path(git_dir) / "hooks"
        logger.warning("Invalid .git file format - skipping hook installation")
        return None
    if git_file.is_dir():
        # Regular git repo
        return git_file / "hooks"
    logger.warning("No .git directory or file found - skipping hook installation")
    return None


def install_precommit(module_root: Path) -> None:
    """Install native git hooks from /base/scripts/hooks/ to module's .git/hooks/.

    This enables standalone module setup without requiring propagate.py.
    Single source of truth: /base/scripts/hooks/
    """
    orchestrator_root = _find_orchestrator_root(module_root)
    hook_sources = orchestrator_root / "base" / "scripts" / "hooks"
    if not hook_sources.exists():
        logger.warning("Hook sources not found at %s - skipping hook installation", hook_sources)
        return

    git_hooks_dir = _get_git_hooks_dir(module_root)
    if not git_hooks_dir or not git_hooks_dir.exists():
        logger.warning("Git hooks directory not found - skipping hook installation")
        return

    # Install hooks
    installed = 0
    for hook_file in ["pre-commit", "pre-push", "commit-msg"]:
        source = hook_sources / hook_file
        if source.exists():
            dest = git_hooks_dir / hook_file
            shutil.copy2(source, dest)
            dest.chmod(0o755)
            installed += 1

    if installed > 0:
        logger.info(f"Installed {installed} native git hooks from /base/scripts/hooks/")


def setup_child_submodules(module_root: Path) -> None:
    """Recursively setup direct child submodules with module_setup.py.

    Only processes immediate children, not deeper descendants.
    Each child's setup will handle its own children recursively.
    """
    children_with_setup = []
    for child in module_root.iterdir():
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        child_setup = child / "module_setup.py"
        if child_setup.exists():
            children_with_setup.append(child)

    if not children_with_setup:
        return

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Setting up {len(children_with_setup)} child submodule(s)")
    logger.info("=" * 60)

    for child in children_with_setup:
        child_setup = child / "module_setup.py"
        logger.info(f"\nRunning setup for {child.name}...")
        result = subprocess.run([sys.executable, str(child_setup)], cwd=child, check=False)
        if result.returncode != 0:
            logger.warning(f"Setup for {child.name} failed with code {result.returncode}")
        else:
            logger.info(f"✓ {child.name} setup complete")


def setup(module_root: Path, project_name: str | None) -> int:
    """Main setup orchestration."""
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

    # Use consolidated env utilities for venv creation
    setup_imports(module_root)
    ensure_venv(module_root, python_version="3.12")

    # Sync dependencies from pyproject.toml
    if not sync_dependencies(module_root):
        return 1

    install_precommit(module_root)

    # Setup direct child submodules recursively
    setup_child_submodules(module_root)

    logger.info("")
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
    parser = argparse.ArgumentParser(description="Set up development environment for AMI base module")
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent, help="Project directory (default: this module)")
    parser.add_argument("--project-name", type=str, help="Optional project name for display")
    args = parser.parse_args()

    return setup(args.project_dir, args.project_name)


if __name__ == "__main__":
    sys.exit(main())
