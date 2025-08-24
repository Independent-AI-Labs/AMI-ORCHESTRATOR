#!/usr/bin/env python
"""AMI Orchestrator Master Setup Script.

This script:
1. Initializes and syncs all git submodules
2. Sets up each submodule's virtual environment and dependencies
3. Installs pre-commit hooks for all modules
"""

import subprocess
import sys
from pathlib import Path


class OrchestratorSetup:
    """Master setup for AMI Orchestrator and all submodules."""

    def __init__(self):
        """Initialize orchestrator setup."""
        self.root_dir = Path(__file__).parent.resolve()
        self.submodules = [
            "base",
            "browser",
            "compliance",
            "domains",
            "files",
            "streams",
            "ux",
        ]

    def run_command(self, cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
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
            
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            if check:
                sys.exit(1)
                
        return result

    def init_submodules(self) -> None:
        """Initialize and sync all git submodules."""
        print("\n" + "=" * 60)
        print("STEP 1: Initializing Git Submodules")
        print("=" * 60)
        
        # Initialize submodules
        self.run_command(["git", "submodule", "init"])
        
        # Sync submodule URLs
        self.run_command(["git", "submodule", "sync", "--recursive"])
        
        # Update submodules
        self.run_command(["git", "submodule", "update", "--init", "--recursive"])
        
        print("✓ All submodules initialized and synced")

    def setup_module(self, module_name: str) -> None:
        """Set up a single module's environment.
        
        Args:
            module_name: Name of the module to set up
        """
        module_path = self.root_dir / module_name
        
        if not module_path.exists():
            print(f"⚠ Module {module_name} not found, skipping")
            return
            
        print(f"\n--- Setting up {module_name} module ---")
        
        # Check if setup.py exists
        setup_script = module_path / "setup.py"
        if not setup_script.exists():
            print(f"⚠ No setup.py found in {module_name}, skipping")
            return
            
        # Run the module's setup.py
        result = self.run_command(
            [sys.executable, "setup.py"],
            cwd=module_path,
            check=False
        )
        
        if result.returncode == 0:
            print(f"✓ {module_name} module setup complete")
        else:
            print(f"✗ {module_name} module setup failed")
            print(f"  Error: {result.stderr}")

    def setup_orchestrator_venv(self) -> None:
        """Set up the orchestrator's own virtual environment."""
        print("\n" + "=" * 60)
        print("STEP 2: Setting up Orchestrator Environment")
        print("=" * 60)
        
        venv_path = self.root_dir / ".venv"
        
        # Check if uv is available
        try:
            self.run_command(["uv", "--version"], check=False)
            has_uv = True
        except FileNotFoundError:
            has_uv = False
            print("⚠ uv not found, using standard venv")
        
        if has_uv:
            # Create venv with uv
            if not venv_path.exists():
                print("Creating virtual environment with uv...")
                self.run_command(["uv", "venv", ".venv"])
            
            # Install base requirements
            base_reqs = self.root_dir / "base" / "requirements.txt"
            if base_reqs.exists():
                print("Installing base requirements...")
                self.run_command(["uv", "pip", "install", "-r", str(base_reqs)])
            
            # Install base test requirements
            base_test_reqs = self.root_dir / "base" / "requirements-test.txt"
            if base_test_reqs.exists():
                print("Installing base test requirements...")
                self.run_command(["uv", "pip", "install", "-r", str(base_test_reqs)])
                
            # Install orchestrator requirements if they exist
            orch_reqs = self.root_dir / "requirements.txt"
            if orch_reqs.exists():
                print("Installing orchestrator requirements...")
                self.run_command(["uv", "pip", "install", "-r", str(orch_reqs)])
                
        else:
            # Fallback to standard venv
            if not venv_path.exists():
                print("Creating virtual environment...")
                self.run_command([sys.executable, "-m", "venv", ".venv"])
            
            # Get pip path
            if sys.platform == "win32":
                pip_path = venv_path / "Scripts" / "pip.exe"
            else:
                pip_path = venv_path / "bin" / "pip"
            
            # Install requirements
            base_reqs = self.root_dir / "base" / "requirements.txt"
            if base_reqs.exists():
                print("Installing base requirements...")
                self.run_command([str(pip_path), "install", "-r", str(base_reqs)])
            
            base_test_reqs = self.root_dir / "base" / "requirements-test.txt"
            if base_test_reqs.exists():
                print("Installing base test requirements...")
                self.run_command([str(pip_path), "install", "-r", str(base_test_reqs)])
        
        # Install pre-commit hooks for orchestrator
        self.install_precommit_hooks(self.root_dir)
        
        print("✓ Orchestrator environment setup complete")

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
            print(f"Installing pre-commit hooks in {module_path.name}...")
            self.run_command(
                [str(python_path), "-m", "pre_commit", "install"],
                cwd=module_path,
                check=False
            )
            self.run_command(
                [str(python_path), "-m", "pre_commit", "install", "--hook-type", "pre-push"],
                cwd=module_path,
                check=False
            )

    def setup_all_modules(self) -> None:
        """Set up all submodules."""
        print("\n" + "=" * 60)
        print("STEP 3: Setting up All Submodules")
        print("=" * 60)
        
        # Base module must be set up first
        if "base" in self.submodules:
            self.setup_module("base")
            self.submodules.remove("base")
        
        # Set up remaining modules
        for module in self.submodules:
            self.setup_module(module)

    def run(self) -> int:
        """Run the complete orchestrator setup.
        
        Returns:
            Exit code (0 for success)
        """
        print("\n" + "=" * 60)
        print("AMI ORCHESTRATOR COMPLETE SETUP")
        print("=" * 60)
        
        try:
            # Step 1: Initialize submodules
            self.init_submodules()
            
            # Step 2: Set up orchestrator environment
            self.setup_orchestrator_venv()
            
            # Step 3: Set up all submodules
            self.setup_all_modules()
            
            print("\n" + "=" * 60)
            print("✓ SETUP COMPLETE!")
            print("=" * 60)
            print("\nTo activate the orchestrator environment:")
            if sys.platform == "win32":
                print("  .venv\\Scripts\\activate")
            else:
                print("  source .venv/bin/activate")
            print("\nEach submodule has its own .venv in its directory.")
            print("Pre-commit hooks have been installed for all modules.")
            
            return 0
            
        except Exception as e:
            print(f"\n✗ Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    """Main entry point."""
    setup = OrchestratorSetup()
    sys.exit(setup.run())


if __name__ == "__main__":
    main()