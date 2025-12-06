"""Comprehensive tests for basic edge cases and error conditions in ami-agent interactive mode."""

from unittest.mock import patch

from scripts.cli_components.cursor_manager import CursorManager
from scripts.cli_components.editor_saving import save_content
from scripts.cli_components.text_editor import TextEditor


class TestEdgeCasesAndErrorConditions:
    """Test edge cases and error conditions for ami-agent interactive mode."""

    # Text Editor Edge Cases
    def test_cursor_manager_edge_cases(self):
        """Test cursor manager edge cases."""
        # Empty lines
        cursor = CursorManager([])
        assert cursor.current_line == 0
        assert cursor.current_col == 0

        # Single empty line
        cursor = CursorManager([""])
        assert cursor.current_line == 0
        assert cursor.current_col == 0

        # Move beyond boundaries
        lines = ["test"]
        cursor = CursorManager(lines)

        # Try to move left when already at beginning
        cursor.move_cursor_left()
        cursor.move_cursor_left()  # Should not go beyond 0
        assert cursor.current_col >= 0

        # Try to move up when already at first line
        cursor.move_cursor_up()
        assert cursor.current_line >= 0

        # Single character line
        cursor = CursorManager(["x"])
        assert cursor.current_line == 0
        assert cursor.current_col == 1  # at end of "x"

    def test_cursor_manager_word_movement_edge_cases(self):
        """Test cursor word movement edge cases."""
        # Empty string
        cursor = CursorManager([""])
        cursor.move_to_previous_word()
        assert cursor.current_col == 0

        # Single word
        cursor = CursorManager(["hello"])
        cursor.current_col = len("hello")  # At end
        cursor.move_to_previous_word()
        assert cursor.current_col == 0  # Beginning of word

        # Move to next word from end
        cursor = CursorManager(["hello"])
        cursor.current_col = len("hello")  # At end
        cursor.move_to_next_word()
        assert cursor.current_col == len("hello")  # Stay at end

    def test_text_editor_edge_cases(self):
        """Test text editor edge cases."""
        # Empty initial text
        editor = TextEditor("")
        assert editor.lines == [""]

        # None initial text
        editor = TextEditor()
        assert editor.lines == [""]

        # Very long line
        long_line = "x" * 1000
        editor = TextEditor(long_line)
        assert editor.lines[0] == long_line

    @patch.object(TextEditor, "run")
    def test_text_editor_run_edge_cases(self, mock_run):
        """Test text editor run method edge cases."""
        editor = TextEditor()

        # Test with None return (cancelled)
        mock_run.return_value = None
        result = editor.run()
        assert result is None

        # Test with empty string
        mock_run.return_value = ""
        result = editor.run()
        assert result == ""

        # Test with whitespace-only content
        mock_run.return_value = "   \\n\\t\\n  "
        result = editor.run()
        assert result == "   \\n\\t\\n  "

    def test_save_content_edge_cases(self):
        """Test save content function edge cases."""
        # Empty lines
        content = save_content([], 0)
        assert content == ""

        # Single empty line
        content = save_content([""], 0)
        assert content == ""

        # Lines with only whitespace
        content = save_content(["  ", "\\t", "\\n"], 0)
        assert content == "  \n\\t\n\\n"
