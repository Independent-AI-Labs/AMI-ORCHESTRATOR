"""Unit tests for transcript manipulation utilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.automation.transcript import (
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
