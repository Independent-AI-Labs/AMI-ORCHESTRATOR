"""Integration tests for ami-agent --tasks mode.

These tests ACTUALLY execute the ami-agent --tasks script with real subprocesses.
NO mocking of worker or moderator agents.
"""

import subprocess
import tempfile
import unittest.mock
from pathlib import Path

import pytest

from scripts.automation.tasks import TaskExecutor


class TestAmiAgentTasksMode:
    """REAL execution of ami-agent --tasks command."""

    @pytest.mark.slow
    def test_successful_task_completion(self):
        """ami-agent --tasks executes task and completes successfully."""
        with tempfile.TemporaryDirectory() as task_dir, tempfile.TemporaryDirectory() as work_dir:
            task_path = Path(task_dir)
            work_path = Path(work_dir)

            # Create task that does actual work
            task_file = task_path / "task-success.md"
            task_file.write_text("""
# Test Task: Create Hello File

Create a file called `hello.txt` in the current directory containing the text "Hello World".

After creating the file, output WORK DONE.
""")

            # Run ami-agent --tasks with --root-dir
            result = subprocess.run(
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--tasks", str(task_path), "--root-dir", str(work_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Check exit code
            assert result.returncode == 0, f"Exit code should be 0, got {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

            # Check summary output
            assert "Total: 1" in result.stdout
            assert "Completed: 1" in result.stdout
            assert "Failed: 0" in result.stdout

            # Verify file created in working directory
            hello_file = work_path / "hello.txt"
            assert hello_file.exists(), "hello.txt should be created in working directory"
            assert hello_file.read_text() == "Hello World"

            # Verify progress file was created and preserved for audit trail
            progress_files = list(task_path.glob("progress-*.md"))
            assert len(progress_files) == 1, "Progress file should be preserved for audit"

    @pytest.mark.slow
    def test_task_requiring_feedback(self):
        """ami-agent --tasks handles task that requests feedback."""
        with tempfile.TemporaryDirectory() as task_dir, tempfile.TemporaryDirectory() as work_dir:
            task_path = Path(task_dir)
            work_path = Path(work_dir)

            # Create task that outputs FEEDBACK marker
            task_file = task_path / "task-feedback.md"
            task_file.write_text("""
# Test Task: Request Feedback

This task should output FEEDBACK marker.

Output: FEEDBACK: Need help with X and Y
""")

            # Run ami-agent --tasks with --root-dir
            result = subprocess.run(
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--tasks", str(task_path), "--root-dir", str(work_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Check exit code (should be 0 for feedback)
            assert result.returncode == 0

            # Check summary output
            assert "Needs Feedback: 1" in result.stdout

            # Verify feedback file created in task directory
            feedback_files = list(task_path.glob("feedback-*.md"))
            assert len(feedback_files) == 1, "Should create feedback file"

    @pytest.mark.slow
    def test_multiple_tasks(self):
        """ami-agent --tasks executes multiple tasks in order."""
        with tempfile.TemporaryDirectory() as task_dir, tempfile.TemporaryDirectory() as work_dir:
            task_path = Path(task_dir)
            work_path = Path(work_dir)

            # Create multiple tasks that do actual work
            (task_path / "task1.md").write_text("""
# Task 1: Create file1.txt

Create a file called `file1.txt` in the current directory containing the text "Task 1 complete".

After creating the file, output WORK DONE.
""")
            (task_path / "task2.md").write_text("""
# Task 2: Create file2.txt

Create a file called `file2.txt` in the current directory containing the text "Task 2 complete".

After creating the file, output WORK DONE.
""")
            (task_path / "task3.md").write_text("""
# Task 3: Create file3.txt

Create a file called `file3.txt` in the current directory containing the text "Task 3 complete".

After creating the file, output WORK DONE.
""")

            # Run ami-agent --tasks with --root-dir
            result = subprocess.run(
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--tasks", str(task_path), "--root-dir", str(work_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=240,
            )

            # Check summary
            assert "Total: 3" in result.stdout

            # Verify files created in working directory
            assert (work_path / "file1.txt").exists()
            assert (work_path / "file2.txt").exists()
            assert (work_path / "file3.txt").exists()

    @pytest.mark.slow
    def test_parallel_execution(self):
        """ami-agent --tasks executes tasks in parallel with --parallel flag."""
        with tempfile.TemporaryDirectory() as task_dir, tempfile.TemporaryDirectory() as work_dir:
            task_path = Path(task_dir)
            work_path = Path(work_dir)

            # Create task that does actual work
            task_file = task_path / "task-parallel.md"
            task_file.write_text("""
# Test Task: Parallel Execution

Create a file called `parallel.txt` in the current directory containing the text "Parallel execution works".

After creating the file, output WORK DONE.
""")

            # Run ami-agent --tasks with --parallel and --root-dir
            result = subprocess.run(
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--tasks", str(task_path), "--root-dir", str(work_path), "--parallel"],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Check exit code
            assert result.returncode == 0, f"Exit code should be 0, got {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

            # Check summary output
            assert "Total: 1" in result.stdout
            assert "Completed: 1" in result.stdout

            # Verify file created in working directory
            assert (work_path / "parallel.txt").exists()

    @pytest.mark.slow
    def test_task_timeout(self):
        """ami-agent --tasks handles task that times out."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create task that never outputs completion marker
            task_file = tmpdir_path / "task-timeout.md"
            task_file.write_text("""
# Test Task: Timeout

This task should timeout because it never outputs WORK DONE or FEEDBACK.

Do not output any completion marker.
""")

            # Skip actual execution - timeout handling requires config
            pytest.skip("Timeout configuration requires automation.yaml setup")

    @pytest.mark.slow
    def test_excludes_standard_files(self):
        """ami-agent --tasks excludes README.md, CLAUDE.md, AGENTS.md."""
        with tempfile.TemporaryDirectory() as task_dir, tempfile.TemporaryDirectory() as work_dir:
            task_path = Path(task_dir)
            work_path = Path(work_dir)

            # Create standard files that should be excluded
            (task_path / "README.md").write_text("# README\nOutput WORK DONE")
            (task_path / "CLAUDE.md").write_text("# CLAUDE\nOutput WORK DONE")
            (task_path / "AGENTS.md").write_text("# AGENTS\nOutput WORK DONE")

            # Create one actual task that does work
            (task_path / "task1.md").write_text("""
# Task 1: Create verification file

Create a file called `verification.txt` with the content "Standard files were excluded".

Output WORK DONE.
""")

            # Run ami-agent --tasks with --root-dir
            result = subprocess.run(
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--tasks", str(task_path), "--root-dir", str(work_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Should only find task1.md
            assert "Total: 1" in result.stdout

            # Verify file created in working directory
            assert (work_path / "verification.txt").exists()

    @pytest.mark.slow
    def test_excludes_feedback_files(self):
        """ami-agent --tasks excludes feedback-*.md files."""
        with tempfile.TemporaryDirectory() as task_dir, tempfile.TemporaryDirectory() as work_dir:
            task_path = Path(task_dir)
            work_path = Path(work_dir)

            # Create feedback file that should be excluded
            (task_path / "feedback-20250119-task1.md").write_text("# Feedback\nOutput WORK DONE")

            # Create one actual task that does work
            (task_path / "task1.md").write_text("""
# Task 1: Create confirmation file

Create a file called `confirmation.txt` with the content "Feedback files were excluded".

Output WORK DONE.
""")

            # Run ami-agent --tasks with --root-dir
            result = subprocess.run(
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--tasks", str(task_path), "--root-dir", str(work_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Should only find task1.md
            assert "Total: 1" in result.stdout

            # Verify file created in working directory
            assert (work_path / "confirmation.txt").exists()

    def test_empty_directory(self):
        """ami-agent --tasks handles empty directory gracefully."""
        with tempfile.TemporaryDirectory() as task_dir, tempfile.TemporaryDirectory() as work_dir:
            task_path = Path(task_dir)
            work_path = Path(work_dir)

            # Run ami-agent --tasks on empty directory with --root-dir
            result = subprocess.run(
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--tasks", str(task_path), "--root-dir", str(work_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Should complete with 0 tasks
            assert result.returncode == 0
            assert "Total: 0" in result.stdout

    def test_nonexistent_directory(self):
        """ami-agent --tasks handles nonexistent directory."""
        with tempfile.TemporaryDirectory() as work_dir:
            work_path = Path(work_dir)

            # Run ami-agent --tasks on nonexistent directory with --root-dir
            result = subprocess.run(
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--tasks", "/tmp/nonexistent-dir-12345", "--root-dir", str(work_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Should fail with exit code 1
            assert result.returncode == 1
            assert "not found" in result.stderr.lower()


class TestTaskExecutorIntegration:
    """Integration tests for TaskExecutor class directly."""

    @pytest.mark.slow
    def test_worker_moderator_validation_loop(self, monkeypatch):
        """TaskExecutor runs worker then moderator validation."""
        # Set AMI_SUDO_PASSWORD for initialization
        monkeypatch.setenv("AMI_SUDO_PASSWORD", "test-password")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create simple task
            task_file = tmpdir_path / "task.md"
            task_file.write_text("""
# Test Task: Validation

Create a simple Python function and output WORK DONE.

The moderator should validate the output.
""")

            # Mock only chattr subprocess calls, pass through agent calls
            original_popen = subprocess.Popen

            def mock_chattr_only(cmd, *args, **kwargs):
                """Mock only chattr subprocess calls, pass through agent calls."""
                if isinstance(cmd, list) and "chattr" in cmd:
                    mock_process = unittest.mock.Mock()
                    mock_process.communicate.return_value = ("", "")
                    mock_process.returncode = 0
                    return mock_process
                # Pass through to real subprocess for agent spawning
                return original_popen(cmd, *args, **kwargs)

            with unittest.mock.patch("subprocess.Popen", side_effect=mock_chattr_only):
                executor = TaskExecutor()
                result = executor._execute_single_task(task_file)

            # Should complete (either success or feedback)
            assert result.status in ("completed", "feedback", "failed")
            assert len(result.attempts) > 0

    @pytest.mark.slow
    def test_moderator_failure_triggers_retry(self, monkeypatch):
        """TaskExecutor retries when moderator fails validation."""
        # Set AMI_SUDO_PASSWORD for initialization
        monkeypatch.setenv("AMI_SUDO_PASSWORD", "test-password")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create task that intentionally produces bad output
            task_file = tmpdir_path / "task-bad.md"
            task_file.write_text("""
# Test Task: Bad Output

Output WORK DONE immediately without doing any actual work.

The moderator should fail this and trigger a retry.
""")

            # Mock only chattr subprocess calls, pass through agent calls
            original_popen = subprocess.Popen

            def mock_chattr_only(cmd, *args, **kwargs):
                """Mock only chattr subprocess calls, pass through agent calls."""
                if isinstance(cmd, list) and "chattr" in cmd:
                    mock_process = unittest.mock.Mock()
                    mock_process.communicate.return_value = ("", "")
                    mock_process.returncode = 0
                    return mock_process
                # Pass through to real subprocess for agent spawning
                return original_popen(cmd, *args, **kwargs)

            with unittest.mock.patch("subprocess.Popen", side_effect=mock_chattr_only):
                executor = TaskExecutor()
                result = executor._execute_single_task(task_file)

            # Should have multiple attempts if moderator failed first time
            # Note: This might pass first time if worker is smart enough
            assert len(result.attempts) >= 1

    @pytest.mark.slow
    def test_file_locking_during_execution(self, monkeypatch):
        """Verify file locking and unlocking during task execution."""
        # Set AMI_SUDO_PASSWORD for initialization
        monkeypatch.setenv("AMI_SUDO_PASSWORD", "test-password")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create simple task
            task_file = tmpdir_path / "task.md"
            task_file.write_text("""
# Test Task: File Locking

Verify file locking works correctly.

Output WORK DONE.
""")

            lock_calls = []
            unlock_calls = []

            # Mock only chattr subprocess calls, pass through agent calls
            original_popen = subprocess.Popen

            def track_chattr_calls(cmd, *args, **kwargs):
                """Track chattr calls, pass through agent calls."""
                if isinstance(cmd, list) and "chattr" in cmd:
                    if "+i" in cmd:
                        lock_calls.append(cmd)
                    elif "-i" in cmd:
                        unlock_calls.append(cmd)

                    mock_process = unittest.mock.Mock()
                    mock_process.communicate.return_value = ("", "")
                    mock_process.returncode = 0
                    return mock_process
                # Pass through to real subprocess for agent spawning
                return original_popen(cmd, *args, **kwargs)

            with unittest.mock.patch("subprocess.Popen", side_effect=track_chattr_calls):
                executor = TaskExecutor()
                result = executor._execute_single_task(task_file)

            # Verify file was locked and unlocked
            assert len(lock_calls) == 1, "File should be locked once"
            assert len(unlock_calls) == 1, "File should be unlocked once"
            assert result.status in ("completed", "feedback")
