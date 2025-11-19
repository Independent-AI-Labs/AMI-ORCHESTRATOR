"""Unit tests for transcript message retrieval functions."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.agents.transcript import (
    format_messages_for_prompt,
    get_last_n_messages,
    get_messages_until_last_user,
    is_actual_user_message,
)

# Test constants
TWO_MESSAGES = 2
THREE_MESSAGES = 3
FIRST_MESSAGE_INDEX = 0
SECOND_MESSAGE_INDEX = 1


def create_test_transcript(messages):
    """Helper to create a temporary transcript file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for msg in messages:
            # Convert simplified message format to real Claude transcript format
            if "text" in msg and "type" in msg:
                # Convert {"type": "user", "text": "..."} to real format
                real_format = {
                    "type": msg["type"],
                    "message": {"role": msg["type"], "content": msg["text"] if msg["type"] == "user" else [{"type": "text", "text": msg["text"]}]},
                    "timestamp": msg.get("timestamp", "2025-01-01T00:00:00.000Z"),
                }
                f.write(json.dumps(real_format) + "\n")
            else:
                # If already in real format, write as-is
                f.write(json.dumps(msg) + "\n")
        return Path(f.name)


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


class TestGetMessagesUntilLastUser:
    """Tests for get_messages_until_last_user()."""

    def test_get_until_last_user_basic(self) -> None:
        """Test basic functionality with user messages."""
        messages = [
            {"type": "user", "text": "First user"},
            {"type": "assistant", "text": "First assistant"},
            {"type": "user", "text": "Second user"},
            {"type": "assistant", "text": "Second assistant"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_messages_until_last_user(transcript)
            # Should return messages up to and including the last user message
            assert len(result) == THREE_MESSAGES  # First user, first assistant, second user
            assert result[FIRST_MESSAGE_INDEX]["text"] == "First user"
            assert result[SECOND_MESSAGE_INDEX]["text"] == "First assistant"
            assert result[2]["text"] == "Second user"
        finally:
            transcript.unlink()

    def test_get_until_last_user_no_user_messages(self) -> None:
        """Test with no user messages (should return empty list)."""
        messages = [
            {"type": "assistant", "text": "First assistant"},
            {"type": "assistant", "text": "Second assistant"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_messages_until_last_user(transcript)
            assert result == []
        finally:
            transcript.unlink()

    def test_get_until_last_user_only_one_user(self) -> None:
        """Test with only one user message."""
        messages = [
            {"type": "user", "text": "Only user"},
            {"type": "assistant", "text": "Assistant reply"},
            {"type": "assistant", "text": "Another reply"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_messages_until_last_user(transcript)
            assert len(result) == 1
            assert result[0]["text"] == "Only user"
        finally:
            transcript.unlink()

    def test_get_until_last_user_multiple_users(self) -> None:
        """Test with multiple user messages."""
        messages = [
            {"type": "user", "text": "User 1"},
            {"type": "assistant", "text": "Reply 1"},
            {"type": "user", "text": "User 2"},
            {"type": "assistant", "text": "Reply 2"},
            {"type": "user", "text": "User 3"},
        ]
        transcript = create_test_transcript(messages)

        try:
            result = get_messages_until_last_user(transcript)
            # Should return up to and including the last user
            assert len(result) == 5  # All messages including last user
            assert result[FIRST_MESSAGE_INDEX]["text"] == "User 1"
            assert result[SECOND_MESSAGE_INDEX]["text"] == "Reply 1"
            assert result[2]["text"] == "User 2"
            assert result[3]["text"] == "Reply 2"
            assert result[4]["text"] == "User 3"
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
        """Test basic formatting functionality."""
        messages = [
            {"type": "user", "text": "Hello"},
            {"type": "assistant", "text": "Hi there"},
        ]

        result = format_messages_for_prompt(messages)
        # Check for the new exhibit format
        assert "EXHIBIT A: CONVERSATION TRANSCRIPT FOR VALIDATION" in result
        assert '<message role="user" timestamp="unknown time">' in result
        assert "Hello" in result
        assert '<message role="assistant" timestamp="unknown time">' in result
        assert "Hi there" in result
        assert "END OF EXHIBIT A" in result

    def test_format_empty_list(self) -> None:
        """Test formatting empty message list."""
        result = format_messages_for_prompt([])
        assert result == "No messages found."

    def test_format_multiline(self) -> None:
        """Test formatting multiline messages."""
        messages = [
            {"type": "user", "text": "Line 1\nLine 2"},
            {"type": "assistant", "text": "Reply 1\nReply 2"},
        ]

        result = format_messages_for_prompt(messages)
        assert "Line 1\nLine 2" in result
        assert "Reply 1\nReply 2" in result

    def test_format_special_characters(self) -> None:
        """Test formatting messages with special characters."""
        messages = [
            {"type": "user", "text": 'Hello & "special" chars <>'},
            {"type": "assistant", "text": 'Reply & "more" chars <>'},
        ]

        result = format_messages_for_prompt(messages)
        assert 'Hello & "special" chars <>' in result
        assert 'Reply & "more" chars <>' in result


class TestIsActualUserMessage:
    """Tests for is_actual_user_message()."""

    def test_is_actual_user_true(self) -> None:
        """Test returns True for actual user message."""
        msg = json.dumps({"type": "user", "message": {"role": "user", "content": "Regular user message"}, "timestamp": "2025-01-01T00:00:00.000Z"})
        assert is_actual_user_message(msg) is True

    def test_is_actual_user_false_type(self) -> None:
        """Test returns False for non-user message types."""
        msg = json.dumps(
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "Assistant message"}]},
                "timestamp": "2025-01-01T00:00:00.000Z",
            }
        )
        assert is_actual_user_message(msg) is False

        msg = json.dumps({"type": "system", "message": {"role": "system", "content": "System message"}, "timestamp": "2025-01-01T00:00:00.000Z"})
        assert is_actual_user_message(msg) is False

    def test_is_actual_user_false_content(self) -> None:
        """Test returns True for user messages even with system-like content (since type field is definitive)."""
        # Test with "WORK DONE" indicator - in real Claude transcripts, these appear in assistant messages,
        # so if a user message contains this, it's still from a user
        msg = json.dumps(
            {"type": "user", "message": {"role": "user", "content": "I've completed the task. WORK DONE"}, "timestamp": "2025-01-01T00:00:00.000Z"}
        )
        assert is_actual_user_message(msg) is True

        # Test with "FEEDBACK:" indicator
        msg = json.dumps(
            {"type": "user", "message": {"role": "user", "content": "FEEDBACK: The model is struggling with this"}, "timestamp": "2025-01-01T00:00:00.000Z"}
        )
        assert is_actual_user_message(msg) is True

        # Test with "ALLOW" indicator
        msg = json.dumps({"type": "user", "message": {"role": "user", "content": "ALLOW: Test result passed"}, "timestamp": "2025-01-01T00:00:00.000Z"})
        assert is_actual_user_message(msg) is True

        # Test with "BLOCK" indicator
        msg = json.dumps(
            {"type": "user", "message": {"role": "user", "content": "BLOCK: This would be a security issue"}, "timestamp": "2025-01-01T00:00:00.000Z"}
        )
        assert is_actual_user_message(msg) is True

        # Test with "WORK DONE" in larger context
        msg = json.dumps(
            {"type": "user", "message": {"role": "user", "content": "Some context followed by WORK DONE marker"}, "timestamp": "2025-01-01T00:00:00.000Z"}
        )
        assert is_actual_user_message(msg) is True

    def test_actual_user_with_indicators_in_text(self) -> None:
        """Test that user messages are still identified if they legitimately contain indicators."""
        # These should still be True if they're coming from the user, not the AI result
        msg = json.dumps(
            {"type": "user", "message": {"role": "user", "content": "Can you explain what WORK DONE means?"}, "timestamp": "2025-01-01T00:00:00.000Z"}
        )
        assert is_actual_user_message(msg) is True

        msg = json.dumps(
            {"type": "user", "message": {"role": "user", "content": "Why do some messages end with FEEDBACK?"}, "timestamp": "2025-01-01T00:00:00.000Z"}
        )
        assert is_actual_user_message(msg) is True
