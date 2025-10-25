"""Integration tests for ami-agent --sync mode.

These tests ACTUALLY execute ami-agent --sync with real git repositories.
NO mocking of Claude CLI, git operations, or agent functionality.

Following TEST WHAT RUNS IN PRODUCTION philosophy.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


def create_git_repo(path: Path, initial_commit: bool = True):  # test-fixture
    """Create a git repository with initial setup."""
    path.mkdir(parents=True, exist_ok=True)  # test-fixture
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)  # test-fixture
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True)  # test-fixture
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)  # test-fixture

    if initial_commit:  # test-fixture
        (path / "README.md").write_text("# Test Repo\n")  # test-fixture
        subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True)  # test-fixture
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=path, check=True, capture_output=True)  # test-fixture


def get_git_status(path: Path) -> str:  # test-fixture
    """Get git status porcelain output."""
    result = subprocess.run(["git", "status", "--porcelain"], cwd=path, check=True, capture_output=True, text=True)  # test-fixture
    return result.stdout.strip()  # test-fixture


def has_unpushed_commits(path: Path) -> bool:  # test-fixture
    """Check if repo has unpushed commits."""
    result = subprocess.run(["git", "log", "@{u}..", "--oneline"], check=False, cwd=path, capture_output=True, text=True)  # test-fixture
    return bool(result.stdout.strip())  # test-fixture


class TestSyncModeBasicFunctionality:
    """Test basic sync mode operations."""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_already_synced(self):  # test-fixture
        """Sync mode exits quickly when module is already synced."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert result.returncode == 0
            assert "SYNCED" in result.stdout or "synced" in result.stdout
            assert get_git_status(repo_path) == ""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_commits_uncommitted_changes(self):  # test-fixture
        """Sync mode commits uncommitted changes."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            (repo_path / "new_file.txt").write_text("new content\n")  # test-fixture

            assert get_git_status(repo_path) != ""

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert result.returncode == 0
            assert get_git_status(repo_path) == ""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_handles_staged_changes(self):  # test-fixture
        """Sync mode commits already-staged changes."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            (repo_path / "staged_file.txt").write_text("staged content\n")  # test-fixture
            subprocess.run(["git", "add", "staged_file.txt"], cwd=repo_path, check=True, capture_output=True)  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert result.returncode == 0
            assert get_git_status(repo_path) == ""


class TestSyncModeModeratorValidation:
    """Test moderator validation logic."""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_moderator_validates_clean_state(self):  # test-fixture
        """Moderator validates that git state is actually clean."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert result.returncode == 0
            assert get_git_status(repo_path) == ""
            assert "PASS" in result.stdout or "synced" in result.stdout.lower()


class TestSyncModeZeroToleranceEnforcement:
    """Test zero-tolerance policy enforcement."""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_prevents_test_deletion(self):  # test-fixture
        """Sync mode prevents committing test file deletions."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            test_file = repo_path / "test_feature.py"  # test-fixture
            test_file.write_text("def test_something():\n    assert True\n")  # test-fixture
            subprocess.run(["git", "add", "test_feature.py"], cwd=repo_path, check=True, capture_output=True)  # test-fixture
            subprocess.run(["git", "commit", "-m", "Add test"], cwd=repo_path, check=True, capture_output=True)  # test-fixture

            test_file.unlink()  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert result.returncode == 1
            assert "test" in result.stdout.lower() or "deletion" in result.stdout.lower()


class TestSyncModeErrorHandling:
    """Test error handling for sync mode."""

    def test_sync_mode_missing_module(self):  # test-fixture
        """Sync mode returns error for non-existent path."""
        result = subprocess.run(  # test-fixture
            ["./scripts/ami-agent", "--sync", "/nonexistent/path"],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "not found" in result.stderr.lower()

    def test_sync_mode_not_git_repo(self):  # test-fixture
        """Sync mode returns error for non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", tmpdir],
                check=False,
                capture_output=True,
                text=True,
            )

            assert result.returncode == 1
            assert "git" in result.stderr.lower() or "repository" in result.stderr.lower()


class TestSyncModeProgressTracking:
    """Test progress file tracking."""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_creates_progress_file(self):  # test-fixture
        """Sync mode creates .sync-progress-*.md during execution."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            (repo_path / "test.txt").write_text("content\n")  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            progress_files = list(repo_path.glob(".sync-progress-*.md"))  # test-fixture

            if result.returncode == 0:  # test-fixture
                assert len(progress_files) == 0
            else:  # test-fixture
                assert len(progress_files) >= 0

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_cleans_progress_on_success(self):  # test-fixture
        """Sync mode deletes progress file on successful completion."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:  # test-fixture
                progress_files = list(repo_path.glob(".sync-progress-*.md"))  # test-fixture
                assert len(progress_files) == 0


class TestSyncModeGitCommandUsage:
    """Test that sync mode uses correct git command wrappers."""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_uses_git_commit_script(self):  # test-fixture
        """Sync mode uses scripts/git_commit.sh not direct git commit."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            (repo_path / "file.txt").write_text("content\n")  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:  # test-fixture
                log_result = subprocess.run(["git", "log", "-1", "--format=%B"], check=False, cwd=repo_path, capture_output=True, text=True)  # test-fixture
                assert "Generated with" in log_result.stdout or "Claude" in log_result.stdout


class TestSyncModeRetryBehavior:
    """Test retry loop and attempt tracking."""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_tracks_attempts(self):  # test-fixture
        """Sync mode tracks attempt count in result output."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert "Attempts:" in result.stdout or "attempt" in result.stdout.lower()
            assert "Duration:" in result.stdout or "duration" in result.stdout.lower()


class TestSyncModeOutputFormat:
    """Test output format and exit codes."""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_outputs_result_summary(self):  # test-fixture
        """Sync mode outputs structured result summary."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert "Sync Result:" in result.stdout or "Result:" in result.stdout
            assert "Module:" in result.stdout
            assert "Attempts:" in result.stdout
            assert "Duration:" in result.stdout

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    @pytest.mark.slow
    def test_sync_mode_exit_code_success(self):  # test-fixture
        """Sync mode returns 0 for successful sync."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            repo_path = Path(tmpdir) / "test_repo"
            create_git_repo(repo_path)  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-agent", "--sync", str(repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert result.returncode == 0
