"""Unit tests for transcript manipulation utilities."""

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
