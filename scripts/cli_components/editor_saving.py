#!/usr/bin/env python3

import datetime
import sys
from pathlib import Path

from scripts.cli_components.text_input_utils import display_final_output


def save_content(lines: list[str], previous_display_lines: int) -> str:
    """Save the content to a timestamped file."""
    # Combine all lines
    content = "\n".join(lines)

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamped filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = logs_dir / f"text_input_{timestamp}.txt"

    # Save the content to the file
    with filename.open("w", encoding="utf-8") as f:
        f.write(content)

    # Clear the previous editor content before showing final output
    if previous_display_lines > 0:
        # Move up to the beginning of the previous display and clear all lines
        sys.stdout.write(f"\033[{previous_display_lines}A")  # Move cursor up to the top of previous display
        sys.stdout.flush()
        # Clear each line completely
        for i in range(previous_display_lines):
            sys.stdout.write("\033[2K")  # Clear the entire line
            sys.stdout.flush()
            if i < previous_display_lines - 1:  # For all but the last line, move to beginning of next line
                sys.stdout.write("\033[B\033[1G")  # Move cursor down to next line and to beginning of that line
                sys.stdout.flush()
        # The cursor is now at the last cleared line. Move back up to print new content
        if previous_display_lines > 1:
            sys.stdout.write(f"\033[{previous_display_lines - 1}A")  # Move back up to the first line position
            sys.stdout.flush()

    # Split content into lines for the utility function
    content_lines = content.split("\n") if content else []

    # Use the utility function to display final output
    display_final_output(content_lines, "✅ Sent to agent")
    return content
