"""Unit tests for HookInput functionality."""

import json
import sys
from io import StringIO

import pytest

# Import the implemented hooks functionality
from scripts.agents.workflows.core import HookInput


class TestHookInput:
    """Unit tests for HookInput."""

    def test_from_stdin_valid_json(self, tmp_path):
        """HookInput.from_stdin() parses valid JSON."""
        hook_data = {
            "session_id": "test-123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "transcript_path": str(tmp_path / "transcript.jsonl"),
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

    def test_from_stdin_invalid_json(self):
        """HookInput raises error on invalid JSON."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("not valid json{")

        try:
            with pytest.raises(json.JSONDecodeError):
                HookInput.from_stdin()
        finally:
            sys.stdin = old_stdin
