"""Unit tests for transcript manipulation utilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

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


class TestGetLastNMessages:
    """Tests for get_last_n_messages()."""

    def test_get_last_n_basic(self) -> None:
        """Test basic functionality with valid messages."""
        messages = [
            {"type": "user", "text": "First message"},
            {"type": "assistant", "text": "Second message"},
            {"type": "user", "text": "Third message"},
            {"type": "assistant", "text": "Fourth message"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_last_n_messages(transcript, TWO_MESSAGES)
            assert len(result) == TWO_MESSAGES
            assert result[FIRST_MESSAGE_INDEX]["type"] == "user"
            assert result[FIRST_MESSAGE_INDEX]["text"] == "Third message"
            assert result[SECOND_MESSAGE_INDEX]["type"] == "assistant"
            assert result[SECOND_MESSAGE_INDEX]["text"] == "Fourth message"
        finally:
            transcript.unlink()

    def test_get_last_n_exceeds_available(self) -> None:
        """Test requesting more messages than available."""
        messages = [
            {"type": "user", "text": "Only message"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_last_n_messages(transcript, 10)
            assert len(result) == 1
            assert result[0]["text"] == "Only message"
        finally:
            transcript.unlink()

    def test_get_last_n_empty_transcript(self) -> None:
        """Test with empty transcript file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            tmp_path = tmp.name
        transcript = Path(tmp_path)

        try:
            result = get_last_n_messages(transcript, 5)
            assert result == []
        finally:
            transcript.unlink()

    def test_get_last_n_invalid_file(self) -> None:
        """Test with non-existent file."""
        with pytest.raises(FileNotFoundError):
            get_last_n_messages(Path("/nonexistent/file.jsonl"), 5)

    def test_get_last_n_invalid_n(self) -> None:
        """Test with invalid n value."""
        messages = [{"type": "user", "text": "Test"}]
        transcript = create_test_transcript(messages)

        try:
            with pytest.raises(ValueError, match="n must be >= 1"):
                get_last_n_messages(transcript, 0)
        finally:
            transcript.unlink()

    def test_get_last_n_malformed_json(self) -> None:
        """Test with malformed JSON lines (should skip them)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            # Valid message
            msg1 = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Valid message"}]},
            }
            tmp.write(json.dumps(msg1) + "\n")
            # Malformed JSON
            tmp.write("{ invalid json }\n")
            # Another valid message
            msg2 = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Second valid"}]},
            }
            tmp.write(json.dumps(msg2) + "\n")
            tmp_path = tmp.name
        transcript = Path(tmp_path)

        try:
            result = get_last_n_messages(transcript, 10)
            # Should only get 2 valid messages, skipping malformed line
            assert len(result) == TWO_MESSAGES
            assert result[FIRST_MESSAGE_INDEX]["text"] == "Valid message"
            assert result[SECOND_MESSAGE_INDEX]["text"] == "Second valid"
        finally:
            transcript.unlink()

    def test_get_last_n_multiline_content(self) -> None:
        """Test with multiline message content."""
        messages = [
            {"type": "user", "text": "Line 1\nLine 2\nLine 3"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_last_n_messages(transcript, 1)
            assert len(result) == 1
            text = result[0]["text"]
            assert text is not None
            assert "Line 1\nLine 2\nLine 3" in text
        finally:
            transcript.unlink()
