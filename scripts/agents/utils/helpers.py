"""Helper functions for task execution and CLI providers."""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.agents.core.models import UnifiedExecutionAttempt, UnifiedExecutionResult


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


def display_task_metadata(attempts: list[Any], logger: Any) -> None:
    """Display aggregated metadata for a task.

    Args:
        attempts: List of task attempts with metadata
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
            "task_metadata",
            total_cost=round(total_cost, 4),
            total_duration_seconds=round(total_duration_ms / 1000, 2),
            total_api_seconds=round(total_api_ms / 1000, 2),
            total_turns=int(total_turns),
        )


def calculate_timeout(timeout: int | None, elapsed_time: float) -> float:
    """Calculate timeout for next read operation.

    Args:
        timeout: Overall timeout in seconds, or None for no limit
        elapsed_time: Time elapsed so far in seconds

    Returns:
        Timeout value in seconds for next operation
    """
    if timeout is None:
        return 1.0  # Default timeout to prevent infinite blocking

    remaining = timeout - elapsed_time
    if remaining <= 0:
        # Timeout occurred
        return 0.0

    # Use smaller of remaining time or default read timeout
    return min(remaining, 1.0)


def validate_path_and_return_code(path: str) -> int:
    """Validate path exists and return appropriate exit code.

    Args:
        path: Path string to validate

    Returns:
        Exit code (0=success, 1=failure)
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return 1
    return 0


def handle_task_feedback_result(
    task_file: Path,
    task_name: str,
    timestamp_str: str,
    completion_marker: dict[str, str],
    attempts: list[Any],
    attempt_num: int,
    worker_output: str,
    worker_metadata: dict[str, Any] | None,
    attempt_duration: float,
    start_time: float,
) -> UnifiedExecutionResult:
    """Handle worker feedback request.

    Args:
        task_file: Task file path
        task_name: Task name
        timestamp_str: Timestamp string for file naming
        completion_marker: Parsed completion marker
        attempts: List of attempts so far
        attempt_num: Current attempt number
        worker_output: Worker output text
        attempt_duration: Duration of this attempt
        start_time: Task start time

    Returns:
        UnifiedExecutionResult with feedback status
    """

    feedback_file = task_file.parent / f"feedback-{timestamp_str}-{task_name}.md"
    feedback_file.write_text(f"# Feedback Request: {task_name}\n\n{completion_marker['content']}\n")

    attempts.append(
        UnifiedExecutionAttempt(
            attempt_number=attempt_num,
            worker_output=worker_output,
            moderator_output=None,
            timestamp=datetime.now(),
            duration=attempt_duration,
            worker_metadata=worker_metadata,
            moderator_metadata=None,
        )
    )

    return UnifiedExecutionResult(
        item_path=task_file,
        status="feedback",
        attempts=attempts,
        feedback=completion_marker["content"],
        total_duration=time.time() - start_time,
    )
