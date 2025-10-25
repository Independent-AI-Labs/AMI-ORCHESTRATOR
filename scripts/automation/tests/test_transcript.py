"""Unit tests for transcript manipulation utilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ..transcript import (
    format_messages_for_prompt,
    get_last_n_messages,
    get_messages_until_last_user,
)


def create_test_transcript(messages: list[dict[str, str]]) -> Path:
    """Create a temporary JSONL transcript file for testing.

    Args:
        messages: List of message dicts with type and content

    Returns:
        Path to temporary transcript file
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
        for msg in messages:
            msg_data = {
                "type": msg["type"],
                "message": {"content": [{"type": "text", "text": msg["text"]}]},
                "timestamp": msg.get("timestamp", "2025-01-01T00:00:00Z"),
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
            result = get_last_n_messages(transcript, 2)
            assert len(result) == 2
            assert result[0]["type"] == "user"
            assert result[0]["text"] == "Third message"
            assert result[1]["type"] == "assistant"
            assert result[1]["text"] == "Fourth message"
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
            assert len(result) == 2
            assert result[0]["text"] == "Valid message"
            assert result[1]["text"] == "Second valid"
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
            assert len(result) == 3
            assert result[0]["type"] == "user"
            assert result[0]["text"] == "First user"
            assert result[1]["type"] == "assistant"
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
            assert len(result) == 2
            assert result[1]["text"] == "User 2"
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


class TestFormatMessagesForPrompt:
    """Tests for format_messages_for_prompt()."""

    def test_format_basic(self) -> None:
        """Test basic formatting."""
        messages: list[dict[str, str | None]] = [
            {"type": "user", "text": "Hello", "timestamp": "2025-01-01T12:00:00Z"},
            {"type": "assistant", "text": "Hi there", "timestamp": "2025-01-01T12:00:01Z"},
        ]

        result = format_messages_for_prompt(messages)

        assert "=== USER MESSAGE" in result
        assert "=== ASSISTANT MESSAGE" in result
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
