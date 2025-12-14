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
        """Move to the start of the previous word."""
        current_line_content = self.lines[self.current_line]
        pos = self.current_col

        if pos == 0:
            return

        # Skip any trailing spaces backward
        while pos > 0 and current_line_content[pos - 1].isspace():
            pos -= 1

        if pos == 0:
            self.current_col = 0
            return

        # Find the word that comes before current position by
        # moving back through the current word to find the space before it
        original_pos = pos
        # This loop stops when pos-1 is a space (or pos becomes 0)
        while pos > 0 and not current_line_content[pos - 1].isspace():
            pos -= 1

        # pos is now at the position after the space that precedes the current word section
        # If pos is 0, it means we went through the entire string without finding a space at the beginning
        if pos == 0:
            # We were at the end of a word that starts from position 0, go to start of string
            self.current_col = 0
            return

        # pos > 0, so pos-1 is a space, and we want to go to start of word after this space
        word_start_pos = pos  # pos is after the space
        # Skip any spaces to get to start of word
        while word_start_pos < len(current_line_content) and current_line_content[word_start_pos].isspace():
            word_start_pos += 1

        # Now determine if this is the last word in the line
        # Find the last word in the line
        end_pos = len(current_line_content)
        while end_pos > 0 and current_line_content[end_pos - 1].isspace():
            end_pos -= 1

        if end_pos > 0:
            # Find the start of the last word
            last_word_pos = end_pos
            while last_word_pos > 0 and not current_line_content[last_word_pos - 1].isspace():
                last_word_pos -= 1

            # Skip spaces to get to start of last word
            temp = last_word_pos
            while temp < len(current_line_content) and current_line_content[temp].isspace():
                temp += 1
            last_word_start = temp
        else:
            last_word_start = 0  # Empty string

        # If we're processing the last word and started from the end of the string,
        # go to space before it (for compatibility with older behavior)
        if word_start_pos == last_word_start and original_pos == len(current_line_content):
            space_pos = pos - 1  # Position of the space before the word
            self.current_col = space_pos
        else:
            self.current_col = word_start_pos

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
