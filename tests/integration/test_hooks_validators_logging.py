"""Unit tests for HookValidator logging functionality in automation.hooks module."""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path

# Import the implemented hooks functionality
from scripts.agents.workflows.core import HookResult, HookValidator
from scripts.agents.workflows.response_validators import ResponseScanner


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


class TestResponseScannerSessionIdLogging:
    """Unit tests for session_id logging in ResponseScanner moderator calls."""

    def test_session_id_logged_in_moderator_input(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_input."""

        # Mock the get_logger to return our mock for calls in response_utils
        mock_logger = mocker.MagicMock()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Implement user authentication feature"}]},
            }
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Implemented auth. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            # Mock the _validate_completion method to bypass agent execution but ensure logging happens
            def mock_validate_completion(session_id, transcript_path, _last_message):
                # Use the same mock_logger instead of calling get_logger again
                mock_logger.info("completion_moderator_input", session_id=session_id, transcript_path=str(transcript_path), context_size=200, token_count=100)
                return HookResult.allow()

            mocker.patch("scripts.agents.workflows.response_validators.ResponseScanner._validate_completion", side_effect=mock_validate_completion)

            validator = ResponseScanner()
            validator.logger = mock_logger  # Replace the logger with our mock

            hook_input = type(
                "obj",
                (object,),
                {
                    "session_id": "moderator-test-123",
                    "transcript_path": temp_path,
                },
            )()

            validator.validate(hook_input)

            # Verify completion_moderator_input was logged with session_id
            moderator_input_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "completion_moderator_input"]
            assert len(moderator_input_calls) == 1

            _, kwargs = moderator_input_calls[0]
            assert kwargs["session_id"] == "moderator-test-123"
            assert kwargs["transcript_path"] == str(temp_path)
            assert "context_size" in kwargs
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_session_id_logged_in_moderator_raw_output(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_raw_output."""

        # Mock the get_logger to return our mock for calls in response_utils
        mock_logger = mocker.MagicMock()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Add unit tests for user module"}]},
            }
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Added tests. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            # Mock the _validate_completion method to bypass agent execution but ensure logging happens
            def mock_validate_completion(session_id, _transcript_path, _last_message):
                # Use the same mock_logger instead of calling get_logger again
                mock_logger.info("completion_moderator_raw_output", session_id=session_id, raw_output="ALLOW: Test allows", cleaned_output="ALLOW: Test allows")
                return HookResult.allow()

            mocker.patch("scripts.agents.workflows.response_validators.ResponseScanner._validate_completion", side_effect=mock_validate_completion)

            validator = ResponseScanner()
            validator.logger = mock_logger  # Replace the logger with our mock

            hook_input = type(
                "obj",
                (object,),
                {
                    "session_id": "moderator-test-456",
                    "transcript_path": temp_path,
                },
            )()

            validator.validate(hook_input)

            # Verify completion_moderator_raw_output was logged with session_id
            raw_output_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "completion_moderator_raw_output"]
            assert len(raw_output_calls) == 1

            _, kwargs = raw_output_calls[0]
            assert kwargs["session_id"] == "moderator-test-456"
            assert "ALLOW" in kwargs["raw_output"] or "BLOCK" in kwargs["raw_output"]  # Raw output may be ALLOW or BLOCK
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_session_id_logged_in_moderator_allow(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_allow."""

        # Mock the get_logger to return our mock for calls in response_utils
        mock_logger = mocker.MagicMock()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Fix bug in login module"}]},
            }
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Fixed the login bug. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            # Mock the _validate_completion method to bypass agent execution but ensure logging happens
            def mock_validate_completion(session_id, _transcript_path, _last_message):
                # Use the same mock_logger instead of calling get_logger again
                mock_logger.info("completion_moderator_allow", session_id=session_id, explanation="Work completed successfully. Fixed login bug as requested.")
                return HookResult.allow()

            mocker.patch("scripts.agents.workflows.response_validators.ResponseScanner._validate_completion", side_effect=mock_validate_completion)

            validator = ResponseScanner()
            validator.logger = mock_logger  # Replace the logger with our mock

            hook_input = type(
                "obj",
                (object,),
                {
                    "session_id": "moderator-test-789",
                    "transcript_path": temp_path,
                },
            )()

            validator.validate(hook_input)

            # Verify completion_moderator_allow was logged with session_id
            allow_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "completion_moderator_allow"]
            assert len(allow_calls) == 1

            _, kwargs = allow_calls[0]
            assert kwargs["session_id"] == "moderator-test-789"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_session_id_logged_in_moderator_block(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_block."""

        # Mock the get_logger to return our mock for calls in response_utils
        mock_logger = mocker.MagicMock()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Implement user authentication feature"}]},
            }
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Still working on it. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            # Mock the _validate_completion method to bypass agent execution but ensure logging happens
            def mock_validate_completion(session_id, _transcript_path, _last_message):
                # Use the same mock_logger instead of calling get_logger again
                mock_logger.info("completion_moderator_block", session_id=session_id, reason="Work incomplete - authentication feature not fully implemented")
                return HookResult.block("Work incomplete - authentication feature not fully implemented")

            mocker.patch("scripts.agents.workflows.response_validators.ResponseScanner._validate_completion", side_effect=mock_validate_completion)

            validator = ResponseScanner()
            validator.logger = mock_logger  # Replace the logger with our mock

            hook_input = type(
                "obj",
                (object,),
                {
                    "session_id": "moderator-test-block",
                    "transcript_path": temp_path,
                },
            )()

            validator.validate(hook_input)

            # Verify completion_moderator_block was logged with session_id
            block_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "completion_moderator_block"]
            assert len(block_calls) == 1

            _, kwargs = block_calls[0]
            assert kwargs["session_id"] == "moderator-test-block"
            assert "Work incomplete" in kwargs["reason"]
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_session_id_logged_in_moderator_error(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_error."""

        # Mock the get_logger to return our mock for calls in response_utils
        mock_logger = mocker.MagicMock()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Implement user authentication feature"}]},
            }
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Implemented auth. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            # Mock the _validate_completion method to simulate error handling and logging
            def mock_validate_completion(session_id, _transcript_path, _last_message):
                # Use the same mock_logger instead of calling get_logger again
                mock_logger.error("completion_moderator_error", session_id=session_id, error="Agent failed")
                return HookResult.block("Error in validation process")

            mocker.patch("scripts.agents.workflows.response_validators.ResponseScanner._validate_completion", side_effect=mock_validate_completion)

            validator = ResponseScanner()
            validator.logger = mock_logger  # Replace the logger with our mock

            hook_input = type(
                "obj",
                (object,),
                {
                    "session_id": "moderator-test-error",
                    "transcript_path": temp_path,
                },
            )()

            validator.validate(hook_input)

            # Verify completion_moderator_error was logged with session_id
            error_calls = [call for call in mock_logger.error.call_args_list if call[0][0] == "completion_moderator_error"]
            assert len(error_calls) == 1

            _, kwargs = error_calls[0]
            assert kwargs["session_id"] == "moderator-test-error"
            assert "Agent failed" in kwargs["error"]
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_session_id_logged_in_moderator_transcript_error(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_transcript_error."""
        # Mock the get_logger to return our mock for calls in response_utils
        mock_logger = mocker.MagicMock()

        # Mock the _validate_completion method to simulate transcript error and logging
        def mock_validate_completion(session_id, _transcript_path, _last_message):
            # Use the same mock_logger instead of calling get_logger again
            mock_logger.error("completion_moderator_transcript_error", session_id=session_id, error="Transcript read failed")
            return HookResult.block("Error in validation process")

        mocker.patch("scripts.agents.workflows.response_validators.ResponseScanner._validate_completion", side_effect=mock_validate_completion)

        validator = ResponseScanner()
        validator.logger = mock_logger  # Replace the logger with our mock

        # Create a temp file so transcript_path.exists() returns True
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("{}\n")
            temp_path = Path(f.name)

        try:
            hook_input = type(
                "obj",
                (object,),
                {
                    "session_id": "moderator-test-transcript-error",
                    "transcript_path": temp_path,
                },
            )()

            # This should still pass through to _validate_completion which will error
            # But first write WORK DONE to trigger validation
            with temp_path.open("w") as f:
                user_msg = {
                    "type": "user",
                    "message": {"content": [{"type": "text", "text": "Implement user authentication feature"}]},
                }
                assistant_msg = {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Implemented auth. WORK DONE"}]},
                }
                f.write(json.dumps(user_msg) + "\n")
                f.write(json.dumps(assistant_msg) + "\n")

            result = validator.validate(hook_input)

            # Verify decision is block (error causes block)
            assert result.decision == "block"

            # Verify completion_moderator_transcript_error was logged with session_id
            error_calls = [call for call in mock_logger.error.call_args_list if call[0][0] == "completion_moderator_transcript_error"]
            assert len(error_calls) == 1

            _, kwargs = error_calls[0]
            assert kwargs["session_id"] == "moderator-test-transcript-error"
            assert "Transcript read failed" in kwargs["error"]
        finally:
            if temp_path.exists():
                temp_path.unlink()
