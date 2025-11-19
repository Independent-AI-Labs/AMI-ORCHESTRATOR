"""Moderator execution with retry logic for handling hangs during startup or analysis."""

import contextlib
import re
import time
from pathlib import Path
from typing import Any

from loguru import logger

from scripts.agents.cli.exceptions import AgentExecutionError, AgentTimeoutError
from scripts.agents.validation.validation_utils import parse_code_fence_output


def _check_first_output_in_audit_log(audit_log_path: Path) -> bool:
    """Check if audit log contains first output marker.

    Args:
        audit_log_path: Path to audit log file

    Returns:
        True if first output marker found, False otherwise
    """
    if not audit_log_path or not audit_log_path.exists():
        return False

    try:
        content = audit_log_path.read_text()
        # Check for first output marker from agent CLI
        return "=== FIRST OUTPUT:" in content
    except Exception:
        return False


def _check_decision_in_output(output: str) -> bool:
    """Check if output contains a decision (ALLOW or BLOCK).

    Args:
        output: Moderator output string

    Returns:
        True if decision found, False otherwise
    """
    if not output:
        return False

    # Check for decision markers
    # Pattern matches: ALLOW or BLOCK or BLOCK: (with optional colon and reason)

    cleaned = parse_code_fence_output(output)
    return bool(re.search(r"\b(ALLOW|BLOCK)\b", cleaned, re.IGNORECASE))


def run_moderator_with_retry(
    cli: Any,
    instruction_file: Path,
    stdin: str,
    agent_config: Any,
    audit_log_path: Path | None,
    moderator_name: str,
    session_id: str,
    execution_id: str,
    max_attempts: int = 2,
    first_output_timeout: float = 3.5,
) -> tuple[str, dict[str, Any] | None]:
    """Run moderator with automatic restart if hangs during startup or analysis.

    Monitors for TWO types of hangs:
    1. **Startup hang**: No first output within first_output_timeout (default 3.5s)
       - Claude never starts streaming
       - Process appears stuck before any output

    2. **Analysis hang**: First output produced but no <decision> tag
       - Claude starts streaming (system init message)
       - But hangs during thinking/analysis phase
       - Never produces final decision output

    If either hang detected, automatically restarts (up to max_attempts total).

    Args:
        cli: Agent CLI instance
        instruction_file: Path to moderator prompt file
        stdin: Input context for moderator
        agent_config: Agent configuration
        audit_log_path: Audit log path (required for hang monitoring)
        moderator_name: Name of moderator for logging
        session_id: Session ID
        execution_id: Execution ID
        max_attempts: Maximum attempts (default 2: original + 1 restart)
        first_output_timeout: Seconds to wait for first output (default 3.5s)

    Returns:
        Tuple of (output, metadata)

    Raises:
        AgentTimeoutError: All attempts hung without first output
        AgentError: Other execution errors
    """
    if not audit_log_path:
        # No audit log - cannot monitor for first output, run directly
        result: tuple[str, dict[str, Any] | None] = cli.run_print(
            instruction_file=instruction_file,
            stdin=stdin,
            agent_config=agent_config,
            audit_log_path=audit_log_path,
        )
        return result

    # Use shorter timeout to detect hangs quickly
    original_timeout = agent_config.timeout
    hang_detection_timeout = max(int(first_output_timeout * 2), 15)  # At least 2x first_output_timeout, minimum 15s

    for attempt in range(1, max_attempts + 1):
        attempt_execution_id = f"{execution_id}-attempt{attempt}"

        # Clear audit log for this attempt
        if audit_log_path.exists():
            audit_log_path.unlink()

        logger.info(
            f"{moderator_name}_attempt_starting",
            session_id=session_id,
            execution_id=attempt_execution_id,
            attempt=attempt,
            max_attempts=max_attempts,
            timeout=hang_detection_timeout,
        )

        # Set shorter timeout for hang detection
        agent_config.timeout = hang_detection_timeout

        try:
            start_time = time.time()

            # Start moderator execution
            output, metadata = cli.run_print(
                instruction_file=instruction_file,
                stdin=stdin,
                agent_config=agent_config,
                audit_log_path=audit_log_path,
            )

            # Success - verify first output was produced and decision was made
            has_first_output = _check_first_output_in_audit_log(audit_log_path)
            has_decision = _check_decision_in_output(output)
            elapsed = time.time() - start_time

            if has_first_output and has_decision:
                # Complete success
                logger.info(
                    f"{moderator_name}_attempt_success",
                    session_id=session_id,
                    execution_id=attempt_execution_id,
                    attempt=attempt,
                    elapsed=round(elapsed, 2),
                )
                agent_config.timeout = original_timeout
                return output, metadata

            if has_first_output and not has_decision:
                # Analysis hang: first output present but no decision
                if attempt < max_attempts:
                    # Kill hung process before retry
                    with contextlib.suppress(Exception):
                        cli.kill_current_process()

                    logger.warning(
                        f"{moderator_name}_analysis_hang_restarting",
                        session_id=session_id,
                        execution_id=attempt_execution_id,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        reason="First output present but no decision - moderator hung during analysis",
                        output_preview=output[:500] if output else "",
                        elapsed=elapsed,
                    )
                    continue  # Retry

                # Last attempt - return output even without decision (parsing will fail-closed)
                logger.error(
                    f"{moderator_name}_analysis_hang_exhausted",
                    session_id=session_id,
                    execution_id=attempt_execution_id,
                    attempt=attempt,
                )
                agent_config.timeout = original_timeout
                return output, metadata

            # No first output but completed (shouldn't happen)
            logger.warning(
                f"{moderator_name}_no_first_output_but_completed",
                session_id=session_id,
                execution_id=attempt_execution_id,
                attempt=attempt,
            )
            agent_config.timeout = original_timeout
            return output, metadata

        except (AgentTimeoutError, AgentExecutionError) as e:
            # On timeout, always retry
            if attempt < max_attempts:
                # Kill hung process before retry
                with contextlib.suppress(Exception):
                    cli.kill_current_process()

                # Check if first output was produced for logging
                has_first_output = _check_first_output_in_audit_log(audit_log_path)
                hang_type = "startup hang" if not has_first_output else "analysis hang"

                logger.warning(
                    f"{moderator_name}_timeout_restarting",
                    session_id=session_id,
                    execution_id=attempt_execution_id,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error_type=type(e).__name__,
                    hang_type=hang_type,
                    has_first_output=has_first_output,
                    elapsed=time.time() - start_time,
                )

                # Restore timeout before retry
                agent_config.timeout = original_timeout
                continue  # Retry

            # Last attempt - re-raise
            agent_config.timeout = original_timeout
            raise

        except Exception:
            # Other errors - re-raise immediately
            agent_config.timeout = original_timeout
            raise

    # All attempts exhausted without success
    raise AgentTimeoutError(
        timeout=int(hang_detection_timeout * max_attempts),
        cmd=["claude", "--print"],
        duration=float(hang_detection_timeout * max_attempts),
    )
