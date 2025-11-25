#!/usr/bin/env python3

import contextlib
import shutil
import sys

from scripts.cli_components.text_input_utils import Colors, display_final_output

"""
Display functionality for the text editor.
"""


class EditorDisplay:
    """Handles the display functionality of the text editor."""

    def __init__(self) -> None:
        # Store the original cursor position (number of lines we print)
        self.editor_line_count: int = 0
        self.previous_display_lines: int = 0  # Track how many lines were displayed in the previous render

    def display_editor(self, lines: list[str], current_line: int, current_col: int) -> None:
        """Display the current state of the editor."""
        # Get terminal size with default
        with contextlib.suppress(OSError):
            _, terminal_width = shutil.get_terminal_size()

        # Display ALL input lines to maintain terminal scrollability
        total_lines = len(lines)

        # Count how many lines we're about to print to track for redraw
        lines_to_print = []

        # Show ALL lines as required by spec
        for i in range(total_lines):
            if i == current_line:
                # Highlight current line by inverting the line number
                line_content = lines[i]

                # Apply inverted video to the character at cursor position
                if current_col < len(line_content):
                    # Split the line to apply reverse video to the character at cursor
                    before_cursor = line_content[:current_col]
                    cursor_char = line_content[current_col]
                    after_cursor = line_content[current_col + 1 :]
                    formatted_line = f"{before_cursor}{Colors.REVERSE}{cursor_char}{Colors.RESET}{after_cursor}"
                else:
                    # If cursor is at the end of the line, just append a space with reverse video
                    formatted_line = f"{line_content}{Colors.REVERSE} {Colors.RESET}"

                lines_to_print.append(f" {Colors.REVERSE}{i + 1:2d}{Colors.RESET}| {formatted_line}")
            else:
                line_content = lines[i]
                lines_to_print.append(f" {Colors.CYAN}{i + 1:2d}{Colors.RESET}| {line_content}")

        # Calculate total lines to display (header + borders + content + status)
        total_display_lines = 1 + 2 + len(lines_to_print) + 1  # 1 for header + 2 for borders + content + 1 for status

        # For subsequent displays (after first), clear previous content by moving up
        if self.previous_display_lines > 0:
            # Move up to the beginning of the previous display and clear all lines
            sys.stdout.write(f"\033[{self.previous_display_lines}A")  # Move cursor up to the top of previous display
            sys.stdout.flush()
            # Clear each line completely, ensuring proper positioning for next line
            for i in range(self.previous_display_lines):
                sys.stdout.write("\033[2K")  # Clear the entire line
                sys.stdout.flush()
                if i < self.previous_display_lines - 1:  # For all but the last line, move to beginning of next line
                    sys.stdout.write("\033[B\033[1G")  # Move cursor down to next line and to beginning of that line
                    sys.stdout.flush()
            # The cursor is now at the last cleared line. Move back up to the first line position to print new content
            # We moved down (previous_display_lines - 1) times, so we need to move back up the same amount
            # to get back to the position of the first line
            if self.previous_display_lines > 1:
                sys.stdout.write(f"\033[{self.previous_display_lines - 1}A")  # Move back up to the first line position
                sys.stdout.flush()
            # If previous_display_lines was 1, we don't need to move up since we're already at the right position

        # Print a header with instructions (no borders)
        effective_width = 80  # Fixed to 80 characters wide
        content_text = (
            f" Arrows: nav {Colors.CYAN}|{Colors.YELLOW} Enter: newline {Colors.CYAN}|{Colors.YELLOW} Backspace: edit {Colors.CYAN}|{Colors.GREEN} Ctrl+S: send"
        )
        content_width = effective_width  # Full width for header without borders
        content_text = content_text[:content_width] if len(content_text) > content_width else content_text.ljust(content_width)
        sys.stdout.write(content_text + "\n")
        sys.stdout.flush()

        # Create top border for the input area
        border_line = f"{Colors.CYAN}┌{'─' * (effective_width - 2)}┐{Colors.RESET}"
        sys.stdout.write(border_line + "\n")
        sys.stdout.flush()

        # Print all content lines (ALL of them as required)
        for line in lines_to_print:
            sys.stdout.write(f"{line}\n")
            sys.stdout.flush()

        # Create bottom border for the input area
        border_line = f"{Colors.CYAN}└{'─' * (effective_width - 2)}┘{Colors.RESET}"
        sys.stdout.write(border_line + "\n")
        sys.stdout.flush()

        # Print status area with color (keep it compact)
        status_line = (
            f"{Colors.GREEN}Ln {current_line + 1}, "
            f"Col {current_col + 1}{Colors.RESET} | "
            f"{Colors.BLUE}{len(lines)} lines{Colors.RESET} | "
            f"{Colors.GREEN}Ctrl+S to send to agent{Colors.RESET}"
        )
        sys.stdout.write(f"{status_line}\n")
        sys.stdout.flush()

        # Update the count of lines we just printed and store for next time
        self.editor_line_count = total_display_lines
        self.previous_display_lines = self.editor_line_count

        # For in-terminal editing, we can't maintain a precise cursor position
        # due to terminal scrollability requirements. The cursor will be generally
        # at the end after display, but the user will type at the logical position.
        # We maintain the logical position in our variables instead.
        # Don't position cursor - let it stay after the output

    def handle_keyboard_interrupt(self, lines: list[str]) -> None:
        """Handle keyboard interrupt to show final output."""
        # Clear the previous editor content before showing final output
        if self.previous_display_lines > 0:
            # Move up to the beginning of the previous display and clear all lines
            sys.stdout.write(f"\033[{self.previous_display_lines}A")  # Move cursor up to the top of previous display
            sys.stdout.flush()
            # Clear each line completely
            for i in range(self.previous_display_lines):
                sys.stdout.write("\033[2K")  # Clear the entire line
                sys.stdout.flush()
                if i < self.previous_display_lines - 1:  # For all but the last line, move to beginning of next line
                    sys.stdout.write("\033[B\033[1G")  # Move cursor down to next line and to beginning of that line
                    sys.stdout.flush()
            # The cursor is now at the last cleared line. Move back up to print new content
            if self.previous_display_lines > 1:
                sys.stdout.write(f"\033[{self.previous_display_lines - 1}A")  # Move back up to the first line position
                sys.stdout.flush()

        # Use the utility function to display final output
        display_final_output(lines, "❌ Exited")
