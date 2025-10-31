"""Integration E2E tests for ami-repo CLI tool.

Tests real repository operations with actual git commands and file system.
NO TEST DOUBLES - all operations use real subprocess execution.
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

from ami_repo import GitRepoManager

# Import fixtures from conftest
pytest_plugins = ("tests.fixtures.ami_repo.conftest",)


@pytest.fixture(autouse=True)
def disable_file_locking(monkeypatch):
    """Disable file locking for all integration tests."""
    monkeypatch.setenv("AMI_TEST_MODE", "1")


class TestRepositoryManagement:
    """Test repository management operations."""

    @pytest.mark.integration
    def test_init_server_structure(self, tmp_path):
        """init_server creates proper directory structure."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        assert manager.base_path.exists()
        assert manager.repos_path.exists()
        assert (manager.base_path / "README.md").exists()

    @pytest.mark.integration
    def test_create_bare_repository(self, tmp_path):
        """create_repo creates valid bare git repository."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()
        manager.create_repo("test-repo", description="Test repository")

        repo_path = manager.repos_path / "test-repo.git"
        assert repo_path.exists()
        assert (repo_path / "config").exists()
        assert (repo_path / "HEAD").exists()
        assert (repo_path / "description").read_text().strip() == "Test repository"

    @pytest.mark.integration
    def test_create_repository_with_daemon_export(self, tmp_path):
        """create_repo adds git-daemon-export-ok file."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()
        manager.create_repo("test-repo")

        repo_path = manager.repos_path / "test-repo.git"
        assert (repo_path / "git-daemon-export-ok").exists()

    @pytest.mark.integration
    def test_list_repositories_empty(self, tmp_path):
        """list_repos shows no repositories when empty."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.list_repos()

        output = f.getvalue()
        assert "No repositories found" in output

    @pytest.mark.integration
    def test_list_repositories_multiple(self, tmp_path):
        """list_repos displays all repositories."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        manager.create_repo("repo1")
        manager.create_repo("repo2")
        manager.create_repo("repo3")

        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.list_repos()

        output = f.getvalue()
        assert "repo1.git" in output
        assert "repo2.git" in output
        assert "repo3.git" in output

    @pytest.mark.integration
    def test_list_repos_verbose(self, tmp_path):
        """list_repos verbose shows detailed information."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()
        manager.create_repo("test-repo", description="Test description")

        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.list_repos(verbose=True)

        output = f.getvalue()
        assert "test-repo.git" in output
        assert "Test description" in output
        assert "Path:" in output or "URL:" in output

    @pytest.mark.integration
    def test_delete_repository(self, tmp_path):
        """delete_repo removes repository."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()
        manager.create_repo("test-repo")

        repo_path = manager.repos_path / "test-repo.git"
        assert repo_path.exists()

        manager.delete_repo("test-repo", force=True)
        assert not repo_path.exists()

    @pytest.mark.integration
    def test_repo_info_displays_details(self, tmp_path):
        """repo_info shows repository details."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()
        manager.create_repo("test-repo", description="Test repository")

        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.repo_info("test-repo")

        output = f.getvalue()
        assert "test-repo.git" in output
        assert "Test repository" in output
        assert "Path:" in output
        assert "No commits yet" in output


class TestCloneOperations:
    """Test repository cloning operations."""

    @pytest.mark.integration
    def test_clone_empty_repository(self, tmp_path):
        """clone_repo clones empty bare repository."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()
        manager.create_repo("test-repo")

        clone_dest = tmp_path / "cloned-repo"
        manager.clone_repo("test-repo", destination=clone_dest)

        assert clone_dest.exists()
        assert (clone_dest / ".git").exists()

    @pytest.mark.integration
    def test_clone_with_commits(self, tmp_path, test_repo_with_commits):
        """clone_repo clones repository with commits."""
        # First push test repo to bare repository
        manager = GitRepoManager(base_path=tmp_path / "git-server")
        manager.init_server()
        manager.create_repo("test-repo")

        bare_repo = manager.repos_path / "test-repo.git"

        # Push commits to bare repo
        env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
        subprocess.run(["git", "remote", "add", "origin", f"file://{bare_repo}"], cwd=test_repo_with_commits, env=env, check=True)
        subprocess.run(["git", "push", "-u", "origin", "master"], cwd=test_repo_with_commits, env=env, check=True)

        # Clone the repository
        clone_dest = tmp_path / "cloned-repo"
        manager.clone_repo("test-repo", destination=clone_dest)

        assert clone_dest.exists()
        assert (clone_dest / "file0.txt").exists()
        assert (clone_dest / "file1.txt").exists()
        assert (clone_dest / "file2.txt").exists()


class TestSSHKeyManagement:
    """Test SSH key management operations."""

    @pytest.mark.integration
    def test_add_ed25519_key(self, tmp_path, ssh_key_pair):
        """add_ssh_key adds ED25519 key with restrictions."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        _, pub_key = ssh_key_pair
        manager.add_ssh_key(pub_key, "test-developer")

        assert manager.keys_path.exists()
        content = manager.keys_path.read_text()
        assert "# test-developer" in content
        assert "command=" in content
        assert "git-shell" in content
        assert "no-port-forwarding" in content

    @pytest.mark.integration
    def test_add_rsa_key(self, tmp_path, test_keys_dir):
        """add_ssh_key adds RSA key."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        rsa_key = test_keys_dir / "test_rsa.pub"
        manager.add_ssh_key(rsa_key, "test-rsa-key")

        content = manager.keys_path.read_text()
        assert "# test-rsa-key" in content
        assert "ssh-rsa" in content

    @pytest.mark.integration
    def test_list_added_keys(self, tmp_path, ssh_key_pair):
        """list_ssh_keys displays added keys."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        _, pub_key = ssh_key_pair
        manager.add_ssh_key(pub_key, "test-key")

        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.list_ssh_keys()

        output = f.getvalue()
        assert "test-key" in output
        assert "ssh-ed25519" in output

    @pytest.mark.integration
    def test_remove_key(self, tmp_path, ssh_key_pair):
        """remove_ssh_key removes key from authorized_keys."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        _, pub_key = ssh_key_pair
        manager.add_ssh_key(pub_key, "test-key")

        # Verify added
        content_before = manager.keys_path.read_text()
        assert "test-key" in content_before

        # Remove
        manager.remove_ssh_key("test-key")

        # Verify removed
        content_after = manager.keys_path.read_text()
        assert "test-key" not in content_after

    @pytest.mark.integration
    def test_multiple_keys(self, tmp_path, ssh_key_pair, test_keys_dir):
        """Can add and manage multiple SSH keys."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        # Add ED25519 key
        _, ed_pub_key = ssh_key_pair
        manager.add_ssh_key(ed_pub_key, "key1")

        # Add RSA key
        rsa_key = test_keys_dir / "test_rsa.pub"
        manager.add_ssh_key(rsa_key, "key2")

        content = manager.keys_path.read_text()
        assert "# key1" in content
        assert "# key2" in content
        assert "ssh-ed25519" in content
        assert "ssh-rsa" in content


class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_full_repo_lifecycle(self, tmp_path):
        """Complete workflow: init → create → clone → modify → delete."""
        manager = GitRepoManager(base_path=tmp_path / "git-server")

        # Initialize server
        manager.init_server()

        # Create repository
        manager.create_repo("project", description="Test project")

        # Clone repository
        clone_dest = tmp_path / "workspace"
        manager.clone_repo("project", destination=clone_dest)

        # Make changes
        test_file = clone_dest / "README.md"
        test_file.write_text("# Test Project")

        env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=clone_dest, env=env, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=clone_dest, env=env, check=True)
        subprocess.run(["git", "add", "."], cwd=clone_dest, env=env, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=clone_dest, env=env, check=True)
        subprocess.run(["git", "push"], cwd=clone_dest, env=env, check=True)

        # Verify commit in bare repo
        result = subprocess.run(["git", "--git-dir", str(manager.repos_path / "project.git"), "log", "--oneline"], capture_output=True, text=True, check=True)
        assert "Initial commit" in result.stdout

        # Delete repository
        manager.delete_repo("project", force=True)
        assert not (manager.repos_path / "project.git").exists()

    @pytest.mark.integration
    def test_key_management_workflow(self, tmp_path, ssh_key_pair):
        """Complete SSH key workflow: add → list → remove → verify."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        _, pub_key = ssh_key_pair

        # Add key
        manager.add_ssh_key(pub_key, "developer-key")

        # List keys
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.list_ssh_keys()
        assert "developer-key" in f.getvalue()

        # Remove key
        manager.remove_ssh_key("developer-key")

        # Verify removal
        f = io.StringIO()
        with redirect_stdout(f):
            manager.list_ssh_keys()
        assert "developer-key" not in f.getvalue()

    @pytest.mark.integration
    def test_multi_repo_workflow(self, tmp_path):
        """Manage multiple repositories simultaneously."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        # Create multiple repos
        repos = ["backend", "frontend", "docs"]
        for repo in repos:
            manager.create_repo(repo, description=f"{repo} repository")

        # Verify all exist
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            manager.list_repos()

        output = f.getvalue()
        for repo in repos:
            assert f"{repo}.git" in output


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.integration
    def test_operations_before_init(self, tmp_path):
        """Operations fail gracefully before init."""
        manager = GitRepoManager(base_path=tmp_path)

        with pytest.raises(SystemExit):
            manager.create_repo("test")

    @pytest.mark.integration
    def test_duplicate_repository(self, tmp_path):
        """Cannot create duplicate repository."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()
        manager.create_repo("test")

        with pytest.raises(SystemExit):
            manager.create_repo("test")

    @pytest.mark.integration
    def test_delete_nonexistent(self, tmp_path):
        """Delete nonexistent repository fails."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        with pytest.raises(SystemExit):
            manager.delete_repo("nonexistent", force=True)

    @pytest.mark.integration
    def test_clone_nonexistent(self, tmp_path):
        """Clone nonexistent repository fails."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        with pytest.raises(SystemExit):
            manager.clone_repo("nonexistent", destination=tmp_path / "clone")

    @pytest.mark.integration
    def test_invalid_key_file(self, tmp_path):
        """Add invalid key file fails."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        invalid_key = tmp_path / "invalid.pub"
        invalid_key.write_text("not a valid ssh key")

        with pytest.raises(SystemExit):
            manager.add_ssh_key(invalid_key, "invalid")

    @pytest.mark.integration
    def test_duplicate_key_rejected(self, tmp_path, ssh_key_pair):
        """Adding duplicate key is rejected."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        _, pub_key = ssh_key_pair
        manager.add_ssh_key(pub_key, "key1")

        with pytest.raises(SystemExit):
            manager.add_ssh_key(pub_key, "key2")


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    @pytest.mark.integration
    def test_repository_with_special_characters(self, tmp_path):
        """Repository names with hyphens and underscores."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()

        manager.create_repo("my-project_v2")
        assert (manager.repos_path / "my-project_v2.git").exists()

    @pytest.mark.integration
    def test_empty_description(self, tmp_path):
        """Repository with no description."""
        manager = GitRepoManager(base_path=tmp_path)
        manager.init_server()
        manager.create_repo("test")

        repo_path = manager.repos_path / "test.git"
        desc_file = repo_path / "description"

        # Default git description
        desc_content = desc_file.read_text().strip()
        assert "Unnamed repository" in desc_content or desc_content == ""

    @pytest.mark.integration
    def test_clone_to_existing_directory_fails(self, tmp_path):
        """Clone to existing directory fails."""
        manager = GitRepoManager(base_path=tmp_path / "server")
        manager.init_server()
        manager.create_repo("test")

        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        with pytest.raises(SystemExit):
            manager.clone_repo("test", destination=existing_dir)
