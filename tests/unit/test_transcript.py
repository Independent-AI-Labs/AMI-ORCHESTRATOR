"""Unit tests for transcript manipulation utilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.automation.transcript import (
    _is_actual_user_message,
    format_messages_for_prompt,
    get_last_n_messages,
    get_messages_from_last_user_forward,
    get_messages_until_last_user,
)


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
            from scripts.automation.transcript import get_last_n_messages

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
            from scripts.automation.transcript import get_last_n_messages

            messages_parsed = get_last_n_messages(temp_path, 1)
            assert len(messages_parsed) == 1
            text = messages_parsed[0]["text"]
            assert text is not None
            assert "[Tool Result]" in text
            assert "def foo():" in text
            assert "return 42" in text
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
    """Tests for _is_actual_user_message helper."""

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

        assert _is_actual_user_message(line) is True

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

        assert _is_actual_user_message(line) is False

    def test_interruption_marker_returns_false(self) -> None:
        """Interruption marker messages return False."""
        line = json.dumps(
            {
                "type": "user",
                "message": {"role": "user", "content": "[Request interrupted by user]"},
            }
        )

        assert _is_actual_user_message(line) is False

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

        assert _is_actual_user_message(line) is False

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

        assert _is_actual_user_message(line) is False

    def test_empty_line_returns_false(self) -> None:
        """Empty lines return False."""
        assert _is_actual_user_message("") is False
        assert _is_actual_user_message("   ") is False

    def test_invalid_json_returns_false(self) -> None:
        """Invalid JSON returns False."""
        assert _is_actual_user_message("not json{") is False


class TestGetMessagesFromLastUserForward:
    """Tests for get_messages_from_last_user_forward."""

    def test_includes_actual_user_request(self) -> None:
        """Function includes original user request, not just tool results."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Actual user request
            user_request = {
                "type": "user",
                "message": {"role": "user", "content": "Write a README file"},
                "timestamp": "2025-10-25T20:27:00.000Z",
            }
            f.write(json.dumps(user_request) + "\n")

            # Assistant response
            assistant_msg = {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "I'll create a README"}]},
                "timestamp": "2025-10-25T20:27:05.000Z",
            }
            f.write(json.dumps(assistant_msg) + "\n")

            # Tool result (should be filtered from user message tracking)
            tool_result = {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [{"tool_use_id": "toolu_123", "type": "tool_result", "content": "File written"}],
                },
                "toolUseResult": {"stdout": "File written"},
                "timestamp": "2025-10-25T20:27:10.000Z",
            }
            f.write(json.dumps(tool_result) + "\n")

            # Final completion
            completion_msg = {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "WORK DONE"}]},
                "timestamp": "2025-10-25T20:27:15.000Z",
            }
            f.write(json.dumps(completion_msg) + "\n")

            temp_path = Path(f.name)

        try:
            messages = get_messages_from_last_user_forward(temp_path)

            # Should start from actual user request
            assert len(messages) >= 2

            # First message should be actual user request
            assert messages[0]["type"] == "user"
            assert "README" in (messages[0]["text"] or "")

            # Last message should be completion
            assert messages[-1]["type"] == "assistant"
            assert "WORK DONE" in (messages[-1]["text"] or "")
        finally:
            temp_path.unlink()

    def test_skips_interruption_markers(self) -> None:
        """Function skips '[Request interrupted by user]' markers."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Actual user request
            user_request = {
                "type": "user",
                "message": {"role": "user", "content": "Fix the bug"},
                "timestamp": "2025-10-25T20:00:00.000Z",
            }
            f.write(json.dumps(user_request) + "\n")

            # Assistant starts work
            assistant_msg = {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "Looking at the code"}]},
                "timestamp": "2025-10-25T20:00:05.000Z",
            }
            f.write(json.dumps(assistant_msg) + "\n")

            # Interruption marker (should be filtered)
            interruption = {
                "type": "user",
                "message": {"role": "user", "content": "[Request interrupted by user]"},
                "timestamp": "2025-10-25T20:00:10.000Z",
            }
            f.write(json.dumps(interruption) + "\n")

            # Completion
            completion = {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "WORK DONE"}]},
                "timestamp": "2025-10-25T20:00:15.000Z",
            }
            f.write(json.dumps(completion) + "\n")

            temp_path = Path(f.name)

        try:
            messages = get_messages_from_last_user_forward(temp_path)

            # Should start from actual user request, not interruption
            assert messages[0]["type"] == "user"
            assert "Fix the bug" in (messages[0]["text"] or "")
            assert "[Request interrupted" not in (messages[0]["text"] or "")
        finally:
            temp_path.unlink()

    def test_goes_back_n_user_messages(self) -> None:
        """Function goes back N actual user messages."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Three actual user messages
            for i in range(3):
                user_msg = {
                    "type": "user",
                    "message": {"role": "user", "content": f"User message {i + 1}"},
                    "timestamp": f"2025-10-25T20:00:{i:02d}.000Z",
                }
                f.write(json.dumps(user_msg) + "\n")

                # Assistant response
                assistant_msg = {
                    "type": "assistant",
                    "message": {"role": "assistant", "content": [{"type": "text", "text": f"Response {i + 1}"}]},
                    "timestamp": f"2025-10-25T20:00:{i:02d}.500Z",
                }
                f.write(json.dumps(assistant_msg) + "\n")

            temp_path = Path(f.name)

        try:
            # Default: go back 3 user messages
            messages = get_messages_from_last_user_forward(temp_path, num_user_messages=3)
            assert "User message 1" in (messages[0]["text"] or "")

            # Go back only 1 user message
            messages = get_messages_from_last_user_forward(temp_path, num_user_messages=1)
            assert "User message 3" in (messages[0]["text"] or "")

            # Go back 2 user messages
            messages = get_messages_from_last_user_forward(temp_path, num_user_messages=2)
            assert "User message 2" in (messages[0]["text"] or "")
        finally:
            temp_path.unlink()

    def test_returns_empty_list_if_no_user_messages(self) -> None:
        """Function returns empty list if no actual user messages found."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Only assistant messages
            assistant_msg = {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "Hello"}]},
            }
            f.write(json.dumps(assistant_msg) + "\n")

            temp_path = Path(f.name)

        try:
            messages = get_messages_from_last_user_forward(temp_path)
            assert messages == []
        finally:
            temp_path.unlink()

    def test_skips_stop_hook_feedback(self) -> None:
        """Function skips 'Stop hook feedback:' messages."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Actual user request
            user_request = {
                "type": "user",
                "message": {"role": "user", "content": "Complete the task"},
                "timestamp": "2025-10-25T20:00:00.000Z",
            }
            f.write(json.dumps(user_request) + "\n")

            # Work
            assistant_msg = {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "Working on it"}]},
                "timestamp": "2025-10-25T20:00:05.000Z",
            }
            f.write(json.dumps(assistant_msg) + "\n")

            # Stop hook feedback (should be filtered)
            stop_feedback = {
                "type": "user",
                "message": {"role": "user", "content": "Stop hook feedback:\n- COMPLETION MARKER REQUIRED."},
                "timestamp": "2025-10-25T20:00:10.000Z",
            }
            f.write(json.dumps(stop_feedback) + "\n")

            # Completion
            completion = {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "WORK DONE"}]},
                "timestamp": "2025-10-25T20:00:15.000Z",
            }
            f.write(json.dumps(completion) + "\n")

            temp_path = Path(f.name)

        try:
            messages = get_messages_from_last_user_forward(temp_path)

            # Should start from actual user request, not stop hook feedback
            assert messages[0]["type"] == "user"
            assert "Complete the task" in (messages[0]["text"] or "")
            assert "Stop hook feedback" not in (messages[0]["text"] or "")
        finally:
            temp_path.unlink()
