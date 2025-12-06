"""Timer-related utility functions."""

import sys
import textwrap
import threading
import time


def wrap_text_in_box(text: str, width: int = 80) -> str:
    """Wrap text in a box with specified width and word-wrap the content.

    Args:
        text: The text to wrap in a box
        width: The width of the box (default 80)

    Returns:
        The text wrapped in a box with borders
    """
    # Account for the border characters (2 chars: one on each side)
    content_width = width - 4  # 2 for left padding and 2 for right padding
    if content_width <= 0:
        content_width = 76  # default width

    # Create the top border
    top_border = "┌" + "─" * (width - 2) + "┐"

    # Create the bottom border
    bottom_border = "└" + "─" * (width - 2) + "┘"

    # Split text into lines if there are existing newlines
    original_lines = text.split("\n")

    # Wrap each original line to fit in the box
    wrapped_lines = []
    for line in original_lines:
        if len(line) <= content_width:
            wrapped_lines.append(line)
        else:
            # Use textwrap to break the line properly with 76 char width for content (80 total - 4 for borders/indentation)
            wrapped_sublines = textwrap.fill(line, width=76).split("\n")
            wrapped_lines.extend(wrapped_sublines)

    # Format each line with proper padding
    formatted_lines = []
    for line in wrapped_lines:
        # If line is empty, just add empty space
        formatted_line = " " * content_width if not line.strip() else line.ljust(content_width)
        formatted_lines.append(f"  {formatted_line}  ")

    # Combine all parts
    result = [top_border] + formatted_lines + [bottom_border]

    return "\n".join(result)


class TimerDisplay:
    """A class to manage the dynamic timer display during agent processing."""

    def __init__(self) -> None:
        self.start_time = time.time()
        self.timer_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.is_running = False

    def _update_timer_display(self) -> None:
        """Internal method to continuously update the timer display."""
        while not self.stop_event.is_set():
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            timer_text = f"⌛ {minutes:02d}:{seconds:02d}"

            # Move cursor to beginning of line and clear the line
            sys.stdout.write(f"\r{timer_text}")
            sys.stdout.flush()

            # Wait 1 second or until stop event
            if self.stop_event.wait(1.0):
                break

    def start(self) -> None:
        """Start the timer display."""
        if not self.is_running:
            self.start_time = time.time()
            self.stop_event.clear()
            self.timer_thread = threading.Thread(target=self._update_timer_display, daemon=True)
            self.timer_thread.start()
            self.is_running = True

    def stop(self) -> None:
        """Stop the timer display."""
        if self.is_running and self.timer_thread:
            self.stop_event.set()
            self.timer_thread.join(timeout=0.1)  # Wait up to 0.1s for thread to finish
            # Move to next line after stopping timer
            sys.stdout.write("\n")
            sys.stdout.flush()
            self.is_running = False
