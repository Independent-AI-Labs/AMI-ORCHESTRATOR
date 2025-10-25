"""Transcript manipulation utilities for Claude Code conversations."""

from __future__ import annotations

import json
import re
from pathlib import Path


def _parse_message_from_json(line: str) -> dict[str, str | None] | None:
    """Parse a single message from JSONL line.

    Args:
        line: Single line from transcript file

    Returns:
        Message dict with type/text/timestamp, or None if invalid
    """
    # Early validation checks
    if not line.strip():
        return None

    try:
        msg_data = json.loads(line)
    except json.JSONDecodeError:
        return None

    # Validate message structure
    msg_type = msg_data.get("type")
    message_obj = msg_data.get("message")
    if msg_type not in ("user", "assistant") or not isinstance(message_obj, dict):
        return None

    # Extract content list
    content_list = message_obj.get("content")
    if not isinstance(content_list, list):
        return None

    # Collect text parts from content items
    text_parts: list[str] = []
    for content in content_list:
        if isinstance(content, dict) and content.get("type") == "text":
            text_value = content.get("text")
            if isinstance(text_value, str):
                text_parts.append(text_value)

    # Return formatted message if we found text
    if text_parts:
        return {
            "type": msg_type,
            "text": "\n".join(text_parts),
            "timestamp": msg_data.get("timestamp"),
        }

    return None


def get_last_n_messages(transcript_path: Path, n: int) -> list[dict[str, str | None]]:
    """Get last N messages from transcript.

    Args:
        transcript_path: Path to Claude Code transcript file (JSONL format)
        n: Number of messages to retrieve

    Returns:
        List of message dictionaries with:
        - type: "user" | "assistant"
        - text: message content
        - timestamp: ISO timestamp (if available)

    Raises:
        FileNotFoundError: If transcript file doesn't exist
        ValueError: If n < 1
    """
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")

    messages: list[dict[str, str | None]] = []
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        msg = _parse_message_from_json(line)
        if msg:
            messages.append(msg)

    return messages[-n:] if messages else []


def get_messages_until_last_user(transcript_path: Path) -> list[dict[str, str | None]]:
    """Get all messages up to and including the last user message.

    Args:
        transcript_path: Path to Claude Code transcript file (JSONL format)

    Returns:
        List of messages from start of conversation through last user message.
        Empty list if no user messages found.

    Raises:
        FileNotFoundError: If transcript file doesn't exist
    """
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    messages: list[dict[str, str | None]] = []
    last_user_index = -1

    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        msg = _parse_message_from_json(line)
        if msg:
            messages.append(msg)
            if msg["type"] == "user":
                last_user_index = len(messages) - 1

    if last_user_index == -1:
        return []

    return messages[: last_user_index + 1]


def get_messages_from_last_user_forward(transcript_path: Path) -> list[dict[str, str | None]]:
    """Get messages from most recent task request through end.

    Scans in reverse from end, skips "[Request interrupted by user]" AND
    "Stop hook feedback:" messages to find actual task request, returns from there.

    Args:
        transcript_path: Path to Claude Code transcript file (JSONL format)

    Returns:
        List of messages from most recent task request through end.
        Includes task request, all assistant work, and completion marker.
        Skips stop hook feedback loops to get actual task context.
        Empty list if no user messages found.

    Raises:
        FileNotFoundError: If transcript file doesn't exist
    """
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    messages: list[dict[str, str | None]] = []
    user_indices: list[int] = []

    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        msg = _parse_message_from_json(line)
        if msg:
            messages.append(msg)
            if msg["type"] == "user":
                user_indices.append(len(messages) - 1)

    if not user_indices:
        return []

    # Scan in reverse, skip interruptions and stop hook feedback, find real task
    interruption_pattern = re.compile(r"^\[Request interrupted by user")
    stop_hook_pattern = re.compile(r"^Stop hook feedback:")

    for i in range(len(user_indices) - 1, -1, -1):
        user_index = user_indices[i]
        message_text = messages[user_index].get("text") or ""

        # Skip interruptions and stop hook feedback - find actual task request
        if not interruption_pattern.match(message_text) and not stop_hook_pattern.match(message_text):
            return messages[user_index:]

    # All user messages are interruptions/stop hooks - return from first one
    return messages[user_indices[0] :]


def format_messages_for_prompt(messages: list[dict[str, str | None]]) -> str:
    """Format messages as readable text for LLM analysis.

    Args:
        messages: List of message dictionaries from get_last_n_messages()
                 or get_messages_until_last_user()

    Returns:
        Formatted string with message history suitable for LLM prompt
    """
    if not messages:
        return "No messages found."

    lines: list[str] = []
    for msg in messages:
        msg_type = msg.get("type", "unknown")
        text = msg.get("text") or ""
        timestamp = msg.get("timestamp", "unknown time")

        lines.append(f'<message role="{msg_type}" timestamp="{timestamp}">')
        lines.append(text)
        lines.append("</message>")
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "get_last_n_messages",
    "get_messages_until_last_user",
    "get_messages_from_last_user_forward",
    "format_messages_for_prompt",
]
