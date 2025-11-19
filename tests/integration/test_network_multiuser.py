"""Network E2E tests for ami-repo CLI tool - Multi-user scenarios.

Tests multi-user SSH access scenarios over localhost.
"""

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
from tests.integration.conftest import SHARED_AUTHORIZED_KEYS_PATH, add_key_to_shared_authorized_keys, remove_key_from_shared_authorized_keys

# Import fixtures from main conftest
pytest_plugins = ("tests.fixtures.ami_repo.conftest",)


class TestMultiUserScenarios:
    """Test multi-user SSH access scenarios."""

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    @pytest.mark.slow
    def test_multiple_keys_different_repos(self, real_git_server, ssh_test_key, tmp_path):
        """Multiple users with different keys can access different repos."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        # Create two repositories
        manager.create_repo("repo-a")
        manager.create_repo("repo-b")

        # Generate a second SSH key for the second user
        key2 = tmp_path / "user2_key"
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(key2), "-N", "", "-C", "user2"], check=True, capture_output=True)
        pub_key2 = key2.with_suffix(".pub")

        # Add both keys to shared authorized_keys
        add_key_to_shared_authorized_keys(pub_key, "user1")
        add_key_to_shared_authorized_keys(pub_key2, "user2")

        # Verify both keys in shared authorized_keys
        content = SHARED_AUTHORIZED_KEYS_PATH.read_text()
        assert "user1" in content
        assert "user2" in content

        # Cleanup
        remove_key_from_shared_authorized_keys("user1")
        remove_key_from_shared_authorized_keys("user2")

    @pytest.mark.network
    @pytest.mark.requires_ssh
    @pytest.mark.integration
    def test_key_rotation(self, real_git_server, ssh_test_key, tmp_path):
        """Key rotation: remove old key, add new key, verify access."""
        manager, server_base = real_git_server
        priv_key, pub_key = ssh_test_key

        # Create repo
        manager.create_repo("test-rotation")

        # Add old key to shared authorized_keys
        add_key_to_shared_authorized_keys(pub_key, "old-key")

        # Verify old key present
        content = SHARED_AUTHORIZED_KEYS_PATH.read_text()
        assert "old-key" in content

        # Remove old key
        remove_key_from_shared_authorized_keys("old-key")

        # Add new key
        new_key = tmp_path / "new_key"
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(new_key), "-N", "", "-C", "new-key"], check=True, capture_output=True)
        new_pub_key = new_key.with_suffix(".pub")
        add_key_to_shared_authorized_keys(new_pub_key, "new-key")

        # Verify rotation
        content = SHARED_AUTHORIZED_KEYS_PATH.read_text()
        assert "old-key" not in content
        assert "new-key" in content

        # Cleanup
        remove_key_from_shared_authorized_keys("new-key")
