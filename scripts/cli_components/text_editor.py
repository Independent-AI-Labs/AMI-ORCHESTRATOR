#!/usr/bin/env python3

from typing import Any

from scripts.cli_components.cursor_manager import CursorManager
from scripts.cli_components.editor_display import EditorDisplay
from scripts.cli_components.editor_saving import save_content
from scripts.cli_components.text_input_utils import read_key_sequence


class TextEditor:
    """A class to manage the text editor functionality."""

    def __init__(self, initial_text: str = "") -> None:
        self.lines: list[str] = initial_text.split("\n") if initial_text else [""]
        self.cursor_manager = CursorManager(self.lines)

    def handle_key_navigation(self, key: str) -> None:
        """Handle all cursor navigation keys."""
        if key == "UP":
            self.cursor_manager.move_cursor_up()
        elif key == "DOWN":
            self.cursor_manager.move_cursor_down()
        elif key == "LEFT":
            self.cursor_manager.move_cursor_left()
        elif key == "RIGHT":
            self.cursor_manager.move_cursor_right()
        elif key == "CTRL_LEFT":  # Ctrl+Left - move to previous word
            self.cursor_manager.move_to_previous_word()
        elif key == "CTRL_RIGHT":  # Ctrl+Right - move to next word
            self.cursor_manager.move_to_next_word()
        elif key == "CTRL_UP":  # Ctrl+Up - move to previous paragraph (empty line)
            self.cursor_manager.move_to_previous_paragraph()
        elif key == "CTRL_DOWN":  # Ctrl+Down - move to next paragraph (empty line)
            self.cursor_manager.move_to_next_paragraph()

    def process_enter_key(self) -> None:
        """Process the Enter key by splitting the current line."""
        # Split the current line at the cursor position
        current_line_content = self.lines[self.cursor_manager.current_line]
        before_cursor = current_line_content[: self.cursor_manager.current_col]
        after_cursor = current_line_content[self.cursor_manager.current_col :]

        # Update current line and insert new line
        self.lines[self.cursor_manager.current_line] = before_cursor
        self.lines.insert(self.cursor_manager.current_line + 1, after_cursor)

        # Move to the new line
        self.cursor_manager.current_line += 1
        self.cursor_manager.current_col = 0

    def process_backspace_key(self) -> None:
        """Process the Backspace key by deleting character or joining lines."""
        if self.cursor_manager.current_col > 0:
            # Delete character before cursor
            current_line_content = self.lines[self.cursor_manager.current_line]
            before_cursor = current_line_content[: self.cursor_manager.current_col - 1]
            after_cursor = current_line_content[self.cursor_manager.current_col :]
            self.lines[self.cursor_manager.current_line] = before_cursor + after_cursor
            self.cursor_manager.current_col -= 1
        elif self.cursor_manager.current_line > 0:
            # Join with previous line
            prev_line = self.lines[self.cursor_manager.current_line - 1]
            current_line_content = self.lines[self.cursor_manager.current_line]

            # Combine lines
            self.lines[self.cursor_manager.current_line - 1] = prev_line + current_line_content

            # Remove current line
            del self.lines[self.cursor_manager.current_line]

            # Move to previous line and set column to end of that line
            self.cursor_manager.current_line -= 1
            self.cursor_manager.current_col = len(self.lines[self.cursor_manager.current_line])

    def process_home_key(self) -> None:
        """Process the Home key (Ctrl+A) to move cursor to beginning of line."""
        # Ctrl+A pressed - go to beginning of current line
        self.cursor_manager.current_col = 0

    def handle_text_modification(self, key: str) -> None:
        """Handle text modification keys (enter, backspace, etc)."""
        if key == "ENTER":
            self.process_enter_key()
        elif key == "BACKSPACE":
            self.process_backspace_key()
        elif key == "HOME":
            self.process_home_key()

    def run(self) -> str | Any | None:
        """Run the main editor loop."""
        display = EditorDisplay()
        # Initial display
        display.display_editor(self.lines, self.cursor_manager.current_line, self.cursor_manager.current_col)

        try:
            while True:
                # Process one key at a time
                key = read_key_sequence()

                # Handle special cases first
                if key is None:
                    # Skip unhandled control characters
                    continue

                # Handle special keys that require screen refresh - only process string keys
                if isinstance(key, str) and key in [
                    "UP",
                    "DOWN",
                    "LEFT",
                    "RIGHT",
                    "ENTER",
                    "BACKSPACE",
                    "EOF",
                    "HOME",
                    "CTRL_UP",
                    "CTRL_DOWN",
                    "CTRL_LEFT",
                    "CTRL_RIGHT",
                ]:
                    if key == "EOF":
                        # Ctrl+S pressed - send to agent and exit
                        # Just break and let the save_content function handle the message
                        break
                    if key in ["UP", "DOWN", "LEFT", "RIGHT", "CTRL_UP", "CTRL_DOWN", "CTRL_LEFT", "CTRL_RIGHT"]:
                        self.handle_key_navigation(key)
                    else:  # Other text modification keys
                        self.handle_text_modification(key)

                    # Redraw the editor by reprinting the entire interface
                    display.display_editor(self.lines, self.cursor_manager.current_line, self.cursor_manager.current_col)

                elif isinstance(key, str) and len(key) == 1:
                    # Regular character input
                    current_line_content = self.lines[self.cursor_manager.current_line]

                    # Insert character at cursor position
                    before_cursor = current_line_content[: self.cursor_manager.current_col]
                    after_cursor = current_line_content[self.cursor_manager.current_col :]

                    self.lines[self.cursor_manager.current_line] = before_cursor + key + after_cursor
                    self.cursor_manager.current_col += 1

                    # Redraw the editor by reprinting the entire interface
                    display.display_editor(self.lines, self.cursor_manager.current_line, self.cursor_manager.current_col)

        except KeyboardInterrupt:
            display.handle_keyboard_interrupt(self.lines)
            return None

        return save_content(self.lines, display.previous_display_lines)
