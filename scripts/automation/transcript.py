"""Transcript manipulation utilities for Claude Code conversations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _parse_content_list(content: list[Any]) -> str | None:
    """Parse content list extracting text, tool_use, and tool_result blocks.

    Args:
        content: List of content items from message

    Returns:
        Formatted string with all content, or None if empty
    """
    text_parts: list[str] = []
    for content_item in content:
        if isinstance(content_item, dict):
            item_type = content_item.get("type")

            # Text blocks
            if item_type == "text":
                text_value = content_item.get("text")
                if isinstance(text_value, str):
                    text_parts.append(text_value)

            # Tool uses
            elif item_type == "tool_use":
                tool_name = content_item.get("name", "unknown")
                tool_input = content_item.get("input", {})
                text_parts.append(f"[Tool: {tool_name}] {json.dumps(tool_input)}")

            # Tool results (in user messages)
            elif item_type == "tool_result":
                tool_content = content_item.get("content", "")
                if isinstance(tool_content, str):
                    text_parts.append(f"[Tool Result]\n{tool_content}")

    return "\n\n".join(text_parts) if text_parts else None


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

    # Extract content - can be string or list
    content = message_obj.get("content")

    # Handle string content (user messages in real transcripts)
    if isinstance(content, str):
        return {
            "type": msg_type,
            "text": content,
            "timestamp": msg_data.get("timestamp"),
        }

    # Handle list content (assistant messages, tool results)
    if isinstance(content, list):
        text = _parse_content_list(content)
        if text:
            return {
                "type": msg_type,
                "text": text,
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


def _is_actual_user_message(line: str) -> bool:
    """Check if JSONL line is actual user input (not tool result or interruption).

    Args:
        line: Single line from transcript JSONL file

    Returns:
        True if line represents actual human user input, False otherwise
    """
    if not line.strip():
        return False

    try:
        msg_data = json.loads(line)
    except json.JSONDecodeError:
        return False

    # Must be user type
    if msg_data.get("type") != "user":
        return False

    message_obj = msg_data.get("message", {})
    content = message_obj.get("content")

    # Handle string content (newer transcript format)
    if isinstance(content, str):
        # Filter out interruption markers and stop hook feedback
        return not content.startswith(("[Request interrupted", "Stop hook feedback:"))

    # Handle array content (older format and some user messages)
    if isinstance(content, list):
        # Tool results have tool_use_id - filter those out
        return all(not (isinstance(item, dict) and "tool_use_id" in item) for item in content)

    return False


def get_messages_from_last_user_forward(transcript_path: Path, num_user_messages: int = 3) -> list[dict[str, str | None]]:
    """Get messages from Nth-last actual user request through end.

    Finds actual human user input (not tool results or interruptions),
    goes back N user messages, returns from there through end of transcript.
    This ensures moderator receives full context including original request.

    Args:
        transcript_path: Path to Claude Code transcript file (JSONL format)
        num_user_messages: Number of actual user messages to go back (default 3)

    Returns:
        List of messages from Nth-last actual user request through end.
        Includes original request, all assistant work, and completion marker.
        Empty list if insufficient user messages found.

    Raises:
        FileNotFoundError: If transcript file doesn't exist
    """
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    lines = transcript_path.read_text(encoding="utf-8").splitlines()
    messages: list[dict[str, str | None]] = []
    actual_user_indices: list[int] = []

    for line in lines:
        msg = _parse_message_from_json(line)
        if msg:
            messages.append(msg)
            # Track only actual user messages (not tool results/interruptions)
            if _is_actual_user_message(line):
                actual_user_indices.append(len(messages) - 1)

    if not actual_user_indices:
        return []

    # Go back N actual user messages from end
    target_index = max(0, len(actual_user_indices) - num_user_messages)
    start_message_index = actual_user_indices[target_index]

    return messages[start_message_index:]


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
