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
