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
    def test_scan_completion_marker_allows(self):
        """ResponseScanner allows 'WORK DONE' marker."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            transcript_data = {
                "type": "assistant",
                "uuid": "test-123",
                "message": {"content": [{"type": "text", "text": "I've completed the task. WORK DONE"}]},
            }
            f.write(json.dumps(transcript_data) + "\n")
            temp_path = Path(f.name)

        try:
            validator = ResponseScanner()
            hook_input = type("obj", (object,), {"transcript_path": temp_path})()

            result = validator.validate(hook_input)
            assert result.decision is None or result.decision == "allow"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @pytest.mark.skipif(ResponseScanner is None, reason="ResponseScanner not implemented yet")
    def test_scan_feedback_marker_allows(self):
        """ResponseScanner allows 'FEEDBACK:' marker."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            transcript_data = {
                "type": "assistant",
                "uuid": "test-123",
                "message": {"content": [{"type": "text", "text": "I'm stuck. FEEDBACK: need help with X"}]},
            }
            f.write(json.dumps(transcript_data) + "\n")
            temp_path = Path(f.name)

        try:
            validator = ResponseScanner()
            hook_input = type("obj", (object,), {"transcript_path": temp_path})()

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
