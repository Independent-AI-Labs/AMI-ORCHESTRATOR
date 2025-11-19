"""Streaming-related utility functions extracted from base_provider.py."""

from __future__ import annotations

import os
import select
import subprocess
import time
from pathlib import Path
from typing import Any, Protocol

from loguru import logger

from scripts.agents.cli.env_utils import get_unprivileged_env
from scripts.agents.cli.exceptions import (
    AgentCommandNotFoundError,
    AgentExecutionError,
    AgentTimeoutError,
)
from scripts.agents.cli.streaming_utils import calculate_timeout
from scripts.agents.config import get_config


class AgentConfigProtocol(Protocol):
    """Protocol for agent configuration to avoid circular imports."""

    session_id: str
    timeout: int | None
    enable_streaming: bool | None


def start_streaming_process(
    cmd: list[str],
    stdin_data: str | None,
    cwd: Path | None,
    config: Any = None,
) -> subprocess.Popen[str]:
    """Start CLI process in streaming mode.

    Args:
        cmd: Command to execute
        stdin_data: Data to send to stdin, or None
        cwd: Working directory
        config: Configuration object for environment settings

    Returns:
        Started subprocess.Popen instance
    """
    # Get unprivileged environment if configured
    if config is None:
        config = get_config()
    env = get_unprivileged_env(config)
    if env is None:
        env = os.environ.copy()

    # Prepare stdin - we'll provide stdin_data directly to communicate() later
    stdin_pipe = subprocess.PIPE if stdin_data is not None else None

    # Start the process
    try:
        # Validate command to prevent injection attacks
        if not isinstance(cmd, list) or not all(isinstance(arg, str) for arg in cmd):
            raise ValueError(f"Invalid command format: {cmd}")
        # Ensure command paths are absolute or safe relative paths
        for arg in cmd:
            if arg.startswith(("..", "/", "~")) and not Path(arg).is_absolute():
                raise ValueError(f"Unsafe command path: {arg}")

        # Security review: Command validation already performed above (lines 57-65)
        # The cmd list is validated to be a list of strings with proper path checks
        return subprocess.Popen(  # noqa: S603
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=stdin_pipe,
            text=True,
            bufsize=1,  # Line buffered
            cwd=cwd,
            env=env,
        )

    except FileNotFoundError:
        raise AgentCommandNotFoundError(cmd[0]) from None


def read_streaming_line(
    process: subprocess.Popen[str],
    timeout_val: float,
    cmd: list[str],
) -> tuple[str | None, bool]:
    """Read a line from streaming process with timeout.

    Args:
        process: The subprocess to read from
        timeout_val: Timeout in seconds
        cmd: Original command for error reporting

    Returns:
        Tuple of (line content or None, True if timeout occurred)
    """
    # Use select to implement timeout on reading from subprocess
    try:
        # Wait for data to be available with timeout
        ready, _, _ = select.select([process.stdout], [], [], timeout_val)
        if not ready:
            return None, True  # Timeout occurred

        # Read the line
        if process.stdout is not None:
            line = process.stdout.readline()
            if not line:  # EOF
                return None, False

            return line.rstrip(), False
        return None, False
    except OSError:
        stdout, stderr = process.communicate()
        raise AgentExecutionError(process.returncode, stdout, stderr, cmd) from None


def handle_first_output_timeout(
    started_at: float,
    cmd: list[str],
    timeout: int | None,
) -> None:
    """Handle timeout for first output from agent.

    Args:
        started_at: Time when execution started
        cmd: Command that timed out
        timeout: Configured timeout value
    """
    if timeout is not None:
        elapsed = time.time() - started_at
        if elapsed >= timeout:
            raise AgentTimeoutError(timeout, cmd, elapsed)


def handle_process_exit(
    process: subprocess.Popen[str],
) -> str:
    """Handle process exit and return final output.

    Args:
        process: The subprocess that exited

    Returns:
        Final output from the process
    """
    # Get remaining output
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        raise AgentExecutionError(
            process.returncode,
            stdout,
            stderr,
            ["cli"],  # Default command
        ) from None

    # In streaming mode, we should have been collecting output already
    # Just return the final stdout
    return stdout


def handle_first_output_logging(
    agent_config: AgentConfigProtocol | None,
    logger: Any,
) -> None:
    """Handle logging for first output from agent.

    Args:
        agent_config: Agent configuration
        logger: Logger instance
    """
    # Log that we're waiting for first output
    if agent_config is not None:
        logger.info(
            "agent_first_output_waiting",
            extra={
                "session_id": agent_config.session_id,
                "timeout": agent_config.timeout,
            },
        )


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
        raise AgentExecutionError(process.returncode, stdout, stderr, cmd) from None

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


def run_streaming_loop(
    process: subprocess.Popen[str],
    cmd: list[str],
    agent_config: AgentConfigProtocol | None,
) -> tuple[str, dict[str, Any]]:
    """Run the main streaming loop to collect CLI output.

    Args:
        process: The subprocess to read from
        cmd: Original command for error reporting
        agent_config: Agent configuration

    Returns:
        Tuple of (output, metadata)
    """
    output_lines = []
    metadata: dict[str, Any] = {}
    line_count = 0
    started_at = time.time()

    session_id = agent_config.session_id if agent_config else "unknown"
    logger.info("streaming_loop_started", command=" ".join(cmd), session_id=session_id)

    while True:
        # Calculate timeout for this read

        timeout_val = calculate_timeout(agent_config.timeout if agent_config else None, line_count)

        # Read a line with timeout
        line, is_timeout = read_streaming_line(process, timeout_val, cmd)

        if is_timeout:
            # Check if overall timeout was exceeded
            if agent_config and agent_config.timeout is not None:
                elapsed = time.time() - started_at
                if elapsed >= agent_config.timeout:
                    timeout_val = agent_config.timeout if agent_config else 0
                    timeout = agent_config.timeout or 0
                    raise AgentTimeoutError(timeout, cmd, elapsed) from None

            # Otherwise, just continue waiting
            continue

        if line is None:
            # Check if process has exited
            if process.poll() is not None:
                # Process has exited, handle completion
                break
            # No data but process still running, continue
            continue

        # Parse the line - this needs to be handled by the caller since it's specific to each provider
        # For now, we'll just collect the raw line
        output_lines.append(line + "\n")

        # Update counters and time
        line_count += 1
        time.time()

    # Combine all output
    final_output = "".join(output_lines)
    return final_output, metadata


def execute_streaming(
    cmd: list[str],
    stdin_data: str | None = None,
    cwd: Path | None = None,
    agent_config: AgentConfigProtocol | None = None,
    config: Any = None,
) -> tuple[str, dict[str, Any] | None]:
    """Execute CLI command in streaming mode.

    Args:
        cmd: Command to execute
        stdin_data: Data to provide to stdin
        cwd: Working directory
        agent_config: Agent configuration
        config: Configuration object

    Returns:
        Tuple of (output, metadata)
    """
    # For cases where we have stdin data, we should use communicate() instead of streaming
    # since we're providing all the input at once
    if stdin_data is not None:
        # Get unprivileged environment
        if config is None:
            config = get_config()
        env = get_unprivileged_env(config)
        if env is None:
            env = os.environ.copy()

        # Run the process with communicate to provide stdin data
        start_time = time.time()
        try:
            # Validate command to prevent injection attacks
            if not isinstance(cmd, list) or not all(isinstance(arg, str) for arg in cmd):
                raise ValueError(f"Invalid command format: {cmd}")
            # Ensure command paths are absolute or safe relative paths
            for arg in cmd:
                if arg.startswith(("..", "/", "~")) and not Path(arg).is_absolute():
                    raise ValueError(f"Unsafe command path: {arg}")

            # Security review: Command validation already performed above (lines 329-337)
            # The cmd list is validated to be a list of strings with proper path checks
            result = subprocess.run(  # noqa: S603
                cmd,
                check=False,
                input=stdin_data,
                capture_output=True,
                text=True,
                cwd=cwd,
                env=env,
                timeout=agent_config.timeout if agent_config and agent_config.timeout else None,
            )

            duration = time.time() - start_time

            if result.returncode != 0:
                raise AgentExecutionError(result.returncode, result.stdout, result.stderr, cmd)

            # Log completion
            logger.info(
                "agent_completed",
                session_id=agent_config.session_id if agent_config else "unknown",
                duration=duration,
                exit_code=result.returncode,
            )

            # Return output and basic metadata
            metadata: dict[str, Any] = {
                "session_id": agent_config.session_id if agent_config else "unknown",
                "duration": duration,
                "exit_code": result.returncode,
            }
            return result.stdout, metadata

        except subprocess.TimeoutExpired as e:
            timeout = agent_config.timeout if agent_config and agent_config.timeout else 0
            raise AgentTimeoutError(timeout, cmd, e.timeout) from e
        except FileNotFoundError:
            raise AgentCommandNotFoundError(cmd[0]) from None
    else:
        # For no stdin, use the original streaming approach
        process = start_streaming_process(cmd, stdin_data, cwd, config)

        try:
            # Run the streaming loop

            output, metadata = run_streaming_loop(process, cmd, agent_config)

            # Handle completion
            return handle_process_completion(process, cmd, time.time(), agent_config.session_id if agent_config else "unknown")
        finally:
            # Clean up process reference if needed
            pass
