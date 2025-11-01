"""Unit tests for ami-repo CLI tool.

Tests GitRepoManager class methods in isolation with mocking.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
root_dir = Path(__file__).resolve().parents[2]
scripts_dir = root_dir / "scripts"
sys.path.insert(0, str(scripts_dir))

from ami_repo import GitRepoManager

from backend.git_server.results import RepositoryError, SSHKeyError


class TestGitRepoManagerInit:
    """Test GitRepoManager initialization."""

    def test_default_base_path(self):
        """Manager uses ~/git-repos by default."""
        manager = GitRepoManager()
        expected = Path.home() / "git-repos"
        assert manager.base_path == expected
        assert manager.repos_path == expected / "repos"

    def test_custom_base_path(self, tmp_path):
        """Manager accepts custom base path."""
        custom_path = tmp_path / "custom-git"
        manager = GitRepoManager(base_path=custom_path)
        assert manager.base_path == custom_path
        assert manager.repos_path == custom_path / "repos"

    def test_initializes_paths(self, tmp_path):
        """Manager initializes all path attributes."""
        manager = GitRepoManager(base_path=tmp_path)
        assert hasattr(manager, "base_path")
        assert hasattr(manager, "repos_path")
        assert hasattr(manager, "keys_path")
        assert hasattr(manager, "ssh_dir")


class TestURLGeneration:
    """Test repository URL generation."""

    def test_file_url_format(self, tmp_path):
        """get_repo_url generates correct file:// URL."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.repos_path.mkdir(parents=True)
        repo_path = manager.repos_path / "test.git"
        repo_path.mkdir()

        # Capture stdout
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.get_repo_url("test", protocol="file")

        output = f.getvalue().strip()
        assert output.startswith("file://")
        assert output.endswith("test.git")

    def test_ssh_url_format(self, tmp_path, monkeypatch):
        """get_repo_url generates correct ssh:// URL."""
        monkeypatch.setenv("USER", "testuser")
        monkeypatch.setenv("HOSTNAME", "testhost")

        manager = GitRepoManager(base_path=tmp_path)
        manager.repos_path.mkdir(parents=True)
        repo_path = manager.repos_path / "test.git"
        repo_path.mkdir()

        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.get_repo_url("test", protocol="ssh")

        output = f.getvalue().strip()
        assert output.startswith("ssh://testuser@testhost")
        assert "test.git" in output


class TestKeyValidation:
    """Test SSH key validation logic."""

    def test_validates_ed25519_key(self, tmp_path):
        """add_ssh_key accepts valid ED25519 key."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.base_path.mkdir(exist_ok=True)

        key_file = tmp_path / "test_key.pub"
        key_file.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... test@example.com")

        # Should not raise
        manager.add_ssh_key(key_file, "test-key")

    def test_validates_rsa_key(self, tmp_path):
        """add_ssh_key accepts valid RSA key."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.base_path.mkdir(exist_ok=True)

        key_file = tmp_path / "test_key.pub"
        key_file.write_text("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABA... test@example.com")

        # Should not raise
        manager.add_ssh_key(key_file, "test-key")

    def test_rejects_invalid_key_format(self, tmp_path):
        """add_ssh_key rejects invalid key format."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.base_path.mkdir(exist_ok=True)

        key_file = tmp_path / "invalid_key.pub"
        key_file.write_text("not-a-valid-ssh-key")

        with pytest.raises(SSHKeyError):
            manager.add_ssh_key(key_file, "invalid-key")

    def test_rejects_missing_key_file(self, tmp_path):
        """add_ssh_key fails on missing key file."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.base_path.mkdir(exist_ok=True)

        missing_key = tmp_path / "nonexistent.pub"

        with pytest.raises(SSHKeyError):
            manager.add_ssh_key(missing_key, "missing-key")


class TestRepositoryNameHandling:
    """Test repository name normalization."""

    @patch("subprocess.run")
    def test_adds_git_extension(self, mock_run, tmp_path):
        """create_repo adds .git extension if missing."""

        def mock_init(*args, **kwargs):
            # Simulate git init --bare by creating the directory
            cmd_args = args[0] if args else kwargs.get("args", [])
            if "git" in cmd_args and "init" in cmd_args:
                # Find the path argument
                for arg in cmd_args:
                    if str(tmp_path) in str(arg):
                        Path(arg).mkdir(parents=True, exist_ok=True)
            return MagicMock(returncode=0)

        mock_run.side_effect = mock_init

        manager = GitRepoManager(base_path=tmp_path)
        manager.repos_path.mkdir(parents=True)

        manager.create_repo("my-project")

        # Check that .git extension was added
        expected_path = manager.repos_path / "my-project.git"
        assert expected_path.exists()

    @patch("subprocess.run")
    def test_preserves_git_extension(self, mock_run, tmp_path):
        """create_repo preserves existing .git extension."""

        def mock_init(*args, **kwargs):
            # Simulate git init --bare by creating the directory
            cmd_args = args[0] if args else kwargs.get("args", [])
            if "git" in cmd_args and "init" in cmd_args:
                # Find the path argument
                for arg in cmd_args:
                    if str(tmp_path) in str(arg):
                        Path(arg).mkdir(parents=True, exist_ok=True)
            return MagicMock(returncode=0)

        mock_run.side_effect = mock_init

        manager = GitRepoManager(base_path=tmp_path)
        manager.repos_path.mkdir(parents=True)

        manager.create_repo("my-project.git")

        expected_path = manager.repos_path / "my-project.git"
        assert expected_path.exists()


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_init_server_before_operations(self, tmp_path):
        """Operations fail gracefully when server not initialized."""
        manager = GitRepoManager(base_path=tmp_path)

        with pytest.raises(RepositoryError):
            manager.create_repo("test")

    def test_duplicate_repository_creation(self, tmp_path):
        """create_repo fails on duplicate repository name."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.repos_path.mkdir(parents=True)

        # Create first repo
        repo_path = manager.repos_path / "test.git"
        repo_path.mkdir()

        # Try to create duplicate
        with pytest.raises(RepositoryError):
            manager.create_repo("test")

    def test_list_repos_empty_server(self, tmp_path):
        """list_repos handles empty server gracefully."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.repos_path.mkdir(parents=True)

        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.list_repos()

        output = f.getvalue()
        assert "No repositories found" in output

    def test_delete_nonexistent_repo(self, tmp_path):
        """delete_repo fails on nonexistent repository."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.repos_path.mkdir(parents=True)

        with pytest.raises(RepositoryError):
            manager.delete_repo("nonexistent", force=True)

    def test_repo_info_nonexistent_repo(self, tmp_path):
        """repo_info fails on nonexistent repository."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.repos_path.mkdir(parents=True)

        with pytest.raises(RepositoryError):
            manager.repo_info("nonexistent")


class TestSSHKeyManagement:
    """Test SSH key management functionality."""

    def test_add_key_creates_authorized_keys_file(self, tmp_path):
        """add_ssh_key creates authorized_keys file if missing."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.base_path.mkdir(exist_ok=True)

        key_file = tmp_path / "test_key.pub"
        key_file.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... test@example.com")

        manager.add_ssh_key(key_file, "test-key")

        assert manager.keys_path.exists()
        assert manager.keys_path.stat().st_mode & 0o777 == 0o600

    def test_add_key_with_restrictions(self, tmp_path):
        """add_ssh_key adds proper SSH restrictions."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.base_path.mkdir(exist_ok=True)

        key_file = tmp_path / "test_key.pub"
        key_file.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... test@example.com")

        manager.add_ssh_key(key_file, "test-key")

        content = manager.keys_path.read_text()
        assert "no-port-forwarding" in content
        assert "no-X11-forwarding" in content
        assert "no-agent-forwarding" in content
        assert "no-pty" in content
        assert "git-shell" in content

    def test_prevents_duplicate_keys(self, tmp_path):
        """add_ssh_key rejects duplicate keys."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.base_path.mkdir(exist_ok=True)

        key_file = tmp_path / "test_key.pub"
        key_content = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... test@example.com"
        key_file.write_text(key_content)

        # Add key first time
        manager.add_ssh_key(key_file, "test-key")

        # Try to add same key again
        with pytest.raises(SSHKeyError):
            manager.add_ssh_key(key_file, "duplicate-key")

    def test_list_keys_empty(self, tmp_path):
        """list_ssh_keys handles no keys gracefully."""
        manager = GitRepoManager(base_path=tmp_path)

        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.list_ssh_keys()

        output = f.getvalue()
        assert "No SSH keys configured" in output

    def test_remove_key_success(self, tmp_path):
        """remove_ssh_key removes key successfully."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.base_path.mkdir(exist_ok=True)

        # Add key
        key_file = tmp_path / "test_key.pub"
        key_file.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... test@example.com")
        manager.add_ssh_key(key_file, "test-key")

        # Remove key
        manager.remove_ssh_key("test-key")

        # Verify removed
        content = manager.keys_path.read_text()
        assert "test-key" not in content

    def test_remove_nonexistent_key(self, tmp_path):
        """remove_ssh_key fails on nonexistent key."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.base_path.mkdir(exist_ok=True)
        manager.keys_path.touch()

        with pytest.raises(SSHKeyError):
            manager.remove_ssh_key("nonexistent-key")


class TestPathSafety:
    """Test path safety and validation."""

    def test_repos_path_is_subdirectory(self, tmp_path):
        """repos_path is always subdirectory of base_path."""
        manager = GitRepoManager(base_path=tmp_path)
        assert manager.repos_path.parent == manager.base_path

    def test_keys_path_is_in_base(self, tmp_path):
        """keys_path is inside base_path."""
        manager = GitRepoManager(base_path=tmp_path)
        assert manager.base_path in manager.keys_path.parents

    def test_base_path_absolute(self):
        """base_path is always absolute."""
        manager = GitRepoManager()
        assert manager.base_path.is_absolute()
