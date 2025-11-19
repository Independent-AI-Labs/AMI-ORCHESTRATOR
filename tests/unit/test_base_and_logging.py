"""Unit tests for HookValidator base class and logging functionality."""

import json
import sys
from io import StringIO

# Import the implemented hooks functionality
from scripts.agents.workflows.core import HookResult, HookValidator


class TestHookValidatorBase:
    """Unit tests for HookValidator base class."""


class TestSessionIdLogging:
    """Unit tests for session_id logging in hook events."""

    def test_session_id_logged_in_hook_execution(self, mocker):
        """HookValidator logs session_id in hook_execution event."""
        # Mock the logger
        mock_logger = mocker.MagicMock()

        # Create a simple validator
        class SimpleValidator(HookValidator):
            def validate(self, _hook_input):
                return HookResult.allow()

        # Create validator and replace its logger with the mock
        validator = SimpleValidator()
        validator.logger = mock_logger

        # Mock stdin with session_id
        old_stdin = sys.stdin
        hook_data = {
            "session_id": "test-session-123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        }
        sys.stdin = StringIO(json.dumps(hook_data))

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            validator.run()

            # Verify hook_execution was logged with session_id
            hook_execution_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "hook_execution"]
            assert len(hook_execution_calls) == 1

            # Check that session_id was passed as keyword argument
            _, kwargs = hook_execution_calls[0]
            assert kwargs["session_id"] == "test-session-123"
            assert kwargs["hook_name"] == "SimpleValidator"
            assert kwargs["event"] == "PreToolUse"
            assert kwargs["tool"] == "Bash"
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_session_id_logged_in_hook_result(self, mocker):
        """HookValidator logs session_id in hook_result event."""
        mock_logger = mocker.MagicMock()

        class SimpleValidator(HookValidator):
            def validate(self, _hook_input):
                return HookResult.deny("test reason")

        validator = SimpleValidator()
        validator.logger = mock_logger

        old_stdin = sys.stdin
        hook_data = {
            "session_id": "test-session-456",
            "hook_event_name": "PreToolUse",
        }
        sys.stdin = StringIO(json.dumps(hook_data))

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            validator.run()

            # Verify hook_result was logged with session_id
            hook_result_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "hook_result"]
            assert len(hook_result_calls) == 1

            _, kwargs = hook_result_calls[0]
            assert kwargs["session_id"] == "test-session-456"
            assert kwargs["decision"] == "deny"
            assert kwargs["reason"] == "test reason"
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_session_id_logged_in_hook_error_with_hook_input(self, mocker):
        """HookValidator logs session_id in hook_error when hook_input available."""
        mock_logger = mocker.MagicMock()

        class FailingValidator(HookValidator):
            def validate(self, _hook_input):
                raise RuntimeError("Validation failed")

        validator = FailingValidator()
        validator.logger = mock_logger

        old_stdin = sys.stdin
        hook_data = {
            "session_id": "test-session-789",
            "hook_event_name": "Stop",
        }
        sys.stdin = StringIO(json.dumps(hook_data))

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            validator.run()

            # Verify hook_error was logged with session_id
            error_calls = [call for call in mock_logger.error.call_args_list if call[0][0] == "hook_error"]
            assert len(error_calls) == 1

            _, kwargs = error_calls[0]
            assert kwargs["session_id"] == "test-session-789"
            assert "Validation failed" in kwargs["error"]
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_session_id_not_in_hook_error_without_hook_input(self, mocker):
        """HookValidator omits session_id from hook_error when hook_input unavailable."""
        mock_logger = mocker.MagicMock()

        class SimpleValidator(HookValidator):
            def validate(self, _hook_input):
                return HookResult.allow()

        validator = SimpleValidator()
        validator.logger = mock_logger

        # Invalid JSON to trigger JSONDecodeError before hook_input is created
        old_stdin = sys.stdin
        sys.stdin = StringIO("invalid json{")

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            validator.run()

            # Verify error was logged without session_id
            error_calls = [call for call in mock_logger.error.call_args_list if call[0][0] == "invalid_hook_input"]
            assert len(error_calls) == 1

            # Should have error but no session_id
            _, kwargs = error_calls[0]
            assert "error" in kwargs
            assert "session_id" not in kwargs
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
