"""Task execution utility functions extracted from tasks.py."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.common import parse_moderator_result
from scripts.agents.core.models import UnifiedExecutionAttempt, UnifiedExecutionResult


def handle_feedback_result(
    task_file: Path,
    task_name: str,
    timestamp_str: str,
    completion_marker: dict[str, str],
    attempts: list[UnifiedExecutionAttempt],
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


def validate_with_moderator(
    task_name: str,
    task_content: str,
    worker_output: str,
    progress_file: Path,
    root_dir: Path | None,
    attempt_num: int,
    session_id: str,
    prompts_dir: Path,
    cli: Any,
) -> tuple[dict[str, Any], str, dict[str, Any] | None]:
    """Run moderator validation on worker output.

    Args:
        task_name: Task name
        task_content: Original task content
        worker_output: Worker output to validate
        progress_file: Progress file to update
        root_dir: Working directory
        attempt_num: Current attempt number
        session_id: Session ID for context
        prompts_dir: Directory containing prompts
        cli: CLI instance

    Returns:
        Tuple of (moderator_result dict, moderator_output text, moderator_metadata dict or None)
    """

    moderator_start = time.time()

    logger.info("moderator_check_started", task=task_name, attempt=attempt_num)

    with progress_file.open("a") as f:
        f.write("### Moderator Validation\n\n")

    moderator_prompt = prompts_dir / "task_moderator.txt"
    validation_context = f"""ORIGINAL TASK:
{task_content}

WORKER OUTPUT:
{worker_output}

Validate if the task was completed correctly."""

    moderator_config = AgentConfigPresets.task_moderator(session_id)
    moderator_config.enable_streaming = True
    moderator_output, moderator_metadata = cli.run_print(
        instruction_file=moderator_prompt,
        stdin=validation_context,
        agent_config=moderator_config,
        cwd=root_dir,
    )

    moderator_result = parse_moderator_result(moderator_output)
    moderator_duration = time.time() - moderator_start
    logger.info(
        "moderator_check_completed",
        task=task_name,
        attempt=attempt_num,
        duration=round(moderator_duration, 1),
        final_status=moderator_result["status"],
    )

    with progress_file.open("a") as f:
        f.write(f"Moderator output:\n```\n{moderator_output}\n```\n\n")

    return moderator_result, moderator_output, moderator_metadata


def execute_worker_attempt(
    task_name: str,
    task_content: str,
    user_instruction: str | None,
    additional_context: str,
    root_dir: Path | None,
    progress_file: Path,
    attempt_num: int,
    session_id: str,
    prompts_dir: Path,
    cli: Any,
) -> tuple[str, dict[str, Any] | None]:
    """Execute single worker attempt.

    Args:
        task_name: Task name
        task_content: Task content
        user_instruction: Optional user instruction
        additional_context: Additional context from previous attempts
        root_dir: Root directory
        progress_file: Progress file to update
        attempt_num: Current attempt number
        session_id: Session ID
        prompts_dir: Directory containing prompts
        cli: CLI instance

    Returns:
        Tuple of (worker output text, execution metadata or None)
    """

    logger.info("worker_attempt", task=task_name, attempt=attempt_num)

    with progress_file.open("a") as f:
        f.write(f"## Attempt {attempt_num} ({datetime.now()})\n\n")

    # Build worker context (task content passed via stdin, just like moderator)
    worker_context = ""
    if user_instruction:
        worker_context = f"{user_instruction}\n\n"
    worker_context += task_content
    if additional_context:
        worker_context += f"\n\n{additional_context}"

    # Execute worker with prompt file (matches moderator pattern)

    worker_prompt = prompts_dir / "task_worker.txt"
    worker_config = AgentConfigPresets.task_worker(session_id)
    worker_config.enable_streaming = True
    worker_output, worker_metadata = cli.run_print(
        instruction_file=worker_prompt,
        stdin=worker_context,
        agent_config=worker_config,
        cwd=root_dir,
    )
    return worker_output, worker_metadata
