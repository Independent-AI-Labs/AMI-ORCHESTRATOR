"""Network SSH authentication tests for ami-repo CLI tool.

Tests SSH authentication and basic git operations over localhost.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Add scripts and fixtures to path
root_dir = Path(__file__).resolve().parents[2]
scripts_dir = root_dir / "scripts"
fixtures_dir = root_dir / "tests" / "fixtures" / "ami_repo"
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(fixtures_dir))


# Import shared fixtures and functions
from tests.integration.conftest import (
    SHARED_AUTHORIZED_KEYS_PATH,
    SSH_HOST,
    SSH_PORT,
    SSH_USER,
    add_key_to_shared_authorized_keys,
    remove_key_from_shared_authorized_keys,
)

# Import fixtures from main conftest
pytest_plugins = ("tests.fixtures.ami_repo.conftest",)


class TestNetworkSSHAuthentication:
    """Test SSH authentication over network interface."""

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    def test_ssh_connection_to_localhost(self, real_git_server, ssh_test_key):
        """SSH connection uses localhost instead of eth0."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        # Add key to shared authorized_keys with restrictions
        add_key_to_shared_authorized_keys(pub_key, "network-test")

        # Setup authorized_keys (for local SSH operations if needed)
        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"

        # Backup existing authorized_keys
        backup_path = None
        if authorized_keys.exists():
            backup_path = authorized_keys.with_suffix(".backup.network-test")
            authorized_keys.rename(backup_path)

        try:
            # Link to the shared authorized_keys file instead
            authorized_keys.symlink_to(SHARED_AUTHORIZED_KEYS_PATH)

            # Test SSH connection - now using localhost
            # Test with git-shell help to see if command execution is allowed (this is a valid git-shell command)
            result = subprocess.run(
                [
                    "ssh",
                    "-i",
                    str(priv_key),
                    "-p",
                    str(SSH_PORT),
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "ConnectTimeout=5",
                    f"{SSH_USER}@{SSH_HOST}",  # Now using localhost
                    "help",
                ],
                check=False,
                capture_output=True,
                timeout=10,
                text=True,
            )

            # Should succeed - the important part is that authentication works, not the specific result
            # Git-shell authentication is working if we don't get "Permission denied (publickey)"
            assert "Permission denied" not in result.stderr

        finally:
            # Remove the key from shared authorized_keys
            remove_key_from_shared_authorized_keys("network-test")

            # Restore original authorized_keys
            if authorized_keys.is_symlink():
                authorized_keys.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(authorized_keys)

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    def test_git_clone_over_ssh_network(self, real_git_server, ssh_test_key, tmp_path):
        """Git clone over SSH using localhost."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        # Create repository
        manager.create_repo("test-clone", description="SSH clone test")

        # Add SSH key to shared authorized_keys
        add_key_to_shared_authorized_keys(pub_key, "clone-test")

        # Setup SSH
        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"
        backup_path = None
        if authorized_keys.exists():
            backup_path = authorized_keys.with_suffix(".backup.clone-test")
            authorized_keys.rename(backup_path)

        try:
            authorized_keys.symlink_to(SHARED_AUTHORIZED_KEYS_PATH)

            # Git clone over SSH using localhost
            clone_dest = tmp_path / "cloned-via-ssh"
            repo_path = server_base / "repos" / "test-clone.git"

            env = {**os.environ, "GIT_SSH_COMMAND": f"ssh -i {priv_key} -p {SSH_PORT} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"}

            result = subprocess.run(
                [
                    "git",
                    "clone",
                    f"ssh://{SSH_USER}@{SSH_HOST}:{SSH_PORT}{repo_path}",  # Using localhost
                    str(clone_dest),
                ],
                check=False,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0, f"Git clone failed: {result.stderr}"
            assert clone_dest.exists()
            assert (clone_dest / ".git").exists()

        finally:
            # Remove the key from shared authorized_keys
            remove_key_from_shared_authorized_keys("clone-test")

            if authorized_keys.is_symlink():
                authorized_keys.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(authorized_keys)

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    @pytest.mark.slow
    def test_git_push_over_ssh_network(self, real_git_server, ssh_test_key, tmp_path):
        """Git push over SSH using localhost."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        # Create repository
        manager.create_repo("test-push")

        # Add SSH key to shared authorized_keys
        add_key_to_shared_authorized_keys(pub_key, "push-test")

        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"
        backup_path = None
        if authorized_keys.exists():
            backup_path = authorized_keys.with_suffix(".backup.push-test")
            authorized_keys.rename(backup_path)

        try:
            authorized_keys.symlink_to(SHARED_AUTHORIZED_KEYS_PATH)

            clone_dest = tmp_path / "push-test-repo"
            repo_path = server_base / "repos" / "test-push.git"

            env = {
                **os.environ,
                "GIT_SSH_COMMAND": f"ssh -i {priv_key} -p {SSH_PORT} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            }

            # Clone
            subprocess.run(["git", "clone", f"ssh://{SSH_USER}@{SSH_HOST}:{SSH_PORT}{repo_path}", str(clone_dest)], env=env, check=True, capture_output=True)

            # Configure git
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=clone_dest, env=env, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=clone_dest, env=env, check=True)

            # Make commit
            test_file = clone_dest / "test.txt"
            test_file.write_text("test content")
            subprocess.run(["git", "add", "."], cwd=clone_dest, env=env, check=True)
            subprocess.run(["git", "commit", "-m", "Test commit"], cwd=clone_dest, env=env, check=True)

            # Push over SSH using localhost
            result = subprocess.run(["git", "push"], check=False, cwd=clone_dest, env=env, capture_output=True, text=True, timeout=30)

            assert result.returncode == 0, f"Git push failed: {result.stderr}"

        finally:
            # Remove the key from shared authorized_keys
            remove_key_from_shared_authorized_keys("push-test")

            if authorized_keys.is_symlink():
                authorized_keys.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(authorized_keys)
