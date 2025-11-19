"""Unit tests for transcript manipulation utilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.agents.transcript import (
    get_messages_until_last_user,
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


class TestGetMessagesUntilLastUser:
    """Tests for get_messages_until_last_user()."""

    def test_get_until_last_user_basic(self) -> None:
        """Test basic functionality."""
        messages = [
            {"type": "user", "text": "First user"},
            {"type": "assistant", "text": "Assistant reply 1"},
            {"type": "user", "text": "Second user"},
            {"type": "assistant", "text": "Assistant reply 2"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_messages_until_last_user(transcript)
            # Should include everything up to "Second user"
            assert len(result) == THREE_MESSAGES
            assert result[FIRST_MESSAGE_INDEX]["type"] == "user"
            assert result[FIRST_MESSAGE_INDEX]["text"] == "First user"
            assert result[SECOND_MESSAGE_INDEX]["type"] == "assistant"
            assert result[2]["type"] == "user"
            assert result[2]["text"] == "Second user"
        finally:
            transcript.unlink()

    def test_get_until_last_user_no_user_messages(self) -> None:
        """Test with no user messages in transcript."""
        messages = [
            {"type": "assistant", "text": "Only assistant messages"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_messages_until_last_user(transcript)
            assert result == []
        finally:
            transcript.unlink()

    def test_get_until_last_user_only_user_messages(self) -> None:
        """Test with only user messages."""
        messages = [
            {"type": "user", "text": "User 1"},
            {"type": "user", "text": "User 2"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_messages_until_last_user(transcript)
            assert len(result) == TWO_MESSAGES
            assert result[SECOND_MESSAGE_INDEX]["text"] == "User 2"
        finally:
            transcript.unlink()

    def test_get_until_last_user_assistant_after_last_user(self) -> None:
        """Test that assistant messages after last user are excluded."""
        messages = [
            {"type": "user", "text": "User message"},
            {"type": "assistant", "text": "Assistant 1"},
            {"type": "assistant", "text": "Assistant 2"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_messages_until_last_user(transcript)
            # Should only include up to user message
            assert len(result) == 1
            assert result[0]["type"] == "user"
        finally:
            transcript.unlink()

    def test_get_until_last_user_empty_transcript(self) -> None:
        """Test with empty transcript."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            tmp_path = tmp.name
        transcript = Path(tmp_path)

        try:
            result = get_messages_until_last_user(transcript)
            assert result == []
        finally:
            transcript.unlink()

    def test_get_until_last_user_invalid_file(self) -> None:
        """Test with non-existent file."""
        with pytest.raises(FileNotFoundError):
            get_messages_until_last_user(Path("/nonexistent/file.jsonl"))
