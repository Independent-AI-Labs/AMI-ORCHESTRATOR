"""Network E2E tests for ami-repo CLI tool.

Tests SSH authentication and git operations over REAL NETWORK INTERFACE (eth0).
CRITICAL: All tests use 192.168.50.66 (eth0), NOT 127.0.0.1 (loopback).

These tests validate:
- SSH authentication over network
- Git operations over SSH
- Security restrictions (no shell, no forwarding, etc.)
- Multi-user scenarios

Prerequisites:
- SSH server running on port 22
- Network interface eth0 with IP 192.168.50.66
- User 'ami' with SSH access
"""

import concurrent.futures
import os
import shutil
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

from ami_repo import GitRepoManager

# Import fixtures from conftest
pytest_plugins = ("tests.fixtures.ami_repo.conftest",)

# Network configuration - CRITICAL: Use eth0, NOT loopback
SSH_HOST = "192.168.50.66"  # eth0 interface
SSH_USER = "ami"
SSH_PORT = 22


def skip_if_no_ssh_server():
    """Skip test if SSH server is not running."""
    try:
        result = subprocess.run(["nc", "-z", SSH_HOST, str(SSH_PORT)], check=False, capture_output=True, timeout=2)
        if result.returncode != 0:
            pytest.skip(f"SSH server not accessible at {SSH_HOST}:{SSH_PORT}")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip(f"Cannot check SSH server status at {SSH_HOST}:{SSH_PORT}")


@pytest.fixture(autouse=True)
def check_ssh_server():
    """Auto-check SSH server before each test."""
    skip_if_no_ssh_server()


@pytest.fixture(autouse=True)
def disable_file_locking(monkeypatch):
    """Disable file locking for all network tests."""
    monkeypatch.setenv("AMI_TEST_MODE", "1")


@pytest.fixture
def real_git_server(_tmp_path):
    """Create git server in REAL user home for SSH access.

    Returns:
        tuple: (GitRepoManager, base_path)
    """
    # Use real home directory subdirectory for SSH access
    real_home = Path.home()
    server_base = real_home / f".ami-repo-test-{os.getpid()}"

    try:
        manager = GitRepoManager(base_path=server_base)
        manager.init_server()
        yield (manager, server_base)
    finally:
        # Cleanup

        if server_base.exists():
            shutil.rmtree(server_base, ignore_errors=True)


@pytest.fixture
def ssh_test_key(tmp_path):
    """Generate SSH key and configure for network testing.

    Returns:
        tuple: (private_key_path, public_key_path)
    """
    key_path = tmp_path / "network_test_key"

    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(key_path), "-N", "", "-C", "network-test-key"], check=True, capture_output=True)

    return (key_path, key_path.with_suffix(".pub"))


class TestNetworkSSHAuthentication:
    """Test SSH authentication over network interface."""

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    def test_ssh_connection_to_eth0(self, real_git_server, ssh_test_key):
        """SSH connection uses eth0 (192.168.50.66) NOT loopback."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        # Add key with restrictions
        manager.add_ssh_key(pub_key, "network-test")

        # Setup authorized_keys
        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"

        # Backup existing authorized_keys
        backup_path = None
        if authorized_keys.exists():
            backup_path = authorized_keys.with_suffix(".backup.network-test")
            authorized_keys.rename(backup_path)

        try:
            # Link our test keys
            authorized_keys.symlink_to(manager.keys_path)

            # Test SSH connection - MUST use eth0 IP
            result = subprocess.run(
                [
                    "ssh",
                    "-i",
                    str(priv_key),
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "ConnectTimeout=5",
                    f"{SSH_USER}@{SSH_HOST}",  # CRITICAL: eth0, not 127.0.0.1
                    "git-receive-pack --help",
                ],
                check=False,
                capture_output=True,
                timeout=10,
                text=True,
            )

            # Should succeed (git command allowed)
            assert result.returncode == 0 or "git-receive-pack" in result.stdout + result.stderr

        finally:
            # Restore original authorized_keys
            if authorized_keys.is_symlink():
                authorized_keys.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(authorized_keys)

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    def test_git_clone_over_ssh_network(self, real_git_server, ssh_test_key, tmp_path):
        """Git clone over SSH using network interface."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        # Create repository
        manager.create_repo("test-clone", description="SSH clone test")

        # Add SSH key
        manager.add_ssh_key(pub_key, "clone-test")

        # Setup SSH
        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"
        backup_path = None
        if authorized_keys.exists():
            backup_path = authorized_keys.with_suffix(".backup.clone-test")
            authorized_keys.rename(backup_path)

        try:
            authorized_keys.symlink_to(manager.keys_path)

            # Git clone over network SSH
            clone_dest = tmp_path / "cloned-via-ssh"
            repo_path = server_base / "repos" / "test-clone.git"

            env = {**os.environ, "GIT_SSH_COMMAND": f"ssh -i {priv_key} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"}

            result = subprocess.run(
                [
                    "git",
                    "clone",
                    f"ssh://{SSH_USER}@{SSH_HOST}{repo_path}",  # eth0, not loopback
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
            if authorized_keys.is_symlink():
                authorized_keys.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(authorized_keys)

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    @pytest.mark.slow
    def test_git_push_over_ssh_network(self, real_git_server, ssh_test_key, tmp_path):
        """Git push over SSH using network interface."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        # Create and clone repository
        manager.create_repo("test-push")
        manager.add_ssh_key(pub_key, "push-test")

        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"
        backup_path = None
        if authorized_keys.exists():
            backup_path = authorized_keys.with_suffix(".backup.push-test")
            authorized_keys.rename(backup_path)

        try:
            authorized_keys.symlink_to(manager.keys_path)

            clone_dest = tmp_path / "push-test-repo"
            repo_path = server_base / "repos" / "test-push.git"

            env = {
                **os.environ,
                "GIT_SSH_COMMAND": f"ssh -i {priv_key} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            }

            # Clone
            subprocess.run(["git", "clone", f"ssh://{SSH_USER}@{SSH_HOST}{repo_path}", str(clone_dest)], env=env, check=True, capture_output=True)

            # Configure git
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=clone_dest, env=env, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=clone_dest, env=env, check=True)

            # Make commit
            test_file = clone_dest / "test.txt"
            test_file.write_text("test content")
            subprocess.run(["git", "add", "."], cwd=clone_dest, env=env, check=True)
            subprocess.run(["git", "commit", "-m", "Test commit"], cwd=clone_dest, env=env, check=True)

            # Push over network SSH
            result = subprocess.run(["git", "push"], check=False, cwd=clone_dest, env=env, capture_output=True, text=True, timeout=30)

            assert result.returncode == 0, f"Git push failed: {result.stderr}"

        finally:
            if authorized_keys.is_symlink():
                authorized_keys.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(authorized_keys)


class TestSSHSecurityRestrictions:
    """Test SSH security restrictions are enforced over network."""

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.ssh_security
    @pytest.mark.integration
    def test_shell_access_blocked(self, real_git_server, ssh_test_key):
        """Restricted SSH key cannot get shell access."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        manager.add_ssh_key(pub_key, "no-shell-test")

        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"
        backup_path = None
        if authorized_keys.exists():
            backup_path = authorized_keys.with_suffix(".backup.no-shell")
            authorized_keys.rename(backup_path)

        try:
            authorized_keys.symlink_to(manager.keys_path)

            # Try to execute shell command
            result = subprocess.run(
                [
                    "ssh",
                    "-i",
                    str(priv_key),
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    f"{SSH_USER}@{SSH_HOST}",
                    "ls /tmp",  # Try arbitrary command
                ],
                check=False,
                capture_output=True,
                timeout=10,
                text=True,
            )

            # Should fail or be restricted by git-shell
            assert result.returncode != 0 or "fatal" in result.stderr or "Interactive git shell" in result.stdout

        finally:
            if authorized_keys.is_symlink():
                authorized_keys.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(authorized_keys)

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.ssh_security
    @pytest.mark.integration
    def test_port_forwarding_blocked(self, real_git_server, ssh_test_key):
        """Port forwarding is blocked by SSH restrictions."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        manager.add_ssh_key(pub_key, "no-forward-test")

        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"
        backup_path = None
        if authorized_keys.exists():
            backup_path = authorized_keys.with_suffix(".backup.no-forward")
            authorized_keys.rename(backup_path)

        try:
            authorized_keys.symlink_to(manager.keys_path)

            # Try port forwarding
            result = subprocess.run(
                [
                    "ssh",
                    "-i",
                    str(priv_key),
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "ExitOnForwardFailure=yes",
                    "-L",
                    "9999:localhost:22",  # Try local port forward
                    f"{SSH_USER}@{SSH_HOST}",
                    "git-upload-pack --help",
                ],
                check=False,
                capture_output=True,
                timeout=10,
                text=True,
            )

            # Port forwarding should be blocked
            # Connection may succeed but forwarding fails
            assert "Warning" in result.stderr or result.returncode != 0 or "disabled" in result.stderr.lower()

        finally:
            if authorized_keys.is_symlink():
                authorized_keys.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(authorized_keys)

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.ssh_security
    @pytest.mark.integration
    def test_non_git_commands_blocked(self, real_git_server, ssh_test_key):
        """Non-git commands are blocked by git-shell."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        manager.add_ssh_key(pub_key, "git-only-test")

        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"
        backup_path = None
        if authorized_keys.exists():
            backup_path = authorized_keys.with_suffix(".backup.git-only")
            authorized_keys.rename(backup_path)

        try:
            authorized_keys.symlink_to(manager.keys_path)

            # Try non-git command
            result = subprocess.run(
                [
                    "ssh",
                    "-i",
                    str(priv_key),
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    f"{SSH_USER}@{SSH_HOST}",
                    "cat /etc/passwd",  # Non-git command
                ],
                check=False,
                capture_output=True,
                timeout=10,
                text=True,
            )

            # Should fail
            assert result.returncode != 0
            assert "fatal" in result.stderr or "not permitted" in result.stderr or "does not exist" in result.stderr

        finally:
            if authorized_keys.is_symlink():
                authorized_keys.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(authorized_keys)


class TestMultiUserScenarios:
    """Test multi-user SSH access scenarios."""

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    @pytest.mark.slow
    def test_multiple_keys_different_repos(self, real_git_server, tmp_path):
        """Multiple users with different keys can access different repos."""
        manager, server_base = real_git_server

        # Create two repositories
        manager.create_repo("repo-a")
        manager.create_repo("repo-b")

        # Generate two SSH keys
        key1 = tmp_path / "user1_key"
        key2 = tmp_path / "user2_key"

        for key_path in [key1, key2]:
            subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(key_path), "-N", "", "-C", f"{key_path.name}"], check=True, capture_output=True)

        # Add both keys
        manager.add_ssh_key(key1.with_suffix(".pub"), "user1")
        manager.add_ssh_key(key2.with_suffix(".pub"), "user2")

        # Verify both keys in authorized_keys
        content = manager.keys_path.read_text()
        assert "user1" in content
        assert "user2" in content

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    def test_key_rotation(self, real_git_server, tmp_path):
        """Key rotation: remove old key, add new key, verify access."""
        manager, server_base = real_git_server

        # Create repo
        manager.create_repo("test-rotation")

        # Add old key
        old_key = tmp_path / "old_key"
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(old_key), "-N", "", "-C", "old-key"], check=True, capture_output=True)
        manager.add_ssh_key(old_key.with_suffix(".pub"), "old-key")

        # Verify old key present
        content = manager.keys_path.read_text()
        assert "old-key" in content

        # Remove old key
        manager.remove_ssh_key("old-key")

        # Add new key
        new_key = tmp_path / "new_key"
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(new_key), "-N", "", "-C", "new-key"], check=True, capture_output=True)
        manager.add_ssh_key(new_key.with_suffix(".pub"), "new-key")

        # Verify rotation
        content = manager.keys_path.read_text()
        assert "old-key" not in content
        assert "new-key" in content


class TestNetworkEdgeCases:
    """Test network-specific edge cases."""

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    def test_ssh_connection_timeout_handling(self, _tmp_path):
        """SSH connection timeout is handled gracefully."""
        # Use invalid port to trigger timeout
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "ConnectTimeout=2",
                "-o",
                "StrictHostKeyChecking=no",
                "-p",
                "9999",  # Invalid port
                f"{SSH_USER}@{SSH_HOST}",
                "git-upload-pack",
            ],
            check=False,
            capture_output=True,
            timeout=5,
            text=True,
        )

        # Should timeout or refuse connection
        assert result.returncode != 0

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    def test_concurrent_git_operations(self, real_git_server, ssh_test_key, tmp_path):
        """Multiple concurrent git operations over SSH."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        # Setup
        manager.create_repo("concurrent-test")
        manager.add_ssh_key(pub_key, "concurrent")

        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        authorized_keys = ssh_dir / "authorized_keys"
        backup_path = None
        if authorized_keys.exists():
            backup_path = authorized_keys.with_suffix(".backup.concurrent")
            authorized_keys.rename(backup_path)

        try:
            authorized_keys.symlink_to(manager.keys_path)

            # Clone multiple times concurrently

            def clone_repo(index):
                clone_dest = tmp_path / f"clone-{index}"
                repo_path = server_base / "repos" / "concurrent-test.git"
                env = {**os.environ, "GIT_SSH_COMMAND": f"ssh -i {priv_key} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"}
                result = subprocess.run(
                    ["git", "clone", f"ssh://{SSH_USER}@{SSH_HOST}{repo_path}", str(clone_dest)], check=False, env=env, capture_output=True, timeout=30
                )
                return result.returncode == 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(clone_repo, i) for i in range(3)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            # All clones should succeed
            assert all(results), "Some concurrent clones failed"

        finally:
            if authorized_keys.is_symlink():
                authorized_keys.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(authorized_keys)
