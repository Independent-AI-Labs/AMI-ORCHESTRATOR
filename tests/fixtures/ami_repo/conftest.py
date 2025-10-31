"""Shared pytest fixtures for ami-repo tests."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent
TEST_KEYS_DIR = FIXTURES_DIR / "test_keys"

# Network configuration for network tests
SSH_HOST = "192.168.50.66"  # eth0 interface, NOT loopback
SSH_USER = "ami"
SSH_PORT = 22


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to ami-repo fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def test_keys_dir() -> Path:
    """Return path to test SSH keys directory."""
    return TEST_KEYS_DIR


@pytest.fixture
def temp_git_server(tmp_path):
    """Create temporary git server directory structure.

    Returns:
        Path to initialized git server base directory
    """
    server_base = tmp_path / "git-server"
    server_base.mkdir()

    repos_dir = server_base / "repos"
    repos_dir.mkdir()

    return server_base


@pytest.fixture
def ssh_key_pair(tmp_path):
    """Generate temporary SSH key pair.

    Returns:
        tuple: (private_key_path, public_key_path)
    """
    key_path = tmp_path / "test_temp_key"

    subprocess.run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(key_path),
            "-N",
            "",  # No passphrase
            "-C",
            "temp-test-key",
        ],
        check=True,
        capture_output=True,
    )

    return (key_path, key_path.with_suffix(".pub"))


@pytest.fixture
def test_repo_with_commits(tmp_path):
    """Create a git repository with test commits.

    Returns:
        Path to git repository with commits
    """
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()

    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}

    # Initialize repo
    subprocess.run(["git", "init"], cwd=repo_dir, env=env, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, env=env, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, env=env, check=True)

    # Create test commits
    for i in range(3):
        test_file = repo_dir / f"file{i}.txt"
        test_file.write_text(f"Test content {i}")
        subprocess.run(["git", "add", "."], cwd=repo_dir, env=env, check=True)
        subprocess.run(["git", "commit", "-m", f"Test commit {i}"], cwd=repo_dir, env=env, check=True)

    return repo_dir


@pytest.fixture
def network_ssh_config(tmp_path):
    """Create SSH config for network tests.

    Returns:
        tuple: (ssh_config_path, host, user)
    """
    ssh_config_path = tmp_path / "ssh_config"

    # SSH config pointing to eth0 interface (NOT loopback)
    config_content = f"""
Host git-test-server
    HostName {SSH_HOST}
    User {SSH_USER}
    Port {SSH_PORT}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    IdentitiesOnly yes
"""

    ssh_config_path.write_text(config_content)

    return (ssh_config_path, SSH_HOST, SSH_USER)


@pytest.fixture
def git_repo_manager(tmp_path):
    """Create GitRepoManager instance with temporary base path.

    Returns:
        GitRepoManager instance
    """
    # Import here to avoid import errors if module not available
    import sys
    from pathlib import Path

    # Add scripts directory to path
    scripts_dir = Path(__file__).resolve().parents[3] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from ami_repo import GitRepoManager

    base_path = tmp_path / "git-repos"
    manager = GitRepoManager(base_path=base_path)

    return manager


@pytest.fixture(autouse=True)
def disable_file_locking(monkeypatch):
    """Disable file locking for all tests."""
    monkeypatch.setenv("AMI_TEST_MODE", "1")


@pytest.fixture
def clean_ssh_dir(tmp_path, monkeypatch):
    """Provide clean temporary .ssh directory for tests.

    Returns:
        Path to temporary .ssh directory
    """
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(mode=0o700)

    # Redirect HOME to tmp_path for tests
    monkeypatch.setenv("HOME", str(tmp_path))

    return ssh_dir
