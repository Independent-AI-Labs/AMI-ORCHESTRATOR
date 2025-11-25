#!/usr/bin/env python3


"""
Cursor management functionality for the text editor.
"""


class CursorManager:
    """Manages cursor position and movement within the text editor."""

    def __init__(self, lines: list[str]) -> None:
        self.lines: list[str] = lines
        # Current cursor position (line, column)
        self.current_line: int = len(lines) - 1 if lines else 0
        self.current_col: int = len(lines[self.current_line]) if lines and lines[self.current_line] else 0

    def move_cursor_up(self) -> None:
        """Move cursor up one line."""
        if self.current_line > 0:
            self.current_line -= 1
            # Adjust column to not exceed line length
            self.current_col = min(self.current_col, len(self.lines[self.current_line]))

    def move_cursor_down(self) -> None:
        """Move cursor down one line."""
        if self.current_line < len(self.lines) - 1:
            self.current_line += 1
            # Adjust column to not exceed line length
            self.current_col = min(self.current_col, len(self.lines[self.current_line]))

    def move_cursor_left(self) -> None:
        """Move cursor left one position."""
        if self.current_col > 0:
            self.current_col -= 1
        elif self.current_line > 0:
            # Move to end of previous line
            self.current_line -= 1
            self.current_col = len(self.lines[self.current_line])

    def move_cursor_right(self) -> None:
        """Move cursor right one position."""
        current_line_len = len(self.lines[self.current_line])
        if self.current_col < current_line_len:
            self.current_col += 1
        elif self.current_line < len(self.lines) - 1:
            # Move to beginning of next line
            self.current_line += 1
            self.current_col = 0

    def move_to_previous_word(self) -> None:
        """Move cursor to the beginning of the previous word."""
        current_line_content = self.lines[self.current_line]
        # Find the previous word by looking backward from current position
        pos = self.current_col
        # Move back to skip any spaces at the current position
        while pos > 0 and current_line_content[pos - 1].isspace():
            pos -= 1
        # Find the start of the current word (or previous word if at space)
        while pos > 0 and not current_line_content[pos - 1].isspace():
            pos -= 1
        # Skip any spaces before the word
        while pos > 0 and pos < len(current_line_content) and current_line_content[pos].isspace():
            pos += 1
        self.current_col = pos

    def move_to_next_word(self) -> None:
        """Move cursor to the beginning of the next word."""
        current_line_content = self.lines[self.current_line]
        pos = self.current_col
        # Move forward to skip the current word
        while pos < len(current_line_content) and not current_line_content[pos].isspace():
            pos += 1
        # Skip spaces until we reach the next word
        while pos < len(current_line_content) and current_line_content[pos].isspace():
            pos += 1
        self.current_col = pos

    def move_to_previous_paragraph(self) -> None:
        """Move cursor to the previous paragraph."""
        # Find the previous empty line or beginning of buffer
        for i in range(self.current_line - 1, -1, -1):
            if not self.lines[i].strip():  # Empty line (or whitespace only)
                self.current_line = i
                self.current_col = 0
                break
        else:
            # If no empty line found, go to the first line
            self.current_line = 0
            self.current_col = 0

    def move_to_next_paragraph(self) -> None:
        """Move cursor to the next paragraph."""
        # Find the next empty line or end of buffer
        for i in range(self.current_line + 1, len(self.lines)):
            if not self.lines[i].strip():  # Empty line (or whitespace only)
                self.current_line = i
                self.current_col = 0
                break
        else:
            # If no empty line found, go to the last line
            self.current_line = len(self.lines) - 1
            self.current_col = len(self.lines[self.current_line])
