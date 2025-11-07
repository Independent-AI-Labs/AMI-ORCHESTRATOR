"""Unit tests for sync module."""

import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.automation.sync import SyncAttempt, SyncExecutor, SyncResult

# Test constants
SINGLE_ATTEMPT = 1
TWO_ATTEMPTS = 2
FIRST_ATTEMPT_INDEX = 0
SECOND_ATTEMPT_INDEX = 1
TOTAL_DURATION = 2.0
ATTEMPT_DURATION = 1.23


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_sync_result_creation(self) -> None:
        """SyncResult can be created with required fields."""
        result = SyncResult(
            module_path=Path("/test/module"),
            status="synced",
        )

        assert result.module_path == Path("/test/module")
        assert result.status == "synced"
        assert result.attempts == []
        assert result.error is None
        assert result.total_duration == 0.0

    def test_sync_result_with_attempts(self) -> None:
        """SyncResult stores attempts correctly."""
        attempt = SyncAttempt(
            attempt_num=1,
            worker_output="output",
            moderator_decision="PASS",
            duration=1.5,
        )

        result = SyncResult(
            module_path=Path("/test/module"),
            status="synced",
            attempts=[attempt],
            total_duration=TOTAL_DURATION,
        )

        assert len(result.attempts) == SINGLE_ATTEMPT
        assert result.attempts[FIRST_ATTEMPT_INDEX].attempt_num == SINGLE_ATTEMPT
        assert result.total_duration == TOTAL_DURATION


class TestSyncAttempt:
    """Tests for SyncAttempt dataclass."""

    def test_sync_attempt_creation(self) -> None:
        """SyncAttempt can be created with all fields."""
        attempt = SyncAttempt(
            attempt_num=1,
            worker_output="test output",
            moderator_decision="PASS",
            duration=ATTEMPT_DURATION,
        )

        assert attempt.attempt_num == SINGLE_ATTEMPT
        assert attempt.worker_output == "test output"
        assert attempt.moderator_decision == "PASS"
        assert attempt.duration == ATTEMPT_DURATION


class TestSyncExecutor:
    """Tests for SyncExecutor class."""

    @pytest.fixture
    def mock_config(self) -> Mock:
        """Create mock config."""
        config = Mock()
        # Use side_effect to return different values for different keys
        config.get.side_effect = lambda key, default=None: {
            "sync.timeout": 1800,
            "prompts.dir": "config/prompts",
        }.get(key, default)
        config.root = Path("/test/root")
        return config

    @pytest.fixture
    def executor(self, mock_config: Mock) -> Generator[SyncExecutor, None, None]:
        """Create SyncExecutor with mocked dependencies."""
        with (
            patch("scripts.automation.sync.get_config") as mock_get_config,
            patch("scripts.automation.sync.get_logger") as mock_get_logger,
            patch("scripts.automation.sync.get_agent_cli") as mock_get_cli,
        ):
            mock_get_config.return_value = mock_config
            mock_get_logger.return_value = Mock()
            mock_get_cli.return_value = Mock()

            executor = SyncExecutor()
            yield executor

    def test_executor_initialization(self, executor: SyncExecutor) -> None:
        """SyncExecutor initializes with dependencies."""
        assert executor.config is not None
        assert executor.logger is not None
        assert executor.cli is not None

    def test_sync_module_success_first_attempt(self, executor: SyncExecutor, tmp_path: Path) -> None:
        """Sync succeeds on first attempt with WORK DONE."""
        module_path = tmp_path / "test_module"
        module_path.mkdir()

        # Mock worker output with WORK DONE
        executor.cli.run_print = Mock(
            side_effect=[
                ("All changes committed and pushed.\n\nWORK DONE", None),
                ("PASS: Module is fully synced", None),
            ]
        )

        result = executor.sync_module(module_path)

        assert result.status == "synced"
        assert len(result.attempts) == SINGLE_ATTEMPT
        assert result.attempts[FIRST_ATTEMPT_INDEX].attempt_num == SINGLE_ATTEMPT
        assert "WORK DONE" in result.attempts[FIRST_ATTEMPT_INDEX].worker_output
        assert "PASS" in result.attempts[FIRST_ATTEMPT_INDEX].moderator_decision
        assert result.error is None

    def test_sync_module_feedback_then_success(self, executor: SyncExecutor, tmp_path: Path) -> None:
        """Sync succeeds after worker provides feedback."""
        module_path = tmp_path / "test_module"
        module_path.mkdir()

        # First attempt: feedback, second attempt: success
        executor.cli.run_print = Mock(
            side_effect=[
                ("FEEDBACK: Tests are failing, need to fix", None),
                ("FAIL: Tests still failing", None),
                ("Fixed tests.\n\nWORK DONE", None),
                ("PASS: All tests passing, module synced", None),
            ]
        )

        result = executor.sync_module(module_path)

        assert result.status == "synced"
        assert len(result.attempts) == TWO_ATTEMPTS
        assert "FEEDBACK" in result.attempts[FIRST_ATTEMPT_INDEX].worker_output
        assert "FAIL" in result.attempts[FIRST_ATTEMPT_INDEX].moderator_decision
        assert "WORK DONE" in result.attempts[SECOND_ATTEMPT_INDEX].worker_output
        assert "PASS" in result.attempts[SECOND_ATTEMPT_INDEX].moderator_decision

    def test_sync_module_timeout(self, executor: SyncExecutor, tmp_path: Path) -> None:
        """Sync times out if worker never completes."""
        module_path = tmp_path / "test_module"
        module_path.mkdir()

        # Set very short timeout
        executor.config.get.side_effect = lambda key, default=None: {
            "sync.timeout": 0.1,
            "prompts.dir": "config/prompts",
        }.get(key, default)

        # Worker never completes
        def slow_worker(*_args: object, **_kwargs: object) -> tuple[str, None]:
            time.sleep(0.05)
            return ("Still working...", None)

        executor.cli.run_print = Mock(side_effect=slow_worker)

        result = executor.sync_module(module_path)

        assert result.status == "timeout"
        assert result.error is not None
        assert "Timeout" in result.error
        assert len(result.attempts) >= 1

    def test_sync_module_moderator_fail(self, executor: SyncExecutor, tmp_path: Path) -> None:
        """Sync retries when moderator returns FAIL."""
        module_path = tmp_path / "test_module"
        module_path.mkdir()

        # First attempt fails, second succeeds
        executor.cli.run_print = Mock(
            side_effect=[
                ("WORK DONE", None),
                ("FAIL: Uncommitted changes detected", None),
                ("Committed changes.\n\nWORK DONE", None),
                ("PASS: All changes committed", None),
            ]
        )

        result = executor.sync_module(module_path)

        assert result.status == "synced"
        assert len(result.attempts) == TWO_ATTEMPTS

    def test_sync_module_creates_progress_file(self, executor: SyncExecutor, tmp_path: Path) -> None:
        """Sync creates and cleans up progress file."""
        module_path = tmp_path / "test_module"
        module_path.mkdir()

        executor.cli.run_print = Mock(
            side_effect=[
                ("WORK DONE", None),
                ("PASS", None),
            ]
        )

        # Check progress file is created during execution
        with patch.object(Path, "write_text") as mock_write:
            result = executor.sync_module(module_path)

            # Progress file should be written to
            assert mock_write.called

        assert result.status == "synced"

    def test_sync_module_incomplete_worker(self, executor: SyncExecutor, tmp_path: Path) -> None:
        """Sync handles worker output without completion marker."""
        module_path = tmp_path / "test_module"
        module_path.mkdir()

        # Worker doesn't signal completion initially
        executor.cli.run_print = Mock(
            side_effect=[
                ("Working on it...", None),  # No WORK DONE or FEEDBACK
                ("FAIL: No completion marker", None),
                ("Done.\n\nWORK DONE", None),
                ("PASS", None),
            ]
        )

        result = executor.sync_module(module_path)

        assert result.status == "synced"
        assert len(result.attempts) == TWO_ATTEMPTS

    def test_sync_module_custom_timeout(self, executor: SyncExecutor, tmp_path: Path) -> None:
        """Sync respects custom timeout configuration."""
        module_path = tmp_path / "test_module"
        module_path.mkdir()

        # Set custom timeout
        custom_timeout = 0.2
        executor.config.get.side_effect = lambda key, default=None: {
            "sync.timeout": custom_timeout,
            "prompts.dir": "config/prompts",
        }.get(key, default)

        start_time = time.time()

        def slow_worker(*_args: object, **_kwargs: object) -> tuple[str, None]:
            time.sleep(0.1)
            return ("Working...", None)

        executor.cli.run_print = Mock(side_effect=slow_worker)

        result = executor.sync_module(module_path)
        elapsed = time.time() - start_time

        assert result.status == "timeout"
        assert elapsed < custom_timeout + 0.5  # Some tolerance
