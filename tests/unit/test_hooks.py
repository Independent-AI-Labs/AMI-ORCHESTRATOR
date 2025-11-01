"""Unit tests for automation.hooks module."""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path

import pytest

# Import will fail until we implement hooks.py - that's expected in TDD
try:
    from scripts.automation.hooks import (
        CodeQualityValidator,
        CommandValidator,
        HookInput,
        HookResult,
        HookValidator,
        ResponseScanner,
    )
except ImportError:
    HookInput = None
    HookResult = None
    HookValidator = None
    CommandValidator = None
    CodeQualityValidator = None
    ResponseScanner = None


class TestHookInput:
    """Unit tests for HookInput."""

    @pytest.mark.skipif(HookInput is None, reason="HookInput not implemented yet")
    def test_from_stdin_valid_json(self):
        """HookInput.from_stdin() parses valid JSON."""
        hook_data = {
            "session_id": "test-123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "transcript_path": "/tmp/transcript.jsonl",
        }

        # Mock stdin
        old_stdin = sys.stdin
        sys.stdin = StringIO(json.dumps(hook_data))

        try:
            result = HookInput.from_stdin()
            assert result.session_id == "test-123"
            assert result.hook_event_name == "PreToolUse"
            assert result.tool_name == "Bash"
            assert result.tool_input["command"] == "ls -la"
        finally:
            sys.stdin = old_stdin

    @pytest.mark.skipif(HookInput is None, reason="HookInput not implemented yet")
    def test_from_stdin_missing_optional_fields(self):
        """HookInput handles missing optional fields."""
        hook_data = {"session_id": "test-123", "hook_event_name": "Stop"}

        old_stdin = sys.stdin
        sys.stdin = StringIO(json.dumps(hook_data))

        try:
            result = HookInput.from_stdin()
            assert result.session_id == "test-123"
            assert result.tool_name is None
            assert result.tool_input is None
        finally:
            sys.stdin = old_stdin

    @pytest.mark.skipif(HookInput is None, reason="HookInput not implemented yet")
    def test_from_stdin_invalid_json(self):
        """HookInput raises error on invalid JSON."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("not valid json{")

        try:
            with pytest.raises(json.JSONDecodeError):
                HookInput.from_stdin()
        finally:
            sys.stdin = old_stdin


class TestHookResult:
    """Unit tests for HookResult."""

    @pytest.mark.skipif(HookResult is None, reason="HookResult not implemented yet")
    def test_allow_result(self):
        """HookResult.allow() creates allow result."""
        result = HookResult.allow()

        assert result.decision is None or result.decision == "allow"
        json_output = result.to_json()
        # Empty JSON or minimal JSON for allow
        data = json.loads(json_output)
        assert data.get("decision") in (None, "allow")

    @pytest.mark.skipif(HookResult is None, reason="HookResult not implemented yet")
    def test_deny_result(self):
        """HookResult.deny() creates deny result."""
        result = HookResult.deny("test reason")

        assert result.decision == "deny"
        assert result.reason == "test reason"

        json_output = result.to_json()
        data = json.loads(json_output)
        assert data["decision"] == "deny"
        assert data["reason"] == "test reason"

    @pytest.mark.skipif(HookResult is None, reason="HookResult not implemented yet")
    def test_block_result(self):
        """HookResult.block() creates block result."""
        result = HookResult.block("block reason")

        assert result.decision == "block"
        assert result.reason == "block reason"

        json_output = result.to_json()
        data = json.loads(json_output)
        assert data["decision"] == "block"
        assert data["reason"] == "block reason"


class TestCommandValidator:
    """Unit tests for CommandValidator."""

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_validate_allowed_command(self):
        """CommandValidator allows safe commands."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "ls -la"}})()

        result = validator.validate(hook_input)
        assert result.decision is None or result.decision == "allow"

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_direct_python(self):
        """CommandValidator denies direct python calls."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "python3 script.py"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "ami-run" in result.reason.lower()

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_pip_install(self):
        """CommandValidator denies pip commands."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "pip install package"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "pyproject.toml" in result.reason or "ami-uv" in result.reason

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_direct_uv(self):
        """CommandValidator denies direct uv."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "uv pip install package"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "ami-uv" in result.reason.lower()

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_git_commit(self):
        """CommandValidator denies direct git commit."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "message"'}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "git_commit.sh" in result.reason

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_git_push(self):
        """CommandValidator denies direct git push."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "git_push.sh" in result.reason

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_hook_bypass(self):
        """CommandValidator denies --no-verify."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": 'git commit --no-verify -m "msg"'}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "bypass" in result.reason.lower() or "forbidden" in result.reason.lower()

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_background_ampersand(self):
        """CommandValidator denies & operator."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "long_command &"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "run_in_background" in result.reason or "&" in result.reason

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_semicolon(self):
        """CommandValidator denies semicolon."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "cmd1; cmd2"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "separate" in result.reason.lower() or "&&" in result.reason

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_or_operator(self):
        """CommandValidator denies || operator."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "cmd1 || cmd2"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "||" in result.reason or "separate" in result.reason.lower()

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_append_redirect(self):
        """CommandValidator denies >> redirect."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "echo text >> file.txt"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "edit" in result.reason.lower() or "write" in result.reason.lower()

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_sed_inplace(self):
        """CommandValidator denies sed -i."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "sed -i 's/old/new/' file.txt"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "edit" in result.reason.lower()

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_deny_and_operator(self):
        """CommandValidator denies && operator."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "cd dir && ls"}})()

        result = validator.validate(hook_input)
        # Should deny (user changed behavior to block &&)
        assert result.decision == "deny"
        assert "&&" in result.reason or "separate" in result.reason.lower()

    @pytest.mark.skipif(CommandValidator is None, reason="CommandValidator not implemented yet")
    def test_non_bash_tool_allowed(self):
        """CommandValidator ignores non-Bash tools."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Read", "tool_input": {"file_path": "/some/file.txt"}})()

        result = validator.validate(hook_input)
        assert result.decision is None or result.decision == "allow"


class TestResponseScanner:
    """Unit tests for ResponseScanner."""

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_scan_no_transcript_allows(self):
        """ResponseScanner allows if no transcript."""
        validator = ResponseScanner()

        hook_input = type("obj", (object,), {"transcript_path": None})()

        result = validator.validate(hook_input)
        assert result.decision is None or result.decision == "allow"

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_scan_missing_transcript_allows(self):
        """ResponseScanner allows if transcript doesn't exist."""
        validator = ResponseScanner()

        hook_input = type("obj", (object,), {"transcript_path": Path("/nonexistent/transcript.jsonl")})()

        result = validator.validate(hook_input)
        assert result.decision is None or result.decision == "allow"

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_scan_completion_marker_allows(self, mocker):
        """ResponseScanner allows 'WORK DONE' marker."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Create user and assistant messages for context
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Do the task"}]},
            }
            transcript_data = {
                "type": "assistant",
                "uuid": "test-123",
                "message": {"content": [{"type": "text", "text": "I've completed the task. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(transcript_data) + "\n")
            temp_path = Path(f.name)

        try:
            # Mock agent CLI to return ALLOW
            mock_agent_cli = mocker.MagicMock()
            mock_agent_cli.run_print.return_value = ("ALLOW", None)
            mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

            validator = ResponseScanner()
            hook_input = type("obj", (object,), {"session_id": "test-session", "transcript_path": temp_path})()

            result = validator.validate(hook_input)
            assert result.decision is None or result.decision == "allow"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_scan_feedback_marker_allows(self, mocker):
        """ResponseScanner allows 'FEEDBACK:' marker."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Create user and assistant messages for context
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Do the task"}]},
            }
            transcript_data = {
                "type": "assistant",
                "uuid": "test-123",
                "message": {"content": [{"type": "text", "text": "I'm stuck. FEEDBACK: need help with X"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(transcript_data) + "\n")
            temp_path = Path(f.name)

        try:
            # Mock agent CLI to return ALLOW
            mock_agent_cli = mocker.MagicMock()
            mock_agent_cli.run_print.return_value = ("ALLOW", None)
            mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

            validator = ResponseScanner()
            hook_input = type("obj", (object,), {"session_id": "test-session", "transcript_path": temp_path})()

            result = validator.validate(hook_input)
            assert result.decision is None or result.decision == "allow"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_scan_violation_blocks(self):
        """ResponseScanner blocks prohibited phrases."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            transcript_data = {
                "type": "assistant",
                "uuid": "test-123",
                "message": {"content": [{"type": "text", "text": "You're absolutely right about that."}]},
            }
            f.write(json.dumps(transcript_data) + "\n")
            temp_path = Path(f.name)

        try:
            validator = ResponseScanner()
            hook_input = type("obj", (object,), {"transcript_path": temp_path})()

            result = validator.validate(hook_input)
            assert result.decision == "block"
            assert "violation" in result.reason.lower() or "right" in result.reason.lower()
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_scan_no_marker_allows(self):
        """ResponseScanner allows if no violations (prevents infinite loop)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            transcript_data = {"type": "assistant", "uuid": "test-123", "message": {"content": [{"type": "text", "text": "I did some work on the task."}]}}
            f.write(json.dumps(transcript_data) + "\n")
            temp_path = Path(f.name)

        try:
            validator = ResponseScanner()
            hook_input = type("obj", (object,), {"transcript_path": temp_path})()

            result = validator.validate(hook_input)
            # Should block (not allow) without completion markers
            assert result.decision == "block"
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestHookValidatorBase:
    """Unit tests for HookValidator base class."""

    @pytest.mark.skipif(HookValidator is None, reason="HookValidator not implemented yet")
    def test_run_exception_fails_open(self):
        """HookValidator.run() fails open on error."""

        # Create a validator that raises an exception
        class FailingValidator(HookValidator):
            def validate(self, hook_input):
                raise ValueError("Test error")

        validator = FailingValidator()

        # Mock stdin with valid JSON
        old_stdin = sys.stdin
        hook_data = {"session_id": "test", "hook_event_name": "PreToolUse"}
        sys.stdin = StringIO(json.dumps(hook_data))

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            exit_code = validator.run()

            # Should return 0 (success)
            assert exit_code == 0

            # Should output allow decision
            output = sys.stdout.getvalue()
            # Output should be JSON with allow decision
            # (or empty JSON which means allow)
            try:
                result_data = json.loads(output)
                # Either empty or has decision=allow
                assert result_data.get("decision") in (None, "allow")
            except json.JSONDecodeError:
                # Empty output is also fine (means allow)
                pass
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout


class TestSessionIdLogging:
    """Unit tests for session_id logging in hook events."""

    @pytest.mark.skipif(HookValidator is None, reason="HookValidator not implemented yet")
    def test_session_id_logged_in_hook_execution(self, mocker):
        """HookValidator logs session_id in hook_execution event."""
        # Mock the logger
        mock_logger = mocker.MagicMock()
        mocker.patch("scripts.automation.hooks.get_logger", return_value=mock_logger)

        # Create a simple validator
        class SimpleValidator(HookValidator):
            def validate(self, hook_input):
                return HookResult.allow()

        validator = SimpleValidator()

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

    @pytest.mark.skipif(HookValidator is None, reason="HookValidator not implemented yet")
    def test_session_id_logged_in_hook_result(self, mocker):
        """HookValidator logs session_id in hook_result event."""
        mock_logger = mocker.MagicMock()
        mocker.patch("scripts.automation.hooks.get_logger", return_value=mock_logger)

        class SimpleValidator(HookValidator):
            def validate(self, hook_input):
                return HookResult.deny("test reason")

        validator = SimpleValidator()

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

    @pytest.mark.skipif(HookValidator is None, reason="HookValidator not implemented yet")
    def test_session_id_logged_in_hook_error_with_hook_input(self, mocker):
        """HookValidator logs session_id in hook_error when hook_input available."""
        mock_logger = mocker.MagicMock()
        mocker.patch("scripts.automation.hooks.get_logger", return_value=mock_logger)

        class FailingValidator(HookValidator):
            def validate(self, hook_input):
                raise RuntimeError("Validation failed")

        validator = FailingValidator()

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

    @pytest.mark.skipif(HookValidator is None, reason="HookValidator not implemented yet")
    def test_session_id_not_in_hook_error_without_hook_input(self, mocker):
        """HookValidator omits session_id from hook_error when hook_input unavailable."""
        mock_logger = mocker.MagicMock()
        mocker.patch("scripts.automation.hooks.get_logger", return_value=mock_logger)

        class SimpleValidator(HookValidator):
            def validate(self, hook_input):
                return HookResult.allow()

        validator = SimpleValidator()

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

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_session_id_logged_in_moderator_input(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_input."""
        # Create temporary transcript with completion marker
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Create a transcript with user message and assistant response with WORK DONE
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Do the task"}]},
            }
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Task completed. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            # Mock the agent CLI to avoid actual agent execution
            mock_agent_cli = mocker.MagicMock()
            mock_agent_cli.run_print.return_value = ("ALLOW", None)
            mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

            # Mock the logger
            mock_logger = mocker.MagicMock()

            validator = ResponseScanner()
            validator.logger = mock_logger

            # Create hook input with session_id
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

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_session_id_logged_in_moderator_raw_output(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_raw_output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Do the task"}]},
            }
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Task completed. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            # Mock agent CLI
            mock_agent_cli = mocker.MagicMock()
            mock_agent_cli.run_print.return_value = ("ALLOW", None)
            mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

            mock_logger = mocker.MagicMock()

            validator = ResponseScanner()
            validator.logger = mock_logger

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
            assert kwargs["output"] == "ALLOW"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_session_id_logged_in_moderator_allow(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_allow."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Do the task"}]},
            }
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Completed. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            mock_agent_cli = mocker.MagicMock()
            mock_agent_cli.run_print.return_value = ("ALLOW", None)
            mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

            mock_logger = mocker.MagicMock()

            validator = ResponseScanner()
            validator.logger = mock_logger

            hook_input = type(
                "obj",
                (object,),
                {
                    "session_id": "moderator-test-789",
                    "transcript_path": temp_path,
                },
            )()

            result = validator.validate(hook_input)

            # Verify decision is allow
            assert result.decision is None or result.decision == "allow"

            # Verify completion_moderator_allow was logged with session_id
            allow_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "completion_moderator_allow"]
            assert len(allow_calls) == 1

            _, kwargs = allow_calls[0]
            assert kwargs["session_id"] == "moderator-test-789"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_session_id_logged_in_moderator_block(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_block."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Do the task"}]},
            }
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Still working. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            mock_agent_cli = mocker.MagicMock()
            mock_agent_cli.run_print.return_value = ("BLOCK: Work incomplete", None)
            mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

            mock_logger = mocker.MagicMock()

            validator = ResponseScanner()
            validator.logger = mock_logger

            hook_input = type(
                "obj",
                (object,),
                {
                    "session_id": "moderator-test-block",
                    "transcript_path": temp_path,
                },
            )()

            result = validator.validate(hook_input)

            # Verify decision is block
            assert result.decision == "block"

            # Verify completion_moderator_block was logged with session_id
            block_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "completion_moderator_block"]
            assert len(block_calls) == 1

            _, kwargs = block_calls[0]
            assert kwargs["session_id"] == "moderator-test-block"
            assert "Work incomplete" in kwargs["reason"]
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_session_id_logged_in_moderator_error(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Do the task"}]},
            }
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Done. WORK DONE"}]},
            }
            f.write(json.dumps(user_msg) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            # Mock agent CLI to raise an error
            mock_agent_cli = mocker.MagicMock()
            from scripts.automation.agent_cli import AgentError

            mock_agent_cli.run_print.side_effect = AgentError("Agent failed")
            mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

            mock_logger = mocker.MagicMock()

            validator = ResponseScanner()
            validator.logger = mock_logger

            hook_input = type(
                "obj",
                (object,),
                {
                    "session_id": "moderator-test-error",
                    "transcript_path": temp_path,
                },
            )()

            result = validator.validate(hook_input)

            # Verify decision is block (error causes block)
            assert result.decision == "block"

            # Verify completion_moderator_error was logged with session_id
            error_calls = [call for call in mock_logger.error.call_args_list if call[0][0] == "completion_moderator_error"]
            assert len(error_calls) == 1

            _, kwargs = error_calls[0]
            assert kwargs["session_id"] == "moderator-test-error"
            assert "Agent failed" in kwargs["error"]
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_session_id_logged_in_moderator_transcript_error(self, mocker):
        """ResponseScanner logs session_id in completion_moderator_transcript_error."""
        # Mock prepare_moderator_context to raise exception
        mocker.patch("scripts.automation.hooks.prepare_moderator_context", side_effect=RuntimeError("Transcript read failed"))

        mock_logger = mocker.MagicMock()

        validator = ResponseScanner()
        validator.logger = mock_logger

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
                assistant_msg = {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Done. WORK DONE"}]},
                }
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
