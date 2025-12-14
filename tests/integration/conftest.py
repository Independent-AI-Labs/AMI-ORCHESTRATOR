"""Shared fixtures and utilities for network tests."""

import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Add scripts and fixtures to path
root_dir = Path(__file__).resolve().parents[2]
scripts_dir = root_dir / "scripts"
sys.path.insert(0, str(scripts_dir))

import contextlib

from ami_repo import GitRepoManager

# Use localhost as SSH host for all network tests
SSH_HOST = "127.0.0.1"
SSH_USER = "ami"
SSH_PORT = 2222  # Git SSH server runs on port 2222, not system SSH port


# Global shared authorized_keys file for all tests
SHARED_AUTHORIZED_KEYS_PATH = Path.home() / ".ami-repo-shared-authorized-keys"


@pytest.fixture(scope="session", autouse=True)
def setup_git_ssh_server():
    """Setup and teardown git SSH server for all network tests in the session."""
    # Create a GitRepoManager instance to access service operations
    # Use a temporary base path for the service operations context
    temp_base_path = Path.home() / ".ami-repo-network-test-tmp"
    temp_base_path.mkdir(exist_ok=True)

    # Initialize the shared authorized_keys file from the beginning
    if SHARED_AUTHORIZED_KEYS_PATH.exists():
        SHARED_AUTHORIZED_KEYS_PATH.unlink()
    SHARED_AUTHORIZED_KEYS_PATH.touch(mode=0o600)

    try:
        # Create GitRepoManager to access service operations
        manager = GitRepoManager(base_path=temp_base_path)

        # Initialize the server to create the base structure
        manager.init_server()

        # Bootstrap SSH server if needed (to ensure it's properly installed/configured)
        with contextlib.suppress(Exception):
            manager.bootstrap_ssh_server(install_type="venv")

        # Configure the git SSH server to use the shared authorized_keys file FIRST
        # This ensures the SSH server knows where to find authorized keys
        _setup_git_ssh_server_config(SHARED_AUTHORIZED_KEYS_PATH)

        # Start the git server services using the service operations
        # This ensures both git-sshd and git-daemon are running
        manager.service_ops.service_start(mode="dev")

        # Wait a moment for the server to initialize
        time.sleep(5)  # Increase the wait time to ensure service is fully operational

        yield  # Run all tests

    finally:
        # Stop git server services after all tests complete
        try:
            temp_manager = GitRepoManager(base_path=temp_base_path)
            temp_manager.service_ops.service_stop(mode="dev")
        except Exception as e:
            logging.warning(f"Error stopping services during cleanup: {e}")
        finally:
            # Remove shared authorized keys file
            if SHARED_AUTHORIZED_KEYS_PATH.exists():
                SHARED_AUTHORIZED_KEYS_PATH.unlink()
            # Cleanup temporary directory
            if temp_base_path.exists():
                shutil.rmtree(temp_base_path, ignore_errors=True)


@pytest.fixture(autouse=True)
def disable_file_locking(monkeypatch):
    """Disable file locking for all network tests."""
    monkeypatch.setenv("AMI_TEST_MODE", "1")


@pytest.fixture
def real_git_server():
    """Use a per-test GitRepoManager while using the session-level SSH configuration.

    Returns:
        tuple: (GitRepoManager, base_path)
    """
    # Use real home directory subdirectory for SSH access
    real_home = Path.home()
    server_base = real_home / f".ami-repo-test-{os.getpid()}"

    try:
        manager = GitRepoManager(base_path=server_base)
        manager.init_server()

        # Ensure the authorized_keys file exists
        if not manager.keys_path.exists():
            manager.keys_path.touch(mode=0o600)
        else:
            # If exists, ensure proper permissions
            manager.keys_path.chmod(0o600)

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


def _restart_git_ssh_server():
    """Restart the git SSH server to pick up updated authorized_keys."""
    try:
        # Use GitRepoManager's service operations instead of direct subprocess calls
        temp_base_path = Path.home() / ".ami-repo-network-test-tmp"
        manager = GitRepoManager(base_path=temp_base_path)

        # Stop the git server services first
        manager.service_ops.service_stop(mode="dev")
        time.sleep(2)  # Allow time for server to stop completely

        # Start the git server services
        manager.service_ops.service_start(mode="dev")
        time.sleep(5)  # Allow more time for server to start completely

        # Verify that the service is actually running and responsive
        if not _verify_git_server_running():
            # Try to restart once more if verification fails
            manager.service_ops.service_stop(mode="dev")
            time.sleep(2)
            manager.service_ops.service_start(mode="dev")
            time.sleep(5)

            if not _verify_git_server_running():
                raise RuntimeError("Git server is not responding after restart attempts")

    except Exception:
        # Try the subprocess method as a fallback
        try:
            subprocess.run(["scripts/ami-run", "launcher/scripts/setup_service.py", "profile", "stop", "git-server"], check=True, capture_output=True, timeout=30)
            time.sleep(2)  # Allow time for server to stop completely
            subprocess.run(["scripts/ami-run", "launcher/scripts/setup_service.py", "profile", "start", "git-server"], check=True, capture_output=True, timeout=30)
            time.sleep(5)  # Allow time for server to start completely

            # Verify that the service is actually running and responsive
            if not _verify_git_server_running():
                pass

        except Exception:
            raise


def _verify_git_server_running():
    """Check if the git server is actually running and responsive."""
    try:
        # Try to connect to the SSH server on port 2222 to verify it's running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        result = sock.connect_ex(("127.0.0.1", SSH_PORT))
        sock.close()

        # Port is open if connect_ex returns 0
        return result == 0
    except Exception:
        # If there's an error checking the port, assume server is not running
        return False


def add_key_to_shared_authorized_keys(public_key_path: Path, name: str):
    """Add an SSH key to the shared authorized_keys file with git restrictions."""
    if not public_key_path.exists():
        raise Exception(f"Key file not found: {public_key_path}")

    key_content = public_key_path.read_text().strip()

    # Properly formatted restriction that allows git operations
    # Following the pattern from SSH authorized_keys format
    restrictions = 'no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty,command="git-shell -c \\"$SSH_ORIGINAL_COMMAND\\"" '

    key_entry = f"# {name}\n{restrictions}{key_content}\n"

    # Append the key to the shared authorized_keys file
    with SHARED_AUTHORIZED_KEYS_PATH.open("a") as f:
        f.write(key_entry)


def remove_key_from_shared_authorized_keys(name: str):
    """Remove an SSH key from the shared authorized_keys file by name."""
    if not SHARED_AUTHORIZED_KEYS_PATH.exists():
        return

    content = SHARED_AUTHORIZED_KEYS_PATH.read_text()
    lines = content.split("\n")

    new_lines = []
    skip_next = False

    for line in lines:
        if skip_next:
            skip_next = False
            continue

        if line.strip() == f"# {name}":
            skip_next = True  # Skip this line and the next (the key itself)
            continue

        new_lines.append(line)

    SHARED_AUTHORIZED_KEYS_PATH.write_text("\n".join(new_lines))


# Function to properly configure SSH server to use our git manager's authorized_keys file
def _setup_git_ssh_server_config(git_manager_keys_path: Path):
    """Setup git SSH server to use the git manager's authorized_keys file."""
    # The git ssh server is configured to use .venv/openssh/etc/authorized_keys
    # per the bootstrap script configuration
    venv_path = Path.cwd() / ".venv"
    openssh_path = venv_path / "openssh"
    sshd_etc_path = openssh_path / "etc"
    sshd_authorized_keys = sshd_etc_path / "authorized_keys"

    # Create the directory if it doesn't exist
    sshd_etc_path.mkdir(parents=True, exist_ok=True)

    # Check if there's already a symlink at the destination and remove it
    if sshd_authorized_keys.is_symlink() or sshd_authorized_keys.exists():
        sshd_authorized_keys.unlink()

    # Ensure the git manager's keys file exists and has correct permissions
    git_manager_keys_path.touch(mode=0o600, exist_ok=True)

    # Create a symlink from the SSH server's expected location to the git manager's keys
    # This ensures the SSH server always reads from the current test's keys file
    sshd_authorized_keys.symlink_to(git_manager_keys_path)
    # Restart the SSH server to pick up the new authorized_keys file
    _restart_git_ssh_server()
