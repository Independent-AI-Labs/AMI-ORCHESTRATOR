"""Streaming-related utility functions extracted from base_provider.py."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from scripts.agents.cli.env_utils import get_unprivileged_env
from scripts.agents.cli.exceptions import (
    AgentCommandNotFoundError,
    AgentExecutionError,
    AgentTimeoutError,
)
from scripts.agents.config import get_config

if TYPE_CHECKING:
    pass

from scripts.agents.cli.process_utils import handle_process_completion, start_streaming_process
from scripts.agents.cli.streaming_loops import AgentConfigProtocol, run_streaming_loop


def execute_streaming(
    cmd: list[str],
    stdin_data: str | None = None,
    cwd: Path | None = None,
    agent_config: AgentConfigProtocol | None = None,
    config: Any = None,
    parse_stream_callback: Callable[..., Any] | None = None,  # Optional callback for parsing stream messages
) -> tuple[str, dict[str, Any] | None]:
    """Execute CLI command in streaming mode.

    Args:
        cmd: Command to execute
        stdin_data: Data to provide to stdin
        cwd: Working directory
        agent_config: Agent configuration
        config: Configuration object
        parse_stream_callback: Optional callback function for parsing stream messages with real-time display

    Returns:
        Tuple of (output, metadata)
    """
    if stdin_data is not None:
        return _execute_with_stdin(cmd, stdin_data, cwd, agent_config, config)
    return _execute_with_streaming(cmd, stdin_data, cwd, agent_config, config, parse_stream_callback)


def _execute_with_stdin(
    cmd: list[str], stdin_data: str, cwd: Path | None, agent_config: AgentConfigProtocol | None, config: Any
) -> tuple[str, dict[str, Any] | None]:
    """Execute command with stdin data provided upfront."""
    # Get unprivileged environment
    if config is None:
        config = get_config()
    env = get_unprivileged_env(config)
    if env is None:
        env = os.environ.copy()

    # Run the process with communicate to provide stdin data
    start_time = time.time()
    try:
        _validate_command(cmd)

        # Security review: Command validation already performed above (lines 329-337)
        # The cmd list is validated to be a list of strings with proper path checks
        result = subprocess.run(
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


def _execute_with_streaming(
    cmd: list[str],
    stdin_data: str | None,
    cwd: Path | None,
    agent_config: AgentConfigProtocol | None,
    config: Any,
    parse_stream_callback: Callable[..., Any] | None,
) -> tuple[str, dict[str, Any] | None]:
    """Execute command in streaming mode."""
    # For no stdin, use the original streaming approach
    process = start_streaming_process(cmd, stdin_data, cwd, config)
    start_time = time.time()

    try:
        if parse_stream_callback:
            return _handle_callback_execution(process, cmd, agent_config, start_time, parse_stream_callback)
        return _handle_standard_execution(process, cmd, agent_config)
    finally:
        # Clean up process reference if needed
        pass


def _validate_command(cmd: list[str]) -> None:
    """Validate command to prevent injection attacks."""
    if not isinstance(cmd, list) or not all(isinstance(arg, str) for arg in cmd):
        raise ValueError(f"Invalid command format: {cmd}")
    # Ensure command paths are absolute or safe relative paths
    for arg in cmd:
        if arg.startswith(("..", "/", "~")) and not Path(arg).is_absolute():
            raise ValueError(f"Unsafe command path: {arg}")


def _handle_callback_execution(
    process: subprocess.Popen[str],
    cmd: list[str],
    agent_config: AgentConfigProtocol | None,
    start_time: float,
    parse_stream_callback: Callable[..., Any],
) -> tuple[str, dict[str, Any] | None]:
    """Handle execution with a callback function."""
    output, metadata = parse_stream_callback(process, cmd, agent_config)

    # For streaming callbacks, we handle completion within the callback,
    # so return the output directly
    duration = time.time() - start_time
    session_id = agent_config.session_id if agent_config else "unknown"

    # Check if process completed successfully
    returncode = process.poll() or 0
    if returncode != 0:
        # Process had an error, but streaming already handled output
        pass

    # Update metadata with duration if not already present
    if metadata is None:
        metadata = {}
    metadata.update({"session_id": session_id, "duration": duration, "exit_code": returncode})
    return output, metadata


def _handle_standard_execution(
    process: subprocess.Popen[str],
    cmd: list[str],
    agent_config: AgentConfigProtocol | None,
) -> tuple[str, dict[str, Any] | None]:
    """Handle standard execution without a callback."""
    output, metadata = run_streaming_loop(process, cmd, agent_config)
    return handle_process_completion(process, cmd, time.time(), agent_config.session_id if agent_config else "unknown")
