"""Unit tests for text_input_cli module."""

from unittest.mock import Mock, patch

import pytest

from scripts.cli_components.text_input_cli import create_text_editor, main


class TestTextInputCLI:
    """Test the text_input_cli module functionality."""

    @patch("scripts.cli_components.text_input_cli.TextEditor")
    def test_create_text_editor_with_initial_text(self, mock_text_editor):
        """Test create_text_editor with initial text."""
        mock_editor_instance = Mock()
        mock_editor_instance.run.return_value = "Test content"
        mock_text_editor.return_value = mock_editor_instance

        result = create_text_editor("Initial text")

        # Verify TextEditor was created with initial text
        mock_text_editor.assert_called_once_with("Initial text")
        # Verify the run method was called
        mock_editor_instance.run.assert_called_once()
        # Verify the result
        assert result == "Test content"

    @patch("scripts.cli_components.text_input_cli.TextEditor")
    def test_create_text_editor_empty_initial_text(self, mock_text_editor):
        """Test create_text_editor with empty initial text."""
        mock_editor_instance = Mock()
        mock_editor_instance.run.return_value = ""
        mock_text_editor.return_value = mock_editor_instance

        result = create_text_editor("")

        mock_text_editor.assert_called_once_with("")
        assert result == ""

    @patch("scripts.cli_components.text_input_cli.TextEditor")
    def test_create_text_editor_none_initial_text(self, mock_text_editor):
        """Test create_text_editor with None initial text."""
        mock_editor_instance = Mock()
        mock_editor_instance.run.return_value = "Some content"
        mock_text_editor.return_value = mock_editor_instance

        result = create_text_editor(None)

        # TextEditor should be called with the None value directly
        mock_text_editor.assert_called_once_with(None)
        assert result == "Some content"

    @patch("scripts.cli_components.text_input_cli.TextEditor")
    def test_create_text_editor_long_initial_text(self, mock_text_editor):
        """Test create_text_editor with long initial text."""
        long_text = "A" * 1000
        mock_editor_instance = Mock()
        mock_editor_instance.run.return_value = long_text + " edited"
        mock_text_editor.return_value = mock_editor_instance

        result = create_text_editor(long_text)

        mock_text_editor.assert_called_once_with(long_text)
        assert result == long_text + " edited"

    @patch("sys.argv")
    @patch("scripts.cli_components.text_input_cli.create_text_editor")
    def test_main_with_command_line_args(self, mock_create_editor, mock_argv):
        """Test main function with command line arguments."""
        mock_argv.__getitem__ = lambda _, idx: {0: "text_input_cli.py", 1: "arg1", 2: "arg2"}.get(idx, "")
        mock_argv.__len__ = lambda _: 3
        mock_create_editor.return_value = "Test result"

        main()

        # Should join command line args (excluding script name) as initial text
        mock_create_editor.assert_called_once_with("arg1 arg2")

    @patch("sys.argv")
    @patch("scripts.cli_components.text_input_cli.create_text_editor")
    def test_main_with_no_args(self, mock_create_editor, mock_argv):
        """Test main function with no command line arguments."""
        mock_argv.__getitem__ = lambda _, idx: "text_input_cli.py" if idx == 0 else ""
        mock_argv.__len__ = lambda _: 1
        mock_create_editor.return_value = None

        main()

        # Should call with empty string when no additional args
        mock_create_editor.assert_called_once_with("")

    @patch("sys.argv")
    @patch("scripts.cli_components.text_input_cli.create_text_editor")
    def test_main_with_single_arg(self, mock_create_editor, mock_argv):
        """Test main function with single command line argument."""
        mock_argv.__getitem__ = lambda _, idx: {0: "text_input_cli.py", 1: "single_arg"}.get(idx, "")
        mock_argv.__len__ = lambda _: 2
        mock_create_editor.return_value = "Result"

        main()

        # Should call with just the single argument
        mock_create_editor.assert_called_once_with("single_arg")


if __name__ == "__main__":
    pytest.main([__file__])
