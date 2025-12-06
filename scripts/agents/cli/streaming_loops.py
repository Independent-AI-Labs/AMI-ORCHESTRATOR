"""Streaming loop-related utility functions."""

import subprocess
import sys
import textwrap
import time
from typing import Any, Protocol

from loguru import logger

from scripts.agents.cli.exceptions import AgentTimeoutError
from scripts.agents.cli.process_utils import read_streaming_line
from scripts.agents.cli.streaming_utils import calculate_timeout
from scripts.agents.cli.timer_utils import TimerDisplay

# Constants for display formatting
CONTENT_WIDTH = 76  # Content width for wrapped text (80 total - 4 for borders/indentation)
TOTAL_WIDTH = 80  # Total width for display boxes


class AgentConfigProtocol(Protocol):
    """Protocol for agent configuration to avoid circular imports."""

    session_id: str
    timeout: int | None
    enable_streaming: bool | None


# Define a protocol for the provider interface to avoid circular imports
class StreamMessageParser(Protocol):
    """Protocol defining the interface for stream message parsing."""

    def _parse_stream_message(
        self,
        line: str,
        cmd: list[str],
        line_count: int,
        agent_config: Any,
    ) -> tuple[str, dict[str, Any] | None]:
        """Parse a single line from CLI's streaming output."""
        ...


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


def run_streaming_loop_with_display(
    process: subprocess.Popen[str],
    cmd: list[str],
    agent_config: AgentConfigProtocol | None,
    provider_instance: StreamMessageParser | None = None,
    capture_content: bool = False,  # When True, content is captured but not printed directly
) -> tuple[str, dict[str, Any]]:
    """Run the main streaming loop with clean output display.

    Args:
        process: The subprocess to read from
        cmd: Original command for error reporting
        agent_config: Agent configuration
        provider_instance: The CLI provider instance with _parse_stream_message method
        capture_content: When True, content is captured for return but not printed to stdout

    Returns:
        Tuple of (output, metadata)
    """
    display_context: dict[str, Any] = {
        "full_output": "",
        "started_at": time.time(),
        "session_id": agent_config.session_id if agent_config else "unknown",
        "timer": TimerDisplay(),
        "content_started": False,
        "box_displayed": False,
        "last_print_ended_with_newline": False,
        "capture_content": capture_content,  # Add flag to control output behavior
        "response_box_started": False,  # Track if response box top border has been displayed
        "response_box_ended": False,  # Track if response box bottom border has been displayed
    }

    # Start the timer display
    timer_display = display_context["timer"]
    if isinstance(timer_display, TimerDisplay):
        timer_display.start()

    try:
        # Main streaming loop
        while True:
            should_continue = _handle_read_iteration(process, cmd, agent_config, display_context, provider_instance)
            if not should_continue:
                break
    finally:
        timer_display = display_context["timer"]
        if isinstance(timer_display, TimerDisplay):
            _handle_display_cleanup(timer_display)

        # Close response box if it was opened but not yet closed
        if (
            not display_context.get("capture_content", False)
            and display_context.get("response_box_started", False)
            and not display_context.get("response_box_ended", False)
        ):
            sys.stdout.write("└" + "─" * 78 + "┘\n")  # Bottom border
            sys.stdout.flush()
            display_context["response_box_ended"] = True

    # Add completion message after processing is done
    if not display_context.get("capture_content", False):
        # Display "Received at" message after processing completes
        sys.stdout.write(f"🤖 Received at {time.strftime('%H:%M:%S')}\n")
        sys.stdout.flush()

    metadata = {
        "session_id": display_context["session_id"],
        "duration": time.time() - display_context["started_at"],
        "output_length": len(display_context["full_output"]),
    }
    return display_context["full_output"], metadata


def _handle_read_iteration(
    process: subprocess.Popen[str],
    cmd: list[str],
    agent_config: AgentConfigProtocol | None,
    display_context: dict[str, Any],
    provider_instance: StreamMessageParser | None,
) -> bool:
    """Handle a single iteration of the streaming read loop."""
    # Calculate timeout for this read
    timeout_val = calculate_timeout(agent_config.timeout if agent_config else None, len(display_context["full_output"]))

    # Read a line with timeout
    line, is_timeout = read_streaming_line(process, timeout_val, cmd)

    if is_timeout:
        # Check if overall timeout was exceeded
        return not _handle_timeout(cmd, agent_config, display_context["started_at"])

    if line is None:
        # Check if process has exited
        return process.poll() is None  # Continue if process is still running

    # Process the line based on whether we have a provider instance
    if provider_instance:
        _process_line_with_provider(line, cmd, display_context, provider_instance, len(display_context["full_output"]), agent_config)
    else:
        _process_raw_line(line, display_context)

    return True


def _handle_timeout(cmd: list[str], agent_config: AgentConfigProtocol | None, started_at: float) -> bool:
    """Handle timeout case. Returns True if we should stop the loop (timeout error), False to continue waiting."""
    if agent_config and agent_config.timeout is not None:
        elapsed = time.time() - started_at
        if elapsed >= agent_config.timeout:
            timeout = agent_config.timeout or 0
            raise AgentTimeoutError(timeout, cmd, elapsed) from None
    return False  # Continue waiting


def _process_line_with_provider(
    line: str,
    cmd: list[str],
    display_context: dict[str, Any],
    provider_instance: StreamMessageParser,
    line_count: int,
    agent_config: AgentConfigProtocol | None,
) -> None:
    """Process a line using the provider-specific parser."""
    chunk_text, chunk_metadata = provider_instance._parse_stream_message(line, cmd, line_count, agent_config)

    # Process the chunk
    if chunk_text:
        if not display_context["content_started"]:  # First piece of actual response content
            if not display_context.get("capture_content", False):
                display_context["timer"].stop()  # Stop timer to clear its display if we're displaying content
            # Mark that content has started
            display_context["content_started"] = True
            display_context["box_displayed"] = True
            # Display response box top border if we're showing content
            if not display_context.get("capture_content", False):
                # Print the top border of the response box
                sys.stdout.write("┌" + "─" * 78 + "┐\n")  # Top border with 80 chars total
                sys.stdout.flush()
            display_context["response_box_started"] = True

        # Only print if not in capture mode
        if not display_context.get("capture_content", False):
            # Add word wrapping to 76 characters for content area (80 total - 4 for borders/indentation)
            # Split the chunk by newlines first, then wrap each line to proper width
            processed_lines = _process_chunk_text(chunk_text)

            # Actually display the output with the same format as input (2-space indentation, no side borders)
            for _i, processed_line in enumerate(processed_lines):
                # Just use the processed line as is (it already has 2-space indentation)
                # Remove the original indentation to avoid double-indenting
                content = processed_line[2:] if processed_line.startswith("  ") else processed_line
                sys.stdout.write(f"  {content}\n")
                sys.stdout.flush()

        # Track if this chunk ends with a newline
        display_context["last_print_ended_with_newline"] = chunk_text.endswith("\n")
        display_context["full_output"] += chunk_text

    # Store metadata if needed
    if chunk_metadata:
        # Process provider-specific metadata
        pass


def _process_chunk_text(chunk_text: str) -> list[str]:
    """Process and wrap text chunk for display."""
    lines = chunk_text.split("\n")
    processed_lines = []

    for line in lines:
        if len(line) <= CONTENT_WIDTH:  # Content width is 76 chars (80 total - 4 for borders/indentation)
            if line.strip():  # Non-empty line
                processed_lines.append("  " + line)
            else:  # Empty line for paragraph breaks
                processed_lines.append("  ")  # Just indentation
        else:
            # Wrap the line to CONTENT_WIDTH characters, then add indentation
            wrapped = textwrap.fill(line, width=CONTENT_WIDTH).split("\n")
            indented_wrapped = ["  " + wrap_line for wrap_line in wrapped]
            processed_lines.extend(indented_wrapped)

    return processed_lines


def _process_raw_line(line: str, display_context: dict[str, Any]) -> None:
    """Process a raw line when no provider instance is available."""
    if not display_context["content_started"]:  # First piece of content
        if not display_context.get("capture_content", False):
            display_context["timer"].stop()
        # Mark that content has started
        display_context["content_started"] = True
        display_context["box_displayed"] = True

    # Add word wrapping to TOTAL_WIDTH characters total (CONTENT_WIDTH for content + 4 for indentation/borders)
    if len(line) <= CONTENT_WIDTH:  # Content width is 76 chars (80 total - 4 for borders/indentation)
        # Only print if not in capture mode
        if not display_context.get("capture_content", False):
            sys.stdout.write("  " + line + "\n")
            sys.stdout.flush()
        display_context["last_print_ended_with_newline"] = True
    else:
        # Wrap the line to CONTENT_WIDTH characters, then add indentation
        wrapped = textwrap.fill(line, width=CONTENT_WIDTH).split("\n")
        for idx, wrap_line in enumerate(wrapped):
            # Only print if not in capture mode
            if not display_context.get("capture_content", False):
                sys.stdout.write("  " + wrap_line + "\n")
                sys.stdout.flush()
            if idx < len(wrapped) - 1 and not display_context.get("capture_content", False):  # For all but the last wrapped line
                sys.stdout.write("\n")  # Add newline between wrapped lines
                sys.stdout.flush()
        # If there were multiple wrapped lines, the last print ended with newline
        display_context["last_print_ended_with_newline"] = True
    display_context["full_output"] += line + "\n"


def _handle_display_cleanup(timer: TimerDisplay) -> None:
    """Handle cleanup of display elements."""
    # Stop and clear the timer display when done (only if still running)
    if timer.is_running:  # Only stop if it's still running
        timer.stop()
