"""Common components extracted from audit.py, tasks.py, and docs.py.

These standardized components eliminate code duplication and provide
consistent interfaces across all executor types.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from scripts.agents.core.base_executor import BaseExecutor
from scripts.agents.core.models import UnifiedExecutionAttempt, UnifiedExecutionResult
from scripts.agents.core.utils import detect_language as core_detect_language
from scripts.agents.core.utils import parse_completion_marker as base_parse_completion_marker
from scripts.agents.core.utils import parse_moderator_result as base_parse_moderator_result

TResult = TypeVar("TResult", bound=UnifiedExecutionResult)


def execute_with_retry_loop(
    executor: Any,
    item_path: Path,
    execute_attempt_func: Any,
    parse_completion_func: Any,
    validate_with_moderator_func: Any = None,
    moderator_enabled: bool = True,
    timeout: int = 3600,
) -> UnifiedExecutionResult:
    """Execute with retry loop, timeout, and optional moderator validation.

    Args:
        executor: The executor instance
        item_path: Path to the item being processed
        execute_attempt_func: Function to execute a single attempt
        parse_completion_func: Function to parse completion marker from output
        validate_with_moderator_func: Function to validate with moderator (optional)
        moderator_enabled: Whether to use moderator validation
        timeout: Maximum execution time in seconds

    Returns:
        UnifiedExecutionResult with execution outcome
    """
    start_time = time.time()
    attempts = []
    attempt_num = 0
    additional_context = ""

    item_name = item_path.stem

    while time.time() - start_time < timeout:
        attempt_num += 1
        attempt_start = time.time()

        try:
            # Execute the attempt
            output, worker_metadata = execute_attempt_func(attempt_num, additional_context)
            attempt_duration = time.time() - attempt_start

            # Parse completion marker
            completion_marker = parse_completion_func(output)

            if completion_marker["type"] == "feedback":
                # Create attempt record
                attempts.append(executor._create_attempt(attempt_num, output, None, attempt_duration, worker_metadata, None))

                return UnifiedExecutionResult(
                    item_path=item_path,
                    status="feedback",
                    attempts=attempts,
                    feedback=completion_marker["content"],
                    total_duration=time.time() - start_time,
                )

            if completion_marker["type"] == "work_done":
                if not moderator_enabled:
                    # No moderator, accept worker's claim
                    attempts.append(executor._create_attempt(attempt_num, output, None, attempt_duration, worker_metadata, None))

                    return UnifiedExecutionResult(
                        item_path=item_path,
                        status="completed",
                        attempts=attempts,
                        total_duration=time.time() - start_time,
                    )

                # Validate with moderator
                moderator_start = time.time()
                executor.logger.info(
                    "moderator_check_started",
                    item=item_name,
                    attempt=attempt_num,
                )

                moderator_result, moderator_output, moderator_metadata = validate_with_moderator_func(item_name, output, attempt_num)

                moderator_duration = time.time() - moderator_start
                executor.logger.info(
                    "moderator_check_completed",
                    item=item_name,
                    attempt=attempt_num,
                    duration=round(moderator_duration, 1),
                    final_status=moderator_result["status"],
                )

                attempts.append(executor._create_attempt(attempt_num, output, moderator_output, attempt_duration, worker_metadata, moderator_metadata))

                if moderator_result["status"] == "pass":
                    return UnifiedExecutionResult(
                        item_path=item_path,
                        status="completed",
                        attempts=attempts,
                        total_duration=time.time() - start_time,
                    )

                # Moderator failed - retry with feedback
                failure_reason = moderator_result["reason"] if moderator_result["reason"] else "Validation failed"
                additional_context = f"PREVIOUS ATTEMPT FAILED VALIDATION:\n{failure_reason}\n\nPlease fix the issues and try again."
                continue

            # No completion marker - continue retry loop with error context
            attempts.append(executor._create_attempt(attempt_num, output, None, attempt_duration, worker_metadata, None))
            additional_context = (
                "PREVIOUS ATTEMPT DID NOT OUTPUT COMPLETION MARKER.\nYou MUST output either 'WORK DONE' or 'FEEDBACK: <questions>' at the end of your response."
            )
            continue

        except Exception as e:
            executor.logger.error(
                "execution_error",
                item=item_name,
                error=str(e),
            )

            return UnifiedExecutionResult(
                item_path=item_path,
                status="failed",
                attempts=attempts,
                total_duration=time.time() - start_time,
                error=str(e),
            )

    # Timeout reached
    return UnifiedExecutionResult(
        item_path=item_path,
        status="timeout",
        attempts=attempts,
        total_duration=time.time() - start_time,
        error=f"Execution timed out after {timeout}s",
    )


def parse_completion_marker(output: str) -> dict[str, Any]:
    """Parse completion marker from worker output. Common implementation.

    Args:
        output: Worker output text

    Returns:
        Dict with type and content
    """
    return base_parse_completion_marker(output)


def parse_moderator_result(output: str) -> dict[str, Any]:
    """Parse moderator validation result. Common implementation.

    Args:
        output: Moderator output text

    Returns:
        Dict with status ('pass' or 'fail') and optional reason
    """
    return base_parse_moderator_result(output)


def detect_language(file_path: Path) -> str | None:
    """Detect language from file extension.

    Args:
        file_path: File path

    Returns:
        Language name or None if unknown
    """
    return core_detect_language(file_path)


class GenericExecutor(BaseExecutor[TResult]):
    """Generic executor providing common functionality for all agent executors."""

    def __init__(self, result_class: type[TResult]):
        super().__init__(result_class)
        self.executor_type = self.get_executor_name()

    def get_include_patterns(self) -> list[str]:
        """Get the file inclusion patterns for this executor.

        Subclasses should override this method with their specific patterns.
        """
        raise NotImplementedError("Subclasses must implement get_include_patterns()")

    def _has_valid_extension(self, file_path: Path) -> bool:
        """Check if the file has a valid extension for this executor."""
        # Standard implementation using include patterns
        return any(file_path.match(pattern) for pattern in self.get_include_patterns())

    def execute_single_item(self, item_path: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> TResult:
        """Execute a single item - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement execute_single_item()")

    def _create_attempt(
        self,
        attempt_number: int,
        worker_output: str,
        moderator_output: str | None,
        duration: float,
        worker_metadata: dict[str, Any] | None,
        moderator_metadata: dict[str, Any] | None,
    ) -> UnifiedExecutionAttempt:
        """Create an attempt record."""
        return UnifiedExecutionAttempt(
            attempt_number=attempt_number,
            worker_output=worker_output,
            moderator_output=moderator_output,
            timestamp=datetime.now(),
            duration=duration,
            worker_metadata=worker_metadata,
            moderator_metadata=moderator_metadata,
        )
