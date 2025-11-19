"""Helper functions extracted from base_provider.py for better modularity."""

import subprocess
import time
from typing import Any

from loguru import logger

from scripts.agents.cli.exceptions import AgentExecutionError


def calculate_streaming_timeout(timeout: int | None, elapsed_time: float) -> float:
    """Calculate timeout for next read operation in streaming mode.

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


def handle_process_completion(
    process: subprocess.Popen[str],
    cmd: list[str],
    started_at: float,
    session_id: str,
) -> tuple[str, dict[str, Any] | None]:
    """Handle process completion and return results.

    Args:
        process: Completed subprocess
        cmd: Original command
        started_at: Time when execution started
        session_id: Session identifier for logging

    Returns:
        Tuple of (output, metadata)
    """
    duration = time.time() - started_at

    # Get the final output - don't call communicate() if process already finished
    # For processes that are already done, just return their output
    if process.poll() is not None:
        # Process already finished, get any remaining output
        stdout, stderr = process.communicate()
    else:
        # Process still running, wait for it to complete
        stdout, stderr = process.communicate()

    if process.returncode != 0:
        raise AgentExecutionError(process.returncode, stdout, stderr, cmd)

    # Log completion
    logger.info(
        "agent_completed",
        session_id=session_id,
        duration=duration,
        exit_code=process.returncode,
    )

    # Return output and basic metadata
    metadata = {
        "session_id": session_id,
        "duration": duration,
        "exit_code": process.returncode,
    }
    return stdout, metadata
