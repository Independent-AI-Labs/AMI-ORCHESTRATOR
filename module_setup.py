#!/usr/bin/env python
"""AMI Orchestrator Master Setup Script.

This script:
1. Initializes and syncs all git submodules
2. Sets up each submodule's virtual environment and dependencies
3. Installs pre-commit hooks for all modules
"""

import argparse
import logging
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

logger = logging.getLogger(__name__)


class OrchestratorSetup:
    """Master setup for AMI Orchestrator and all submodules."""

    def __init__(self, clean: bool = True, reset: bool = False):
        """Initialize orchestrator setup.

        Args:
            clean: Whether to clean all venvs and caches before setup (default: True)
            reset: Whether to reset submodules to recorded commits (default: False)
        """
        self.root_dir = Path(__file__).parent.resolve()
        self.clean = clean
        self.reset = reset
        self.submodules = [
            "base",
            "browser",
            "compliance",
            "domains",
            "files",
            "streams",
            "ux",
        ]

    def run_command(self, cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a command and return the result.

        Args:
            cmd: Command to run as list of strings
            cwd: Working directory (defaults to root)
            check: Whether to check return code

        Returns:
            CompletedProcess result
        """
        if cwd is None:
            cwd = self.root_dir

        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            logger.error(f"Error: {result.stderr}")
            if check:
                sys.exit(1)

        return result

    def clean_all(self) -> None:
        """Clean all venvs and caches."""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 0: Cleaning Project")
        logger.info("=" * 60)

        clean_script = self.root_dir / "scripts" / "clean_all.py"
        if clean_script.exists():
            self.run_command([sys.executable, str(clean_script)])
            logger.info("[OK] Project cleaned")
        else:
            logger.warning("[WARN] clean_all.py not found, skipping clean")

    def init_submodules(self) -> None:
        """Initialize and sync all git submodules."""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 1: Initializing Git Submodules")
        logger.info("=" * 60)

        for module in self.submodules:
            module_path = self.root_dir / module

            # Check if module directory exists and has .git
            if module_path.exists() and (module_path / ".git").exists():
                logger.info(f"Module {module} already initialized, pulling latest...")
                self.run_command(["git", "pull"], cwd=module_path, check=False)
            else:
                logger.info(f"Module {module} not initialized, initializing...")
                # Initialize this specific submodule
                self.run_command(["git", "submodule", "init", module])
                self.run_command(["git", "submodule", "update", "--init", module])

        # Sync submodule URLs
        self.run_command(["git", "submodule", "sync", "--recursive"])

        if self.reset:
            logger.warning("[WARN] Reset flag is set - resetting all submodules to recorded commits")
            self.run_command(["git", "submodule", "update", "--init", "--recursive", "--force"])
            logger.info("[OK] All submodules reset to recorded commits")
        else:
            logger.info("[OK] All submodules initialized/pulled (preserving current commits)")

    def setup_module(self, module_name: str) -> None:
        """Set up a single module's environment.

        Args:
            module_name: Name of the module to set up
        """
        module_path = self.root_dir / module_name

        if not module_path.exists():
            logger.warning(f"[WARN] Module {module_name} not found, skipping")
            return

        logger.info(f"\n--- Setting up {module_name} module ---")

        # Check if setup.py exists
        setup_script = module_path / "module_setup.py"
        if not setup_script.exists():
            logger.warning(f"[WARN] No module_setup.py found in {module_name}, skipping")
            return

        # Run the module's module_setup.py
        result = self.run_command([sys.executable, "module_setup.py"], cwd=module_path, check=False)

        if result.returncode == 0:
            logger.info(f"[OK] {module_name} module setup complete")
        else:
            logger.error(f"[ERROR] {module_name} module setup failed")
            logger.error(f"  Error: {result.stderr}")

    def _check_uv_available(self) -> bool:
        """Check if uv is available."""
        try:
            self.run_command(["uv", "--version"], check=False)
            return True
        except FileNotFoundError:
            return False

    def _setup_with_uv(self, venv_path: Path) -> None:
        """Set up virtual environment using uv."""
        # Always recreate venv to ensure clean state
        if venv_path.exists():
            logger.info(f"Removing existing venv at {venv_path}...")
            shutil.rmtree(venv_path, ignore_errors=True)

        logger.info("Creating virtual environment with uv...")
        self.run_command(["uv", "venv", str(venv_path), "--python", "python3.12"])

        # Install base requirements
        base_reqs = self.root_dir / "base" / "requirements.txt"
        if base_reqs.exists():
            logger.info("Installing base requirements...")
            self.run_command(["uv", "pip", "install", "-r", str(base_reqs)])

        # Install base test requirements
        base_test_reqs = self.root_dir / "base" / "requirements-test.txt"
        if base_test_reqs.exists():
            logger.info("Installing base test requirements...")
            self.run_command(["uv", "pip", "install", "-r", str(base_test_reqs)])

        # Install orchestrator requirements if they exist
        orch_reqs = self.root_dir / "requirements.txt"
        if orch_reqs.exists():
            logger.info("Installing orchestrator requirements...")
            self.run_command(["uv", "pip", "install", "-r", str(orch_reqs)])

    def setup_orchestrator_venv(self) -> None:
        """Set up the orchestrator's own virtual environment."""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: Setting up Orchestrator Environment")
        logger.info("=" * 60)

        # Require uv to be installed
        if not self._check_uv_available():
            logger.error("\n" + "=" * 60)
            logger.error("ERROR: uv is required but not found!")
            logger.error("=" * 60)
            logger.error("\nPlease install uv first:")
            logger.error("  pip install uv")
            logger.error("\nOr download from: https://github.com/astral-sh/uv")
            sys.exit(1)

        # Create orchestrator venv
        venv_path = self.root_dir / ".venv"
        logger.info(f"Creating orchestrator venv at {venv_path}...")
        self._setup_with_uv(venv_path)

        # Install pre-commit hooks for orchestrator
        self.install_precommit_hooks(self.root_dir)

        logger.info("[OK] Orchestrator environment setup complete")

    def install_precommit_hooks(self, module_path: Path) -> None:
        """Install pre-commit hooks for a module.

        Args:
            module_path: Path to the module
        """
        # Check if .pre-commit-config.yaml exists
        precommit_config = module_path / ".pre-commit-config.yaml"
        if not precommit_config.exists():
            return

        # Get python path
        venv_path = module_path / ".venv"
        if sys.platform == "win32":
            python_path = venv_path / "Scripts" / "python.exe"
        else:
            python_path = venv_path / "bin" / "python"

        if python_path.exists():
            # Install pre-commit hooks
            logger.info(f"Installing pre-commit hooks in {module_path.name}...")
            self.run_command([str(python_path), "-m", "pre_commit", "install"], cwd=module_path, check=False)
            self.run_command([str(python_path), "-m", "pre_commit", "install", "--hook-type", "pre-push"], cwd=module_path, check=False)

    def setup_all_modules(self) -> None:
        """Set up all submodules."""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: Setting up All Submodules")
        logger.info("=" * 60)

        # Base module must be set up first
        if "base" in self.submodules:
            logger.info(f"Setting up base module [1/{len(self.submodules)}]...")
            self.setup_module("base")

        # Set up remaining modules (excluding base since it's already done)
        remaining_modules = [module for module in self.submodules if module != "base"]
        for i, module in enumerate(remaining_modules, start=2):
            logger.info(f"Setting up {module} module [{i}/{len(self.submodules)}]...")
            self.setup_module(module)

    def run(self) -> int:
        """Run the complete orchestrator setup.

        Returns:
            Exit code (0 for success)
        """
        logger.info("\n" + "=" * 60)
        logger.info("AMI ORCHESTRATOR COMPLETE SETUP")
        logger.info("=" * 60)

        try:
            # Step 0: Clean if requested
            if self.clean:
                self.clean_all()

            # Step 1: Initialize submodules
            self.init_submodules()

            # Step 2: Set up orchestrator environment
            self.setup_orchestrator_venv()

            # Step 3: Set up all submodules
            self.setup_all_modules()

            logger.info("\n" + "=" * 60)
            logger.info("[OK] SETUP COMPLETE!")
            logger.info("=" * 60)
            logger.info("\nTo activate the orchestrator environment:")
            if sys.platform == "win32":
                logger.info("  .venv\\Scripts\\activate")
            else:
                logger.info("  source .venv/bin/activate")
            logger.info("\nEach submodule has its own .venv in its directory.")
            logger.info("Pre-commit hooks have been installed for all modules.")

            return 0

        except Exception as e:
            logger.error(f"\n[ERROR] Setup failed: {e}")
            traceback.print_exc()
            return 1


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AMI Orchestrator Setup Script")
    parser.add_argument("--no-clean", action="store_true", help="Do not clean venvs and caches before setup (default: clean everything)")
    parser.add_argument("--reset", action="store_true", help="Reset all submodules to recorded commits (default: preserve current commits)")

    args = parser.parse_args()

    # Clean by default unless --no-clean is specified
    clean = not args.no_clean

    setup = OrchestratorSetup(clean=clean, reset=args.reset)
    sys.exit(setup.run())


if __name__ == "__main__":
    main()
