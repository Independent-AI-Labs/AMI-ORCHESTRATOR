"""Unit tests for transcript manipulation utilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.agents.transcript import (
    is_actual_user_message,
)

# Test constants
TWO_MESSAGES = 2
THREE_MESSAGES = 3
FIRST_MESSAGE_INDEX = 0
SECOND_MESSAGE_INDEX = 1


def create_test_transcript(messages: list[dict[str, str]]) -> Path:
    """Create a temporary JSONL transcript file for testing using REAL Claude transcript format.

    Args:
        messages: List of message dicts with type and content

    Returns:
        Path to temporary transcript file
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
        for msg in messages:
            if msg["type"] == "user":
                # Real user messages have string content
                msg_data = {
                    "type": "user",
                    "message": {"role": "user", "content": msg["text"]},
                    "timestamp": msg.get("timestamp", "2025-01-01T00:00:00Z"),
                    "uuid": "test-uuid",
                    "sessionId": "test-session",
                }
            else:
                # Assistant messages have array content
                msg_data = {
                    "type": "assistant",
                    "message": {"role": "assistant", "content": [{"type": "text", "text": msg["text"]}]},
                    "timestamp": msg.get("timestamp", "2025-01-01T00:00:00Z"),
                    "uuid": "test-uuid",
                }
            tmp.write(json.dumps(msg_data) + "\n")
        tmp_path = tmp.name
    return Path(tmp_path)


class TestIsActualUserMessage:
    """Tests for is_actual_user_message helper."""

    def test_actual_user_message_with_string_content(self) -> None:
        """Actual user message with string content returns True (REAL Claude format)."""
        # Copied from real Claude Code transcript line 22
        line = json.dumps(
            {
                "type": "user",
                "message": {"role": "user", "content": "Read the repo source code carefully. We need a new README"},
                "timestamp": "2025-10-25T20:27:58.244Z",
                "thinkingMetadata": {"level": "high", "disabled": False, "triggers": []},
                "uuid": "805c6a10-7a58-42ef-b059-cbf19a8796dc",
                "sessionId": "04d9e8e0-bb02-457a-9007-068d5bf17e16",
            }
        )

        assert is_actual_user_message(line) is True

    def test_tool_result_with_array_content_returns_false(self) -> None:
        """Tool result messages with array content return False (REAL Claude format)."""
        # Copied from real Claude Code transcript line 29 (tool result)
        line = json.dumps(
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [{"tool_use_id": "toolu_01Esh57s6crchYjFfa1v48dg", "type": "tool_result", "content": "file content here"}],
                },
                "toolUseResult": {"type": "text", "file": {"filePath": "/home/ami/Projects/AMI-ORCHESTRATOR/README.md", "content": "..."}},
                "uuid": "283134ca-d315-411e-b266-bc1620388cc0",
                "timestamp": "2025-10-25T20:28:06.439Z",
            }
        )

        assert is_actual_user_message(line) is False

    def test_interruption_marker_returns_false(self) -> None:
        """Interruption marker messages return False."""
        line = json.dumps(
            {
                "type": "user",
                "message": {"role": "user", "content": "[Request interrupted by user]"},
            }
        )

        assert is_actual_user_message(line) is False

    def test_stop_hook_feedback_returns_false(self) -> None:
        """Stop hook feedback messages return False (REAL Claude format)."""
        # Copied from real Claude Code transcript line 6 (stop hook feedback)
        stop_feedback_content = (
            "Stop hook feedback:\n- COMPLETION MARKER REQUIRED.\n\n"
            "You must signal completion before stopping:\n"
            "- Add 'WORK DONE' when task is complete\n"
            "- Add 'FEEDBACK: <reason>' if blocked or need user input\n\n"
            "Never stop without explicitly signaling completion status."
        )
        line = json.dumps(
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": stop_feedback_content,
                },
                "uuid": "430e0dbf-0fcd-43b7-9bfb-dcffcff2a213",
                "timestamp": "2025-10-25T20:23:55.843Z",
                "sessionId": "04d9e8e0-bb02-457a-9007-068d5bf17e16",
            }
        )

        assert is_actual_user_message(line) is False

    def test_completion_moderator_prompt_returns_false(self) -> None:
        """Completion moderator prompt messages return False."""
        moderator_prompt = (
            "# COMPLETION VALIDATION - ONE-SHOT DECISION\n\n"
            "You are validating whether assistant work is complete and legitimate.\n\n"
            "## OUTPUT FORMAT (CRITICAL)\n\n"
            "Output EXACTLY one of:\n"
            "- `ALLOW` - work complete, claims verified, no invalid FEEDBACK\n"
        )
        line = json.dumps(
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": moderator_prompt,
                },
                "uuid": "test-uuid",
                "timestamp": "2025-10-25T21:00:00.000Z",
                "sessionId": "test-session",
            }
        )

        assert is_actual_user_message(line) is False

    def test_assistant_message_returns_false(self) -> None:
        """Assistant messages return False (REAL Claude format)."""
        # Copied from real Claude Code transcript line 5 (assistant message)
        line = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "I understand. I'm ready to help with your software engineering and cybersecurity tasks."}],
                },
                "uuid": "db36352e-7cb3-4fd3-bbd9-a7c022469ee7",
                "timestamp": "2025-10-25T20:23:55.721Z",
            }
        )

        assert is_actual_user_message(line) is False

    def test_empty_line_returns_false(self) -> None:
        """Empty lines return False."""
        assert is_actual_user_message("") is False
        assert is_actual_user_message("   ") is False

    def test_invalid_json_returns_false(self) -> None:
        """Invalid JSON returns False."""
        assert is_actual_user_message("not json{") is False
