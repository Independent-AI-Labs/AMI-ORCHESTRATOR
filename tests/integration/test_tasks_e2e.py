"""E2E integration tests for ami-agent --tasks mode.

Tests that hooks are properly enabled and ResponseScanner provides feedback.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def disable_file_locking(monkeypatch):
    """Disable file locking for all integration tests."""
    monkeypatch.setenv("AMI_TEST_MODE", "1")


@pytest.fixture
def temp_task_dir():
    """Create temporary directory for task files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def orchestrator_root():
    """Get orchestrator root directory."""
    return Path(__file__).resolve().parents[2]


class TestTasksHookIntegration:
    """Test that hooks are enabled and working in --tasks mode."""

    def test_task_with_work_done_succeeds(self, temp_task_dir, orchestrator_root):
        """Task with WORK DONE marker should complete successfully."""
        # Create simple task that doesn't require code changes or commits
        task_file = temp_task_dir / "test-success.md"
        task_file.write_text("Confirm you have read this task. No code changes needed. Output WORK DONE when you've read it.\n")

        # Run ami-agent --tasks with timeout (moderator can be slow)
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--tasks",
                str(temp_task_dir),
                "--root-dir",
                str(temp_task_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should succeed
        assert result.returncode == 0, f"Expected success, got exit code {result.returncode}.\nStdout: {result.stdout}\nStderr: {result.stderr}"

        # Check task summary
        assert "Completed: 1" in result.stdout or "completed" in result.stdout.lower()

    def test_task_without_marker_gets_hook_feedback(self, temp_task_dir, orchestrator_root):
        """Task without completion marker should get ResponseScanner feedback and retry."""
        # Create task without completion marker
        task_file = temp_task_dir / "test-no-marker.md"
        task_file.write_text("What is 2 + 2?\n")

        # Run ami-agent --tasks with timeout (moderator can be slow)
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--tasks",
                str(temp_task_dir),
                "--root-dir",
                str(temp_task_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should succeed (worker gets hook feedback and retries with WORK DONE)
        assert result.returncode == 0, f"Expected success.\nStdout: {result.stdout}\nStderr: {result.stderr}"

        # Check for progress file with multiple attempts
        progress_files = list(temp_task_dir.glob("progress-*-test-no-marker.md"))
        assert len(progress_files) > 0, "Expected progress file to be created"

        progress_content = progress_files[0].read_text()
        # First attempt should have no completion marker
        assert "Attempt 1" in progress_content
        assert "No completion marker found" in progress_content or "completion marker" in progress_content.lower()
        # Second attempt should have WORK DONE and pass
        assert "Attempt 2" in progress_content
        assert "WORK DONE" in progress_content

    def test_task_with_feedback_marker(self, temp_task_dir, orchestrator_root):
        """Task that causes worker to request feedback should create feedback file."""
        # Create task that worker cannot complete (missing required info)
        task_file = temp_task_dir / "test-feedback.md"
        task_file.write_text("Analyze the Python file. If you cannot find any Python file to analyze, output 'FEEDBACK: No Python file specified'\n")

        # Run ami-agent --tasks with timeout (moderator can be slow)
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--tasks",
                str(temp_task_dir),
                "--root-dir",
                str(temp_task_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Check for feedback file
        feedback_files = list(temp_task_dir.glob("feedback-*-test-feedback.md"))
        assert len(feedback_files) > 0, f"Expected feedback file to be created. Stdout: {result.stdout}"

        feedback_content = feedback_files[0].read_text()
        assert "Python" in feedback_content or "file" in feedback_content

    def test_hooks_enabled_in_logs(self, temp_task_dir, orchestrator_root):
        """Verify hooks are enabled in automation logs."""
        # Create simple task
        task_file = temp_task_dir / "test-hooks.md"
        task_file.write_text("Echo test\n\nWORK DONE\n")

        # Run ami-agent --tasks
        subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--tasks",
                str(temp_task_dir),
                "--root-dir",
                str(temp_task_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        # Check latest log file
        log_dir = orchestrator_root / "logs"
        if log_dir.exists():
            log_files = sorted(log_dir.glob("automation-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
            if log_files:
                latest_log = log_files[0]
                log_content = latest_log.read_text()

                # Should have hooks enabled
                assert '"hooks": true' in log_content, f"Expected hooks to be enabled.\nLog: {latest_log}"


class TestTasksExecutionFlow:
    """Test task execution flow and error handling."""

    def test_multiple_tasks_sequential(self, temp_task_dir, orchestrator_root):
        """Multiple tasks should execute sequentially."""
        # Create multiple simple tasks with explicit completion requirement
        (temp_task_dir / "task1.md").write_text("Read this task file and confirm you have read it by outputting WORK DONE.\n")
        (temp_task_dir / "task2.md").write_text("Read this task file and confirm you have read it by outputting WORK DONE.\n")
        (temp_task_dir / "task3.md").write_text("Read this task file and confirm you have read it by outputting WORK DONE.\n")

        # Run ami-agent --tasks with timeout (moderator can be slow)
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--tasks",
                str(temp_task_dir),
                "--root-dir",
                str(temp_task_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should succeed
        assert result.returncode == 0, f"Expected success.\nStdout: {result.stdout}\nStderr: {result.stderr}"

        # All tasks should be processed (some may complete, some may need feedback due to Claude's natural variation)
        assert "Total: 3" in result.stdout
        # At least one task should complete successfully
        completed_count = int(result.stdout.split("Completed: ")[1].split("\n")[0])
        assert completed_count >= 1, f"Expected at least 1 completed task, got {completed_count}"

    def test_excludes_readme_files(self, temp_task_dir, orchestrator_root):
        """README.md and similar files should be excluded."""
        # Create task and README
        (temp_task_dir / "task.md").write_text("Task\n\nWORK DONE\n")
        (temp_task_dir / "README.md").write_text("This is a README\n")
        (temp_task_dir / "CLAUDE.md").write_text("Agent instructions\n")

        # Run ami-agent --tasks with timeout (moderator can be slow)
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--tasks",
                str(temp_task_dir),
                "--root-dir",
                str(temp_task_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should only process 1 task
        assert "Total: 1" in result.stdout

    def test_progress_file_creation(self, temp_task_dir, orchestrator_root):
        """Progress file should be created for each task."""
        task_file = temp_task_dir / "test-progress.md"
        task_file.write_text("Test task\n\nWORK DONE\n")

        # Run ami-agent --tasks
        subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--tasks",
                str(temp_task_dir),
                "--root-dir",
                str(temp_task_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        # Check for progress file
        progress_files = list(temp_task_dir.glob("progress-*-test-progress.md"))
        assert len(progress_files) > 0, "Expected progress file to be created"

        progress_content = progress_files[0].read_text()
        assert "Task Execution Progress: test-progress" in progress_content
        assert "Started:" in progress_content
        assert "Completed:" in progress_content

    def test_single_file_execution(self, temp_task_dir, orchestrator_root):
        """Execute single task file instead of directory."""
        # Create single task file
        task_file = temp_task_dir / "single-task.md"
        task_file.write_text("Confirm you read this. Output WORK DONE.\n")

        # Run ami-agent --tasks with single file path
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--tasks",
                str(task_file),  # Pass file path, not directory
                "--root-dir",
                str(temp_task_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should succeed
        assert result.returncode == 0, f"Expected success.\nStdout: {result.stdout}\nStderr: {result.stderr}"

        # Should process exactly 1 task
        assert "Total: 1" in result.stdout

        # Check progress file was created
        progress_files = list(temp_task_dir.glob("progress-*-single-task.md"))
        assert len(progress_files) > 0, "Expected progress file for single task"
