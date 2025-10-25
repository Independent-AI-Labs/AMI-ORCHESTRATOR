"""Test suite for automation wrapper scripts.

Tests:
- ami-run.sh (Python execution wrapper)
- ami-uv (UV command wrapper)
- git_commit.sh (Git commit wrapper)
- git_push.sh (Git push wrapper)
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


class TestAmiRun:
    """Test ami-run.sh wrapper script."""

    def test_ami_run_exists(self):
        """Verify ami-run.sh exists and is executable."""
        script = Path("/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh")
        assert script.exists()
        assert script.stat().st_mode & 0o111  # Has execute permission

    def test_ami_run_python_version(self):
        """Test ami-run can execute Python and get version."""
        result = subprocess.run(
            ["/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh", "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Python" in result.stdout

    def test_ami_run_import_check(self):
        """Test ami-run can import standard libraries."""
        result = subprocess.run(
            [
                "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh",
                "-c",
                "import sys; import os; import json; print('SUCCESS')",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "SUCCESS" in result.stdout

    def test_ami_run_module_execution(self):
        """Test ami-run can execute Python modules."""
        result = subprocess.run(
            [
                "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh",
                "-m",
                "json.tool",
            ],
            check=False,
            input='{"key": "value"}',
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "key" in result.stdout


class TestAmiUv:
    """Test ami-uv wrapper script."""

    def test_ami_uv_exists(self):
        """Verify ami-uv exists and is executable."""
        script = Path("/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-uv")
        assert script.exists()
        assert script.stat().st_mode & 0o111  # Has execute permission

    def test_ami_uv_version(self):
        """Test ami-uv can get uv version."""
        result = subprocess.run(
            ["/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-uv", "version"],
            check=False,
            capture_output=True,
            text=True,
        )
        # Should succeed or fail gracefully
        assert result.returncode in (0, 1)

    def test_ami_uv_help(self):
        """Test ami-uv can show help."""
        result = subprocess.run(
            ["/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-uv", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "uv" in result.stdout.lower() or "usage" in result.stdout.lower()


class TestGitCommit:
    """Test git_commit.sh wrapper script."""

    def test_git_commit_exists(self):
        """Verify git_commit.sh exists and is executable."""
        script = Path("/home/ami/Projects/AMI-ORCHESTRATOR/scripts/git_commit.sh")
        assert script.exists()
        assert script.stat().st_mode & 0o111  # Has execute permission

    def test_git_commit_requires_message(self):
        """Test git_commit.sh requires commit message."""
        result = subprocess.run(
            ["/home/ami/Projects/AMI-ORCHESTRATOR/scripts/git_commit.sh"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "message required" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_git_commit_dry_run(self):
        """Test git_commit.sh with mock git repo."""
        # Create temp git repo
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo,
                check=True,
            )

            # Create a file
            test_file = repo / "test.txt"
            test_file.write_text("test content")

            # Copy git_commit.sh to temp repo
            script_src = Path("/home/ami/Projects/AMI-ORCHESTRATOR/scripts/git_commit.sh")
            script_dst = repo / "git_commit.sh"
            script_dst.write_text(script_src.read_text())
            script_dst.chmod(0o755)

            # Run commit script
            result = subprocess.run(
                ["./git_commit.sh", "test commit"],
                check=False,
                cwd=repo,
                capture_output=True,
                text=True,
            )

            # Should succeed
            assert result.returncode == 0

            # Verify commit was created
            log_result = subprocess.run(
                ["git", "log", "--oneline"],
                check=False,
                cwd=repo,
                capture_output=True,
                text=True,
            )
            assert "test commit" in log_result.stdout


class TestGitPush:
    """Test git_push.sh wrapper script."""

    def test_git_push_exists(self):
        """Verify git_push.sh exists and is executable."""
        script = Path("/home/ami/Projects/AMI-ORCHESTRATOR/scripts/git_push.sh")
        assert script.exists()
        assert script.stat().st_mode & 0o111  # Has execute permission

    def test_git_push_checks_for_test_runner(self):
        """Test git_push.sh looks for test runner."""
        # Create temp git repo
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo, check=True)

            # Copy git_push.sh to temp repo
            script_src = Path("/home/ami/Projects/AMI-ORCHESTRATOR/scripts/git_push.sh")
            script_dst = repo / "git_push.sh"
            script_dst.write_text(script_src.read_text())
            script_dst.chmod(0o755)

            # Run push script (should fail - no test runner)
            result = subprocess.run(
                ["./git_push.sh"],
                check=False,
                cwd=repo,
                capture_output=True,
                text=True,
            )

            # Should fail because no test runner found
            assert result.returncode != 0
            assert "run_tests.py" in result.stdout or "test" in result.stdout.lower()


class TestWrapperIntegration:
    """Integration tests for wrapper scripts."""

    def test_ami_run_finds_venv(self):
        """Test ami-run can find and use .venv."""
        result = subprocess.run(
            [
                "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh",
                "-c",
                "import sys; print(sys.prefix)",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd="/home/ami/Projects/AMI-ORCHESTRATOR",
        )
        assert result.returncode == 0
        assert ".venv" in result.stdout

    def test_wrapper_scripts_use_bash(self):
        """Verify wrapper scripts use bash shebang."""
        wrappers = [
            "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh",
            "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-uv",
            "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/git_commit.sh",
            "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/git_push.sh",
        ]

        for wrapper in wrappers:
            path = Path(wrapper)
            if path.exists():
                first_line = path.read_text().split("\n")[0]
                assert first_line.startswith("#!"), f"{wrapper} missing shebang"
                assert "bash" in first_line.lower(), f"{wrapper} not using bash"

    def test_wrapper_scripts_have_error_handling(self):
        """Verify wrapper scripts have set -e or set -euo pipefail."""
        wrappers = [
            "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh",
            "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-uv",
            "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/git_commit.sh",
            "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/git_push.sh",
        ]

        for wrapper in wrappers:
            path = Path(wrapper)
            if path.exists():
                content = path.read_text()
                # Check for error handling (set -e or set -euo pipefail)
                assert "set -e" in content or "set -u" in content, f"{wrapper} missing error handling (set -e/-u)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
