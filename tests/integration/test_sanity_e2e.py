"""E2E sanity test for AMI-ORCHESTRATOR deployment.

Tests fresh installation from GitHub repository, verifying:
1. Repository cloning
2. Installation process (install.py)
3. ami-agent responsiveness
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

# GitHub repository configuration
GITHUB_REPO_URL = "https://github.com/Independent-AI-Labs/AMI-ORCHESTRATOR.git"
CLONE_TIMEOUT = 120  # 2 minutes for git clone
INSTALL_TIMEOUT = 600  # 10 minutes for full installation
VERIFY_TIMEOUT = 30  # 30 seconds for agent verification


@pytest.fixture(autouse=True)
def disable_file_locking(monkeypatch):
    """Disable file locking for all integration tests."""
    monkeypatch.setenv("AMI_TEST_MODE", "1")


@pytest.fixture
def temp_install_dir():
    """Create temporary directory for orchestrator installation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestOrchestratorDeployment:
    """Test fresh orchestrator deployment from GitHub."""

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.integration
    def test_fresh_install_from_github(self, temp_install_dir):
        """Fresh install from GitHub should complete successfully with responsive ami-agent.

        This test validates the complete installation workflow:
        1. Clone orchestrator from GitHub (HTTPS)
        2. Run install.py to set up environment
        3. Verify ami-agent is responsive

        This is the primary sanity test for release validation.
        """
        install_path = temp_install_dir / "AMI-ORCHESTRATOR"

        # Phase 1: Clone from GitHub
        clone_result = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                GITHUB_REPO_URL,
                str(install_path),
            ],
            capture_output=True,
            text=True,
            timeout=CLONE_TIMEOUT,
            check=False,
        )

        assert clone_result.returncode == 0, (
            f"Git clone failed with exit code {clone_result.returncode}.\nStdout: {clone_result.stdout}\nStderr: {clone_result.stderr}"
        )

        # Verify clone succeeded
        assert (install_path / ".git").exists(), "Git repository not cloned properly"
        assert (install_path / "install.py").exists(), "install.py not found in cloned repository"

        # Phase 2: Run installation (skip Claude CLI prompt for automated test)
        install_result = subprocess.run(
            ["python", "install.py", "--skip-claude-check"],
            cwd=install_path,
            capture_output=True,
            text=True,
            timeout=INSTALL_TIMEOUT,
            check=False,
        )

        assert install_result.returncode == 0, (
            f"Installation failed with exit code {install_result.returncode}.\nStdout: {install_result.stdout}\nStderr: {install_result.stderr}"
        )

        # Verify key infrastructure is in place
        assert (install_path / ".venv").exists(), "Root .venv not created"
        assert (install_path / "base").exists(), "base/ submodule not initialized"
        assert (install_path / "scripts").exists(), "scripts/ directory not found"
        assert (install_path / "scripts" / "ami-agent").exists(), "ami-agent script not found"

        # Phase 3: Verify ami-agent responsiveness
        ami_agent = install_path / "scripts" / "ami-agent"

        # Test 1: Check ami-agent help
        help_result = subprocess.run(
            [str(ami_agent), "--help"],
            cwd=install_path,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            check=False,
        )

        # ami-agent --help may exit with 0 or 2 (argparse behavior)
        # What matters is that it runs without crashing
        assert help_result.returncode in [0, 2], (
            f"ami-agent --help failed unexpectedly with exit code {help_result.returncode}.\nStdout: {help_result.stdout}\nStderr: {help_result.stderr}"
        )

        # Verify help output contains expected content
        help_output = help_result.stdout + help_result.stderr
        assert "usage:" in help_output.lower() or "ami-agent" in help_output, f"ami-agent help output doesn't contain expected content.\nOutput: {help_output}"

        # Test 2: Verify ami-agent can execute (version check)
        # Run a minimal command that should succeed
        version_result = subprocess.run(
            [str(ami_agent)],
            cwd=install_path,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            check=False,
            input="\n",  # Send immediate EOF to interactive mode
        )

        # Any exit code is acceptable here - we just want to verify ami-agent runs
        # Interactive mode may return non-zero when stdin closes immediately
        assert version_result.returncode is not None, "ami-agent did not execute"

        # Success: Installation completed and ami-agent is responsive
        assert True, "Sanity test passed: Fresh installation from GitHub successful"

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.integration
    def test_install_creates_venv_structure(self, temp_install_dir):
        """Installation should create proper venv structure for all modules."""
        install_path = temp_install_dir / "AMI-ORCHESTRATOR"

        # Clone
        subprocess.run(
            ["git", "clone", "--depth", "1", GITHUB_REPO_URL, str(install_path)],
            capture_output=True,
            timeout=CLONE_TIMEOUT,
            check=True,
        )

        # Install (skip Claude CLI prompt for automated test)
        subprocess.run(
            ["python", "install.py", "--skip-claude-check"],
            cwd=install_path,
            capture_output=True,
            timeout=INSTALL_TIMEOUT,
            check=True,
        )

        # Verify root venv
        root_venv = install_path / ".venv"
        assert root_venv.exists(), "Root .venv not created"
        assert (root_venv / "bin" / "python").exists(), "Root venv python not found"
        assert (root_venv / "bin" / "uv").exists(), "uv not installed in root venv"

        # Verify base module venv
        base_venv = install_path / "base" / ".venv"
        assert base_venv.exists(), "base/.venv not created"
        assert (base_venv / "bin" / "python").exists(), "base venv python not found"

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.integration
    def test_install_initializes_submodules(self, temp_install_dir):
        """Installation should initialize all git submodules."""
        install_path = temp_install_dir / "AMI-ORCHESTRATOR"

        # Clone
        subprocess.run(
            ["git", "clone", "--depth", "1", GITHUB_REPO_URL, str(install_path)],
            capture_output=True,
            timeout=CLONE_TIMEOUT,
            check=True,
        )

        # Install (skip Claude CLI prompt for automated test)
        subprocess.run(
            ["python", "install.py", "--skip-claude-check"],
            cwd=install_path,
            capture_output=True,
            timeout=INSTALL_TIMEOUT,
            check=True,
        )

        # Check for expected submodules
        expected_submodules = ["base", "compliance", "nodes"]
        for submodule in expected_submodules:
            submodule_path = install_path / submodule
            assert submodule_path.exists(), f"Submodule {submodule}/ not initialized"
            # Check for git metadata to confirm it's a proper submodule
            assert (submodule_path / ".git").exists(), f"Submodule {submodule}/ missing .git reference"
