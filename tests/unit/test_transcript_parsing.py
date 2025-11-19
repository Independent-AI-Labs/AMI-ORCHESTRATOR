"""Unit tests for transcript parsing and system reminder stripping."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.agents.transcript import (
    get_last_n_messages,
)

# Test constants
TWO_MESSAGES = 2
THREE_MESSAGES = 3


def create_test_transcript(messages):
    """Helper to create a temporary transcript file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")
        return Path(f.name)


class TestParseMessageIncludesTools:
    """Tests that _parse_message_from_json includes tool_use and tool_result blocks."""

    def test_parse_includes_tool_use_blocks(self) -> None:
        """Parser includes tool_use blocks in message text."""
        messages = [
            {"type": "user", "text": "Read the file"},
            {"type": "assistant", "text": "I'll read it"},
        ]
        transcript = create_test_transcript(messages)

        try:
            # Add a tool use manually to the transcript
            with transcript.open("a") as f:
                tool_use_msg = {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "Let me check the file"},
                            {"type": "tool_use", "id": "toolu_123", "name": "Read", "input": {"file_path": "/test/file.py"}},
                        ],
                    },
                    "timestamp": "2025-01-01T00:00:02Z",
                }
                f.write(json.dumps(tool_use_msg) + "\n")

            # Parse and verify tool use is included
            messages_parsed = get_last_n_messages(transcript, 1)
            assert len(messages_parsed) == 1
            text = messages_parsed[0]["text"]
            assert text is not None
            assert "Let me check the file" in text
            assert "[Tool: Read]" in text
            assert "/test/file.py" in text
        finally:
            transcript.unlink()

    def test_parse_includes_tool_result_blocks(self) -> None:
        """Parser includes tool_result blocks in message text."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Tool result message (real format)
            tool_result_msg = {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"tool_use_id": "toolu_123", "type": "tool_result", "content": "def foo():\n    return 42"},
                    ],
                },
                "timestamp": "2025-01-01T00:00:03Z",
            }
            f.write(json.dumps(tool_result_msg) + "\n")
            temp_path = Path(f.name)

        try:
            messages_parsed = get_last_n_messages(temp_path, 1)
            assert len(messages_parsed) == 1
            text = messages_parsed[0]["text"]
            assert text is not None
            assert "[Tool Result]" in text
            assert "def foo():" in text
            assert "return 42" in text
        finally:
            temp_path.unlink()


class TestSystemReminderStripping:
    """Tests that system-reminder tags are stripped from transcript content."""

    def test_strips_system_reminders_from_string_content(self) -> None:
        """System-reminder tags are removed from user message string content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            user_msg = {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": "Fix the bug<system-reminder>This is a reminder about something</system-reminder> please",
                },
                "timestamp": "2025-01-01T00:00:00Z",
                "uuid": "test-uuid",
                "sessionId": "test-session",
            }
            f.write(json.dumps(user_msg) + "\n")
            temp_path = Path(f.name)

        try:
            messages = get_last_n_messages(temp_path, 1)
            assert len(messages) == 1
            text = messages[0]["text"]
            assert text is not None
            assert "Fix the bug please" in text.strip()
            assert "system-reminder" not in text
            assert "This is a reminder" not in text
        finally:
            temp_path.unlink()

    def test_strips_system_reminders_from_text_blocks(self) -> None:
        """System-reminder tags are removed from assistant text blocks."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            assistant_msg = {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Let me help<system-reminder>Use the tool properly</system-reminder> with that"},
                    ],
                },
                "timestamp": "2025-01-01T00:00:01Z",
            }
            f.write(json.dumps(assistant_msg) + "\n")
            temp_path = Path(f.name)

        try:
            messages = get_last_n_messages(temp_path, 1)
            assert len(messages) == 1
            text = messages[0]["text"]
            assert text is not None
            assert "Let me help with that" in text.strip()
            assert "system-reminder" not in text
            assert "Use the tool properly" not in text
        finally:
            temp_path.unlink()
