#!/usr/bin/env python3

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
        # Calculate the total display lines before making changes
        total_display_lines = 1 + 2 + len(lines) + 1  # 1 for header + 2 for borders + content + 1 for status

        # For subsequent displays (after first), clear previous content using a more robust approach
        if self.previous_display_lines > 0:
            # Use a safer clearing approach: move to bottom of previous display, then clear upward
            # This prevents cursor positioning issues during rapid updates
            for _ in range(self.previous_display_lines):
                sys.stdout.write("\033[1A")  # Move cursor up one line
                sys.stdout.write("\033[2K")  # Clear the entire line
                sys.stdout.write("\033[1G")  # Move cursor to beginning of line (column 1)
                sys.stdout.flush()

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
        for i, line_content in enumerate(lines):
            if i == current_line:
                # Highlight current line by inverting the line number
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

                sys.stdout.write(f" {Colors.REVERSE}{i + 1:2d}{Colors.RESET}| {formatted_line}\n")
            else:
                sys.stdout.write(f" {Colors.CYAN}{i + 1:2d}{Colors.RESET}| {line_content}\n")
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
            # Use the same safer clearing approach as in display_editor
            for _ in range(self.previous_display_lines):
                sys.stdout.write("\033[1A")  # Move cursor up one line
                sys.stdout.write("\033[2K")  # Clear the entire line
                sys.stdout.write("\033[1G")  # Move cursor to beginning of line (column 1)
                sys.stdout.flush()

        # Use the utility function to display final output
        display_final_output(lines, "❌ Message discarded")
