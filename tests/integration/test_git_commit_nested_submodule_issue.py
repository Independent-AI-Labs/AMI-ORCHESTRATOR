"""
Integration test to reproduce the git_commit.sh issue with nested submodules.

This test reproduces the issue where git_commit.sh fails when trying to commit
to a nested submodule like 'learning/forecasting', where it tries to access
/home/ami/Projects/AMI-ORCHESTRATOR/learning/forecasting/base/ruff.toml
instead of /home/ami/Projects/AMI-ORCHESTRATOR/base/ruff.toml
"""

import os
import tempfile
import subprocess
import shutil
from pathlib import Path


def test_git_commit_nested_submodule_issue():
    """
    Test that reproduces the git_commit.sh issue with nested submodule paths.
    
    The issue occurs when running:
    ./scripts/git_commit.sh --fix learning/forecasting -F /tmp/commit_msg.txt
    
    Expected to fail with error:
    error: invalid value '/path/to/orchestrator/learning/forecasting/base/ruff.toml' for '--config <CONFIG_OPTION>'
    """
    # Create a temporary directory to simulate the orchestrator structure
    with tempfile.TemporaryDirectory() as temp_dir:
        orchestrator_root = Path(temp_dir) / "ami-orchestrator"
        orchestrator_root.mkdir()
        
        # Create the base directory with ruff.toml (this exists in the real setup)
        base_dir = orchestrator_root / "base"
        base_dir.mkdir()
        (base_dir / "ruff.toml").write_text("# Test ruff config\n")
        
        # Create the learning directory
        learning_dir = orchestrator_root / "learning"
        learning_dir.mkdir()
        
        # Create a .git file in learning to simulate it being a submodule
        (learning_dir / ".git").write_text("gitdir: ../.git/modules/learning\n")
        
        # Create the forecasting directory inside learning
        forecasting_dir = learning_dir / "forecasting"
        forecasting_dir.mkdir()
        
        # Create a .git file in forecasting to simulate it being a nested submodule
        (forecasting_dir / ".git").write_text("gitdir: ../../.git/modules/learning/modules/forecasting\n")
        
        # Create some test files in forecasting to have something to commit
        (forecasting_dir / "test_file.py").write_text("# Test content\n")
        
        # Create a temporary commit message file
        commit_msg_file = Path(temp_dir) / "commit_msg.txt"
        commit_msg_file.write_text("Test commit for forecasting submodule")
        
        # Create a .venv in the orchestrator root to satisfy the script requirements
        venv_dir = orchestrator_root / ".venv"
        venv_dir.mkdir()
        bin_dir = venv_dir / "bin"
        bin_dir.mkdir()
        # Create a mock ruff executable (we'll create a script that just echoes the --config value)
        ruff_mock = bin_dir / "ruff"
        ruff_mock.write_text("#!/bin/bash\nif [[ \$1 == '--config' ]]; then echo \"error: invalid value '\$2' for '--config <CONFIG_OPTION>'\" >&2; exit 1; fi\n")
        ruff_mock.chmod(0o755)
        
        # Create a mock python executable
        python_mock = bin_dir / "python"
        python_mock.write_text("#!/bin/bash\necho 'Python mock'\n")
        python_mock.chmod(0o755)
        
        # Change to orchestrator root
        original_cwd = os.getcwd()
        os.chdir(orchestrator_root)
        
        try:
            # Initialize git repo for the orchestrator root
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
            
            # Stage the files
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            
            # Try to run git_commit.sh on the nested submodule - this should fail with the known issue
            result = subprocess.run([
                "./scripts/git_commit.sh",
                "--fix",  # Use --fix to trigger the ruff configuration usage
                "learning/forecasting",
                "-F", str(commit_msg_file)
            ], capture_output=True, text=True)
            
            print(f"Return code: {result.returncode}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            
            # Check if we reproduced the error (should fail with the path error)
            assert result.returncode != 0
            assert "invalid value" in result.stderr
            assert "learning/forecasting/base/ruff.toml" in result.stderr
            
            print("Successfully reproduced the git_commit.sh nested submodule issue!")
            
        except subprocess.CalledProcessError as e:
            print(f"Command failed (this might be expected): {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            
            # Check if we got the expected error
            if "invalid value" in e.stderr and "learning/forecasting/base/ruff.toml" in e.stderr:
                print("Successfully reproduced the git_commit.sh nested submodule issue!")
            else:
                raise AssertionError("Did not reproduce the expected error")
        
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    test_git_commit_nested_submodule_issue()