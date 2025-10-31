#!/usr/bin/env python
"""Base module setup - minimal wrapper around scripts/env."""

from __future__ import annotations

import argparse
import logging
import os
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


def bootstrap_venv_from_platform(module_root: Path) -> Path:
    """Bootstrap .venv from platform-specific copy if missing.

    Returns path to .venv directory.
    Raises RuntimeError if bootstrap fails.
    """
    venv_path = module_root / ".venv"

    # If venv exists, return it
    if venv_path.exists():
        return venv_path

    # Determine platform
    platform_suffix = "windows" if sys.platform == "win32" else "macos" if sys.platform == "darwin" else "linux"
    source_venv = module_root / f".venv-{platform_suffix}"

    if not source_venv.exists():
        raise RuntimeError(
            f"Cannot bootstrap .venv: source .venv-{platform_suffix} not found at {source_venv}. "
            f"Run install.py first or manually create .venv-{platform_suffix}."
        )

    logger.info(f"Bootstrapping .venv from .venv-{platform_suffix}...")
    shutil.copytree(source_venv, venv_path, symlinks=True)
    logger.info(f"✓ Bootstrapped .venv from .venv-{platform_suffix}")

    return venv_path


def load_env_var(module_root: Path, var_name: str, default: str | None = None) -> str | None:
    """Load environment variable from .env file."""
    env_file = module_root / ".env"
    if not env_file.exists():
        return default

    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == var_name:
                        return value.strip()
    except Exception as e:
        logger.warning(f"Failed to load {var_name} from .env: {e}")

    return default


def check_uv(venv_uv: Path) -> bool:
    """Check if uv exists in venv.

    Args:
        venv_uv: Path to venv uv binary

    Returns:
        True if venv uv exists and is executable
    """
    if not venv_uv.exists():
        logger.error(f"uv not found in venv at {venv_uv}")
        logger.error("Bootstrap .venv from .venv-{platform} first")
        return False

    try:
        subprocess.run([str(venv_uv), "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error(f"uv at {venv_uv} is not executable")
        return False


def check_npm(venv_npm: Path) -> bool:
    """Check if npm exists in venv.

    Args:
        venv_npm: Path to venv npm binary

    Returns:
        True if venv npm exists and is executable
    """
    if not venv_npm.exists():
        logger.error(f"npm not found in venv at {venv_npm}")
        logger.error("Run bootstrap_node_in_venv() first")
        return False

    try:
        subprocess.run([str(venv_npm), "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error(f"npm at {venv_npm} is not executable")
        return False


def get_claude_version(claude_path: str = "claude") -> str | None:
    """Get installed Claude CLI version.

    Args:
        claude_path: Path to claude binary (default: "claude" to use PATH)

    Returns:
        Version string like "2.0.10" or None if not found
    """
    try:
        result = subprocess.run([claude_path, "--version"], capture_output=True, text=True, check=True)
        # Output format: "X.Y.Z (Claude Code)"
        version = result.stdout.strip().split()[0]
        return version
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def ensure_claude_version(required_version: str, venv_path: Path | None, venv_npm: Path) -> bool:
    """Ensure Claude CLI is installed at exactly the required version.

    Auto-installs via venv npm if missing or wrong version.

    Args:
        required_version: Claude CLI version required
        venv_path: Path to venv for local installation (uses global if None)
        venv_npm: Path to venv npm binary

    Returns:
        True if installation succeeded
    """
    if not check_npm(venv_npm):
        return False

    current_version = get_claude_version()

    if current_version == required_version:
        logger.info(f"✓ Claude CLI version {required_version} is installed")
        return True

    if current_version:
        logger.warning(f"Claude CLI version {current_version} found, but {required_version} is required")
        logger.info(f"Updating to Claude CLI {required_version}...")
    else:
        logger.info(f"Claude CLI not found. Installing version {required_version}...")

    # Install locally in venv if venv_path provided, otherwise attempt global (may fail without sudo)
    install_cmd = [str(venv_npm), "install"]
    if venv_path:
        # Install locally in venv node_modules
        install_cmd.extend(["--prefix", str(venv_path)])
    else:
        # Global install (requires sudo - may fail in restricted environments)
        install_cmd.append("-g")

    install_cmd.append(f"@anthropic-ai/claude-code@{required_version}")

    try:
        subprocess.run(
            install_cmd,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"✓ Successfully installed Claude CLI {required_version}")

        # Verify installation
        if venv_path:
            # Check venv-local installation
            claude_bin = venv_path / "node_modules" / ".bin" / "claude"
            if not claude_bin.exists():
                logger.error(f"Installation verification failed: {claude_bin} not found")
                return False
            installed_version = get_claude_version(str(claude_bin))
        else:
            # Check global installation
            installed_version = get_claude_version()

        if installed_version != required_version:
            logger.error(f"Installation verification failed: got {installed_version}, expected {required_version}")
            return False

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install Claude CLI {required_version}")
        logger.error(f"Error: {e.stderr if e.stderr else e}")
        return False


def ensure_uv_python(version: str, venv_uv: Path) -> None:
    """Ensure Python version is installed via venv uv.

    Args:
        version: Python version to ensure (e.g. "3.12")
        venv_uv: Path to venv uv binary
    """
    find = subprocess.run([str(venv_uv), "python", "find", version], capture_output=True, text=True, check=False)
    if find.returncode != 0 or not find.stdout.strip():
        logger.info(f"Installing Python {version} toolchain via venv uv...")
        subprocess.run([str(venv_uv), "python", "install", version], check=False)


def sync_dependencies(module_root: Path, venv_uv: Path) -> bool:
    """Sync pyproject.toml dependencies with venv uv.

    Args:
        module_root: Root directory of the module
        venv_uv: Path to venv uv binary

    Returns:
        True if sync succeeded
    """
    logger.info("Syncing dependencies with venv uv (including dev)...")
    synced = subprocess.run([str(venv_uv), "sync", "--dev"], cwd=module_root, capture_output=True, text=True, check=False)
    if synced.returncode != 0:
        logger.error("venv uv sync failed")
        logger.error(synced.stderr)
        return False
    return True


def bootstrap_node_in_venv(module_root: Path) -> bool:
    """Bootstrap Node.js and npm into the Python venv using nodeenv.

    This integrates Node.js directly into the existing Python virtualenv.
    License: nodeenv (BSD-3-Clause), Node.js (MIT), npm (Artistic License 2.0).
    """
    venv_path = module_root / ".venv"
    if not venv_path.exists():
        logger.error("Virtual environment not found at %s", venv_path)
        return False

    # Check if node is already installed in venv
    node_bin = venv_path / "bin" / "node" if sys.platform != "win32" else venv_path / "Scripts" / "node.exe"
    if node_bin.exists():
        logger.info("✓ Node.js already bootstrapped in venv")
        return True

    logger.info("Bootstrapping Node.js into Python venv using nodeenv...")

    # Use nodeenv -p to integrate into existing Python venv
    # This installs node/npm into the same venv
    nodeenv_cmd = [str(venv_path / "bin" / "nodeenv"), "-p", "--node=lts"]
    result = subprocess.run(nodeenv_cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        logger.error("Failed to bootstrap Node.js into venv")
        logger.error(result.stderr)
        return False

    logger.info("✓ Node.js and npm successfully bootstrapped into venv")
    return True


def bootstrap_openssh_in_venv(module_root: Path) -> bool:
    """Bootstrap OpenSSH server into the Python venv for git-only access.

    This installs OpenSSH on non-privileged port 2222 for git repository hosting.
    License: OpenSSH (BSD).
    """
    venv_path = module_root / ".venv"
    if not venv_path.exists():
        logger.error("Virtual environment not found at %s", venv_path)
        return False

    # Check if OpenSSH is already installed in venv
    sshd_bin = venv_path / "openssh" / "sbin" / "sshd"
    sshd_venv = venv_path / "bin" / "sshd-venv"
    if sshd_bin.exists() and sshd_venv.exists():
        logger.info("✓ OpenSSH already bootstrapped in venv")
        return True

    # Only bootstrap on Linux (OpenSSH bootstrap script is Linux-only)
    if sys.platform != "linux":
        logger.info("OpenSSH bootstrap only supported on Linux, skipping")
        return True

    logger.info("Bootstrapping OpenSSH server into venv...")

    # Run bootstrap_openssh.sh script
    bootstrap_script = module_root / "scripts" / "bootstrap_openssh.sh"
    if not bootstrap_script.exists():
        logger.warning("OpenSSH bootstrap script not found at %s, skipping", bootstrap_script)
        return True

    result = subprocess.run(["bash", str(bootstrap_script)], capture_output=True, text=True, check=False)

    if result.returncode != 0:
        logger.error("Failed to bootstrap OpenSSH into venv")
        logger.error(result.stderr)
        return False

    logger.info("✓ OpenSSH server successfully bootstrapped into venv (port 2222)")
    return True


def bootstrap_git_in_venv(module_root: Path) -> bool:
    """Bootstrap Git into the Python venv for self-contained git-daemon.

    This installs Git binaries for git-daemon without system dependencies.
    License: Git (GPLv2).
    """
    venv_path = module_root / ".venv"
    if not venv_path.exists():
        logger.error("Virtual environment not found at %s", venv_path)
        return False

    # Check if Git is already installed in venv
    git_bin = venv_path / "git" / "bin" / "git"
    if git_bin.exists():
        logger.info("✓ Git already bootstrapped in venv")
        return True

    # Only bootstrap on Linux (Git bootstrap script is Linux-only)
    if sys.platform != "linux":
        logger.info("Git bootstrap only supported on Linux, skipping")
        return True

    logger.info("Bootstrapping Git into venv...")

    # Run bootstrap_git.sh script
    bootstrap_script = module_root / "scripts" / "bootstrap_git.sh"
    if not bootstrap_script.exists():
        logger.warning("Git bootstrap script not found at %s, skipping", bootstrap_script)
        return True

    result = subprocess.run(["bash", str(bootstrap_script)], capture_output=True, text=True, check=False)

    if result.returncode != 0:
        logger.error("Failed to bootstrap Git into venv")
        logger.error(result.stderr)
        return False

    # Create symlink in .venv/bin
    git_symlink = venv_path / "bin" / "git"
    if not git_symlink.exists():
        git_symlink.symlink_to("../git/bin/git")

    logger.info("✓ Git successfully bootstrapped into venv")
    return True


def sync_venv_platform(module_root: Path) -> bool:
    """Replicate .venv to platform-specific copy (.venv-linux or .venv-windows).

    This enables easy platform-specific backup/restore of virtual environments.
    """
    venv_path = module_root / ".venv"
    if not venv_path.exists():
        logger.warning(".venv does not exist, skipping platform sync")
        return True

    # Determine platform-specific target
    platform_suffix = "windows" if sys.platform == "win32" else "linux"
    target_venv = module_root / f".venv-{platform_suffix}"

    logger.info(f"Syncing .venv → .venv-{platform_suffix}...")

    # Remove old platform-specific venv if it exists
    if target_venv.exists():
        logger.info(f"Removing old .venv-{platform_suffix}...")
        shutil.rmtree(target_venv)

    # Copy .venv to platform-specific location
    logger.info(f"Copying .venv to .venv-{platform_suffix}...")
    shutil.copytree(venv_path, target_venv, symlinks=True)

    logger.info(f"✓ Successfully synced .venv to .venv-{platform_suffix}")
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


def setup_child_submodules(module_root: Path, venv_python: Path) -> None:
    """Recursively setup direct child submodules with module_setup.py.

    Only processes immediate children, not deeper descendants.
    Each child's setup will handle its own children recursively.

    Args:
        module_root: Root directory of the module
        venv_python: Path to venv python binary (NEVER use system python)
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
        result = subprocess.run([str(venv_python), str(child_setup)], cwd=child, check=False)
        if result.returncode != 0:
            logger.warning(f"Setup for {child.name} failed with code {result.returncode}")
        else:
            logger.info(f"✓ {child.name} setup complete")


def setup(module_root: Path, project_name: str | None, claude_mode: str = "local") -> int:
    """Main setup orchestration.

    Args:
        module_root: Root directory of the module
        project_name: Optional project name for display
        claude_mode: Claude CLI install mode (local/system/skip)
    """
    name = project_name or module_root.name
    logger.info("=" * 60)
    logger.info(f"Setting up {name} Development Environment")
    logger.info(f"Module root: {module_root}")
    logger.info("=" * 60)

    # Bootstrap .venv from platform-specific copy
    try:
        venv_path = bootstrap_venv_from_platform(module_root)
    except RuntimeError as e:
        logger.error(str(e))
        return 1

    # Get venv binaries (NEVER use system binaries)
    venv_uv = venv_path / "bin" / "uv"
    venv_python = venv_path / "bin" / "python"
    venv_npm = venv_path / "bin" / "npm"

    if not check_uv(venv_uv):
        return 1

    ensure_uv_python("3.12", venv_uv)

    pyproject = module_root / "pyproject.toml"
    if not pyproject.exists():
        logger.error("pyproject.toml is required but missing at %s", pyproject)
        logger.info("Every module must define dependencies via pyproject.toml for reproducibility.")
        return 1

    # Use consolidated env utilities for venv creation
    setup_imports(module_root)
    ensure_venv(module_root, python_version="3.12")

    # Sync dependencies from pyproject.toml
    if not sync_dependencies(module_root, venv_uv):
        return 1

    # Bootstrap Node.js/npm into venv
    if not bootstrap_node_in_venv(module_root):
        logger.warning("Failed to bootstrap Node.js, continuing anyway...")

    # Bootstrap OpenSSH server into venv (for git repository hosting)
    if not bootstrap_openssh_in_venv(module_root):
        logger.warning("Failed to bootstrap OpenSSH, continuing anyway...")

    # Bootstrap Git into venv (for self-contained git-daemon)
    if not bootstrap_git_in_venv(module_root):
        logger.warning("Failed to bootstrap Git, continuing anyway...")

    # Install Claude CLI based on mode
    if claude_mode == "skip":
        logger.info("Skipping Claude CLI installation (--claude-mode skip)")
    else:
        required_claude_version = load_env_var(module_root, "CLAUDE_CLI_VERSION", "2.0.10")
        venv_path_for_claude = module_root / ".venv" if claude_mode == "local" else None

        if claude_mode == "local":
            logger.info(f"Installing Claude CLI {required_claude_version} to venv (local mode)")
        else:
            logger.info(f"Installing Claude CLI {required_claude_version} globally (system mode)")

        if not ensure_claude_version(required_claude_version, venv_path_for_claude, venv_npm):
            logger.error(f"Claude CLI version {required_claude_version} is required but could not be installed")
            return 1

    install_precommit(module_root)

    # Setup direct child submodules recursively
    setup_child_submodules(module_root, venv_python)

    # Sync .venv to platform-specific copy
    if not sync_venv_platform(module_root):
        logger.warning("Failed to sync venv to platform-specific copy")

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
    parser.add_argument(
        "--claude-mode",
        choices=["local", "system", "skip"],
        default="local",
        help="Claude CLI install mode (local=venv, system=global, skip=none)",
    )
    args = parser.parse_args()

    return setup(args.project_dir, args.project_name, args.claude_mode)


if __name__ == "__main__":
    sys.exit(main())
