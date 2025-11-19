"""Network security tests for ami-repo CLI tool.

Tests SSH security restrictions over localhost.
"""

import subprocess
import sys
from pathlib import Path

# Add scripts and fixtures to path
root_dir = Path(__file__).resolve().parents[2]
scripts_dir = root_dir / "scripts"
sys.path.insert(0, str(scripts_dir))

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


def test_shell_access_blocked(real_git_server, ssh_test_key):
    """Test that shell access is blocked via git-shell restrictions."""
    # Unpack fixture values
    manager, server_base = real_git_server
    priv_key, pub_key = ssh_test_key

    # Add key to shared authorized_keys with restrictions
    add_key_to_shared_authorized_keys(pub_key, "shell-test")

    # Setup authorized_keys
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    authorized_keys = ssh_dir / "authorized_keys"
    backup_path = None
    if authorized_keys.exists():
        backup_path = authorized_keys.with_suffix(".backup.shell-test")
        authorized_keys.rename(backup_path)

    try:
        authorized_keys.symlink_to(SHARED_AUTHORIZED_KEYS_PATH)

        # Try to execute shell command - should be blocked by git-shell
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
                f"{SSH_USER}@{SSH_HOST}",
                "echo 'shell access test'",
            ],
            check=False,
            capture_output=True,
            timeout=10,
            text=True,
        )

        # Should fail with permission denied or unrecognized command (since git-shell blocks non-git commands)
        assert (
            "Permission denied" in result.stderr
            or "not permitted" in result.stderr
            or "unrecognized command" in result.stderr
            or "does not exist" in result.stderr
        )

    finally:
        # Remove the key from shared authorized_keys
        remove_key_from_shared_authorized_keys("shell-test")

        if authorized_keys.is_symlink():
            authorized_keys.unlink()
        if backup_path and backup_path.exists():
            backup_path.rename(authorized_keys)


def test_port_forwarding_blocked(real_git_server, ssh_test_key):
    """Test that port forwarding is blocked via SSH restrictions."""
    # Unpack fixture values
    manager, server_base = real_git_server
    priv_key, pub_key = ssh_test_key

    # Add key to shared authorized_keys with restrictions
    add_key_to_shared_authorized_keys(pub_key, "port-test")

    # Setup authorized_keys
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    authorized_keys = ssh_dir / "authorized_keys"
    backup_path = None
    if authorized_keys.exists():
        backup_path = authorized_keys.with_suffix(".backup.port-test")
        authorized_keys.rename(backup_path)

    try:
        authorized_keys.symlink_to(SHARED_AUTHORIZED_KEYS_PATH)

        # Try to use port forwarding - should be blocked by authorized_keys restrictions
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
                "-L",
                "8080:localhost:80",  # Try to forward local port
                f"{SSH_USER}@{SSH_HOST}",
                "help",
            ],
            check=False,
            capture_output=True,
            timeout=10,
            text=True,
        )

        # Port forwarding should be rejected
        assert "Permission denied" in result.stderr or "administratively prohibited" in result.stderr or result.returncode != 0

    finally:
        # Remove the key from shared authorized_keys
        remove_key_from_shared_authorized_keys("port-test")

        if authorized_keys.is_symlink():
            authorized_keys.unlink()
        if backup_path and backup_path.exists():
            backup_path.rename(authorized_keys)


def test_non_git_commands_blocked(real_git_server, ssh_test_key):
    """Test that non-git commands are blocked via git-shell restrictions."""
    # Unpack fixture values
    manager, server_base = real_git_server
    priv_key, pub_key = ssh_test_key

    # Add key to shared authorized_keys with restrictions
    add_key_to_shared_authorized_keys(pub_key, "git-only-test")

    # Setup authorized_keys
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    authorized_keys = ssh_dir / "authorized_keys"
    backup_path = None
    if authorized_keys.exists():
        backup_path = authorized_keys.with_suffix(".backup.git-only-test")
        authorized_keys.rename(backup_path)

    try:
        authorized_keys.symlink_to(SHARED_AUTHORIZED_KEYS_PATH)

        # Try to execute a non-git command
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
                f"{SSH_USER}@{SSH_HOST}",
                "cat /etc/passwd",
            ],
            check=False,
            capture_output=True,
            timeout=10,
            text=True,
        )

        # Should fail with permission denied or similar
        assert "fatal" in result.stderr or "not permitted" in result.stderr or "does not exist" in result.stderr

    finally:
        # Remove the key from shared authorized_keys
        remove_key_from_shared_authorized_keys("git-only-test")

        if authorized_keys.is_symlink():
            authorized_keys.unlink()
        if backup_path and backup_path.exists():
            backup_path.rename(authorized_keys)
