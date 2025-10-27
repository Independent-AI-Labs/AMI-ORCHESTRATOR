"""Unit tests for TaskExecutor."""

import tempfile
from pathlib import Path

import pytest

from scripts.automation.tasks import TaskExecutor


@pytest.fixture(autouse=True)
def mock_sudo_password(monkeypatch):
    """Mock AMI_SUDO_PASSWORD environment variable for all tests."""
    monkeypatch.setenv("AMI_SUDO_PASSWORD", "test_password")


class TestTaskExecutorFindTaskFiles:
    """Tests for _find_task_files method."""

    def test_find_all_md_files(self):
        """Find all .md files in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            (tmpdir_path / "task1.md").write_text("task 1")
            (tmpdir_path / "task2.md").write_text("task 2")
            (tmpdir_path / "README.md").write_text("readme")

            executor = TaskExecutor()
            task_files = executor._find_task_files(tmpdir_path)

            # Should find task1.md and task2.md (README.md excluded by default)
            assert len(task_files) == 2
            assert task_files[0].name == "task1.md"
            assert task_files[1].name == "task2.md"

    def test_exclude_feedback_files(self):
        """Exclude feedback-*.md files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            (tmpdir_path / "task1.md").write_text("task 1")
            (tmpdir_path / "feedback-20250119-task1.md").write_text("feedback")

            executor = TaskExecutor()
            task_files = executor._find_task_files(tmpdir_path)

            # Should only find task1.md
            assert len(task_files) == 1
            assert task_files[0].name == "task1.md"

    def test_exclude_progress_files(self):
        """Exclude progress-*.md files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            (tmpdir_path / "task1.md").write_text("task 1")
            (tmpdir_path / "progress-20250119-task1.md").write_text("progress")

            executor = TaskExecutor()
            task_files = executor._find_task_files(tmpdir_path)

            # Should only find task1.md
            assert len(task_files) == 1
            assert task_files[0].name == "task1.md"

    def test_exclude_standard_files(self):
        """Exclude README.md, CLAUDE.md, AGENTS.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            (tmpdir_path / "task1.md").write_text("task 1")
            (tmpdir_path / "README.md").write_text("readme")
            (tmpdir_path / "CLAUDE.md").write_text("claude")
            (tmpdir_path / "AGENTS.md").write_text("agents")

            executor = TaskExecutor()
            task_files = executor._find_task_files(tmpdir_path)

            # Should only find task1.md
            assert len(task_files) == 1
            assert task_files[0].name == "task1.md"

    def test_sorted_by_name(self):
        """Return files sorted by name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files in reverse order
            (tmpdir_path / "task3.md").write_text("task 3")
            (tmpdir_path / "task1.md").write_text("task 1")
            (tmpdir_path / "task2.md").write_text("task 2")

            executor = TaskExecutor()
            task_files = executor._find_task_files(tmpdir_path)

            # Should be sorted
            assert len(task_files) == 3
            assert task_files[0].name == "task1.md"
            assert task_files[1].name == "task2.md"
            assert task_files[2].name == "task3.md"

    def test_nested_directories(self):
        """Find files in nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create nested structure
            (tmpdir_path / "task1.md").write_text("task 1")
            (tmpdir_path / "subdir").mkdir()
            (tmpdir_path / "subdir" / "task2.md").write_text("task 2")

            executor = TaskExecutor()
            task_files = executor._find_task_files(tmpdir_path)

            # Should find both files
            assert len(task_files) == 2
            assert any(f.name == "task1.md" for f in task_files)
            assert any(f.name == "task2.md" for f in task_files)


class TestTaskExecutorParseCompletionMarker:
    """Tests for _parse_completion_marker method."""

    def test_work_done_marker(self):
        """Detect 'WORK DONE' marker."""
        executor = TaskExecutor()

        output = "Some output\n\nWORK DONE"
        result = executor._parse_completion_marker(output)

        assert result["type"] == "work_done"
        assert result["content"] is None

    def test_feedback_marker(self):
        """Detect 'FEEDBACK:' marker."""
        executor = TaskExecutor()

        output = "Some output\n\nFEEDBACK: Need help with X and Y"
        result = executor._parse_completion_marker(output)

        assert result["type"] == "feedback"
        assert result["content"] == "Need help with X and Y"

    def test_feedback_multiline(self):
        """Extract multiline feedback content."""
        executor = TaskExecutor()

        output = """Some output

FEEDBACK: Need help with:
- Question 1
- Question 2
"""
        result = executor._parse_completion_marker(output)

        assert result["type"] == "feedback"
        assert "Question 1" in result["content"]
        assert "Question 2" in result["content"]

    def test_no_marker(self):
        """Return 'none' when no marker found."""
        executor = TaskExecutor()

        output = "Some output without any marker"
        result = executor._parse_completion_marker(output)

        assert result["type"] == "none"
        assert result["content"] is None

    def test_work_done_case_sensitive(self):
        """WORK DONE is case sensitive."""
        executor = TaskExecutor()

        # Uppercase should work
        result1 = executor._parse_completion_marker("WORK DONE")
        assert result1["type"] == "work_done"

        # Lowercase should not work
        result2 = executor._parse_completion_marker("work done")
        assert result2["type"] == "none"


class TestTaskExecutorParseModeratorResult:
    """Tests for _parse_moderator_result method."""

    def test_pass_verdict(self):
        """Detect 'PASS' verdict."""
        executor = TaskExecutor()

        output = "Validation result:\n\nPASS"
        result = executor._parse_moderator_result(output)

        assert result["status"] == "pass"
        assert result["reason"] is None

    def test_fail_verdict(self):
        """Detect 'FAIL:' verdict."""
        executor = TaskExecutor()

        output = "Validation result:\n\nFAIL: Missing tests"
        result = executor._parse_moderator_result(output)

        assert result["status"] == "fail"
        assert result["reason"] == "Missing tests"

    def test_fail_multiline_reason(self):
        """Extract multiline failure reason."""
        executor = TaskExecutor()

        output = """Validation result:

FAIL: Multiple issues:
- Missing tests
- No documentation
"""
        result = executor._parse_moderator_result(output)

        assert result["status"] == "fail"
        assert "Missing tests" in result["reason"]
        assert "No documentation" in result["reason"]

    def test_unclear_output_defaults_to_fail(self):
        """Default to fail if output unclear."""
        executor = TaskExecutor()

        output = "Some unclear output"
        result = executor._parse_moderator_result(output)

        assert result["status"] == "fail"
        assert result["reason"] == "Moderator validation unclear - no explicit PASS or FAIL in output"

    def test_pass_case_sensitive(self):
        """PASS is case sensitive."""
        executor = TaskExecutor()

        # Uppercase should work
        result1 = executor._parse_moderator_result("PASS")
        assert result1["status"] == "pass"

        # Lowercase should not work
        result2 = executor._parse_moderator_result("pass")
        assert result2["status"] == "fail"


class TestTaskExecutorFileLocking:
    """Tests for _lock_file and _unlock_file methods."""

    def test_lock_unlock_success_with_mocked_subprocess(self, monkeypatch):
        """Lock and unlock succeed when chattr returns exit code 0."""
        import unittest.mock

        # Set AMI_SUDO_PASSWORD for initialization
        monkeypatch.setenv("AMI_SUDO_PASSWORD", "test-password")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test.md"
            test_file.write_text("test content")

            # Mock subprocess.Popen to simulate successful chattr calls
            with unittest.mock.patch("subprocess.Popen") as mock_popen:
                mock_process = unittest.mock.Mock()
                mock_process.communicate.return_value = ("", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                executor = TaskExecutor()

                # Lock and unlock should not raise exceptions when returncode is 0
                executor._lock_file(test_file)
                executor._unlock_file(test_file)

                # Verify subprocess was called with correct commands
                assert mock_popen.call_count == 2
                calls = mock_popen.call_args_list
                assert calls[0][0][0] == ["sudo", "-S", "chattr", "+i", str(test_file)]
                assert calls[1][0][0] == ["sudo", "-S", "chattr", "-i", str(test_file)]

    def test_lock_file_failure_raises_error(self, monkeypatch):
        """Lock file raises CalledProcessError when chattr fails."""
        import subprocess
        import unittest.mock

        # Set AMI_SUDO_PASSWORD for initialization
        monkeypatch.setenv("AMI_SUDO_PASSWORD", "test-password")

        test_file = Path("/tmp/test-lock-file.md")

        # Mock subprocess to simulate chattr failure
        with unittest.mock.patch("subprocess.Popen") as mock_popen:
            mock_process = unittest.mock.Mock()
            mock_process.communicate.return_value = ("", "chattr: Operation not permitted")
            mock_process.returncode = 1
            mock_popen.return_value = mock_process

            executor = TaskExecutor()

            # Should raise CalledProcessError with correct returncode
            with pytest.raises(subprocess.CalledProcessError) as exc_info:
                executor._lock_file(test_file)

            assert exc_info.value.returncode == 1
            assert exc_info.value.cmd == ["sudo", "-S", "chattr", "+i", str(test_file)]

    def test_unlock_file_failure_raises_error(self, monkeypatch):
        """Unlock file raises CalledProcessError when chattr fails."""
        import subprocess
        import unittest.mock

        # Set AMI_SUDO_PASSWORD for initialization
        monkeypatch.setenv("AMI_SUDO_PASSWORD", "test-password")

        test_file = Path("/tmp/test-unlock-file.md")

        # Mock subprocess to simulate chattr failure
        with unittest.mock.patch("subprocess.Popen") as mock_popen:
            mock_process = unittest.mock.Mock()
            mock_process.communicate.return_value = ("", "chattr: No such file or directory")
            mock_process.returncode = 1
            mock_popen.return_value = mock_process

            executor = TaskExecutor()

            # Should raise CalledProcessError with correct returncode
            with pytest.raises(subprocess.CalledProcessError) as exc_info:
                executor._unlock_file(test_file)

            assert exc_info.value.returncode == 1
            assert exc_info.value.cmd == ["sudo", "-S", "chattr", "-i", str(test_file)]
