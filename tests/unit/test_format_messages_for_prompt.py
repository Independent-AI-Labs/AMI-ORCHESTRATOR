"""Unit tests for transcript manipulation utilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.agents.transcript import (
    format_messages_for_prompt,
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


class TestFormatMessagesForPrompt:
    """Tests for format_messages_for_prompt()."""

    def test_format_basic(self) -> None:
        """Test basic formatting."""
        messages: list[dict[str, str | None]] = [
            {"type": "user", "text": "Hello", "timestamp": "2025-01-01T12:00:00Z"},
            {"type": "assistant", "text": "Hi there", "timestamp": "2025-01-01T12:00:01Z"},
        ]

        result = format_messages_for_prompt(messages)

        assert '<message role="user"' in result
        assert '<message role="assistant"' in result
        assert "Hello" in result
        assert "Hi there" in result
        assert "2025-01-01T12:00:00Z" in result

    def test_format_empty_list(self) -> None:
        """Test with empty message list."""
        result = format_messages_for_prompt([])
        assert result == "No messages found."

    def test_format_multiline_content(self) -> None:
        """Test formatting multiline message content."""
        messages: list[dict[str, str | None]] = [
            {"type": "user", "text": "Line 1\nLine 2\nLine 3", "timestamp": None},
        ]

        result = format_messages_for_prompt(messages)

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_format_preserves_order(self) -> None:
        """Test that message order is preserved."""
        messages: list[dict[str, str | None]] = [
            {"type": "user", "text": "First", "timestamp": "2025-01-01T12:00:00Z"},
            {"type": "assistant", "text": "Second", "timestamp": "2025-01-01T12:00:01Z"},
            {"type": "user", "text": "Third", "timestamp": "2025-01-01T12:00:02Z"},
        ]

        result = format_messages_for_prompt(messages)

        # Check order by finding indices
        first_idx = result.find("First")
        second_idx = result.find("Second")
        third_idx = result.find("Third")

        assert first_idx < second_idx < third_idx
