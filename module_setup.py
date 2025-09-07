#!/usr/bin/env python
"""AMI Orchestrator Master Setup Script.

This script:
1. Initializes and syncs all git submodules
2. Sets up each submodule's virtual environment and dependencies
3. Installs pre-commit hooks for all modules
"""

from __future__ import annotations

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
        self.module_failures: list[str] = []
        # Managed submodules (align with .gitmodules)
        self.submodules = [
            "base",
            "browser",
            "compliance",
            "domains",
            "files",
            "node",
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
                raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)

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
        """Initialize and sync all git submodules recursively.

        Uses safe submodule commands instead of `git pull` inside submodules
        (which may be in detached HEAD state).
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 1: Initializing Git Submodules")
        logger.info("=" * 60)
        # Sync and initialize all submodules recursively
        self.run_command(["git", "submodule", "sync", "--recursive"], check=False)
        self.run_command(["git", "submodule", "update", "--init", "--recursive"])

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

        # If module is uv-native (pyproject.toml present), run uv sync first
        if (module_path / "pyproject.toml").exists():
            self.run_command(["uv", "sync", "--dev"], cwd=module_path, check=False)

        # Run the module's module_setup.py with Python 3.12 via uv
        result = self.run_command(["uv", "run", "--python", "3.12", "module_setup.py"], cwd=module_path, check=False)

        if result.returncode == 0:
            logger.info(f"[OK] {module_name} module setup complete")
        else:
            logger.error(f"[ERROR] {module_name} module setup failed")
            logger.error(f"  Error: {result.stderr}")
            self.module_failures.append(module_name)

    def _check_uv_available(self) -> bool:
        """Check if uv is available on PATH."""
        try:
            self.run_command(["uv", "--version"], check=False)
            return True
        except FileNotFoundError:
            return False

    def ensure_uv_and_python(self) -> None:
        """Ensure uv is available and Python 3.12 toolchain is installed via uv.

        We do not create a root venv here; each module manages its own uv venv.
        """
        if not self._check_uv_available():
            logger.error("\n" + "=" * 60)
            logger.error("uv is required but not found on PATH.")
            logger.error("Use scripts/bootstrap_uv_python.py to install uv safely from official sources.")
            logger.error("Alternatively, install uv manually from https://astral.sh/uv")
            sys.exit(1)

        # Ensure a Python 3.12 runtime is available to uv
        logger.info("Ensuring Python 3.12 toolchain is available via uv...")
        find = self.run_command(["uv", "python", "find", "3.12"], check=False)
        if find.returncode != 0 or not find.stdout.strip():
            logger.info("Python 3.12 not found in uv toolchains. Installing...")
            self.run_command(["uv", "python", "install", "3.12"])
        else:
            logger.info("Python 3.12 already available for uv.")

    def setup_orchestrator_toolchain(self) -> None:
        """Ensure the orchestrator has the required toolchain (uv + Python 3.12)."""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: Ensuring Toolchain (uv + Python 3.12)")
        logger.info("=" * 60)
        self.ensure_uv_and_python()
        logger.info("[OK] Toolchain ready (uv + Python 3.12)")

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

            # Step 2: Ensure toolchain (do not create a root venv)
            self.setup_orchestrator_toolchain()

            # Step 3: Set up all submodules
            self.setup_all_modules()

            logger.info("\n" + "=" * 60)
            if self.module_failures:
                logger.error("[PARTIAL] SETUP COMPLETED WITH FAILURES")
                logger.error("=" * 60)
                logger.error("Failed modules: " + ", ".join(self.module_failures))
                logger.error("Check logs above and re-run their module_setup.py after resolving.")
                logger.info("\nEach submodule manages its own uv virtual environment.")
                return 1
            else:
                logger.info("[OK] SETUP COMPLETE!")
                logger.info("=" * 60)
                logger.info("\nEach submodule manages its own uv virtual environment.")
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
    # Initialize basic logging if not configured by parent
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)8s] %(message)s")
    main()
