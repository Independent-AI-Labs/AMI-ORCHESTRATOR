"""Common utilities for LLM orchestration executors."""

import re
from logging import Logger
from pathlib import Path
from typing import Any


def parse_completion_marker(output: str) -> dict[str, Any]:
    """Parse completion marker from worker output.

    Args:
        output: Worker output text

    Returns:
        Dict with type and content
    """
    # Check for "WORK DONE"
    if "WORK DONE" in output:
        return {"type": "work_done", "content": None}

    # Check for "FEEDBACK: xxx"
    feedback_match = re.search(r"FEEDBACK:\s*(.+)", output, re.DOTALL)
    if feedback_match:
        return {"type": "feedback", "content": feedback_match.group(1).strip()}

    # No marker found
    return {"type": "none", "content": None}


def parse_moderator_result(output: str) -> dict[str, Any]:
    """Parse moderator validation result.

    Args:
        output: Moderator output text

    Returns:
        Dict with status ('pass' or 'fail') and optional reason
    """
    # Check for "PASS"
    if "PASS" in output:
        return {"status": "pass", "reason": None}

    # Check for "FAIL: xxx"
    fail_match = re.search(r"FAIL:\s*(.+)", output, re.DOTALL)
    if fail_match:
        return {"status": "fail", "reason": fail_match.group(1).strip()}

    # Moderator didn't output PASS or FAIL - treat as validation failure
    return {"status": "fail", "reason": "Moderator validation unclear - no explicit PASS or FAIL in output"}


def detect_language(file_path: Path) -> str | None:
    """Detect language from file extension.

    Args:
        file_path: File path

    Returns:
        Language name or None if unknown
    """
    ext = file_path.suffix.lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".php": "php",
        ".rb": "ruby",
        ".html": "html",
        ".css": "css",
        ".md": "markdown",
    }
    return mapping.get(ext)


def display_execution_metadata(attempts: list[Any], logger: Logger) -> None:
    """Display aggregated metadata for an execution.

    Args:
        attempts: List of execution attempts with metadata
        logger: Logger instance to output metadata
    """
    total_cost = 0.0
    total_duration_ms = 0.0
    total_api_ms = 0.0
    total_turns = 0

    for attempt in attempts:
        # Worker metadata
        if attempt.worker_metadata:
            total_cost += attempt.worker_metadata.get("cost_usd", 0) or 0
            total_duration_ms += attempt.worker_metadata.get("duration_ms", 0) or 0
            total_api_ms += attempt.worker_metadata.get("duration_api_ms", 0) or 0
            total_turns += attempt.worker_metadata.get("num_turns", 0) or 0

        # Moderator metadata
        if attempt.moderator_metadata:
            total_cost += attempt.moderator_metadata.get("cost_usd", 0) or 0
            total_duration_ms += attempt.moderator_metadata.get("duration_ms", 0) or 0
            total_api_ms += attempt.moderator_metadata.get("duration_api_ms", 0) or 0
            total_turns += attempt.moderator_metadata.get("num_turns", 0) or 0

    # Only display if we have any metadata
    if total_cost > 0 or total_turns > 0:
        logger.info(
            "execution_metadata - Cost: $%.4f, Duration: %.2fs, API Time: %.2fs, Turns: %d",
            round(total_cost, 4),
            round(total_duration_ms / 1000, 2),
            round(total_api_ms / 1000, 2),
            int(total_turns),
        )
