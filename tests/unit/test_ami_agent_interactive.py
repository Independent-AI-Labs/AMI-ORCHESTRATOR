"""Unit tests for ami-agent interactive mode functionality."""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from scripts.agents.cli.claude_cli import ClaudeAgentCLI
from scripts.agents.cli.config import AgentConfig, AgentConfigPresets
from scripts.agents.cli.config_service import ConfigService
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.cli.mode_handlers import (
    mode_interactive_editor,
)
from scripts.agents.cli.provider_type import ProviderType
from scripts.agents.cli.qwen_cli import QwenAgentCLI
from scripts.agents.cli.streaming_loops import (
    _handle_display_cleanup,
    _process_chunk_text,
    _process_line_with_provider,
    run_streaming_loop_with_display,
)
from scripts.agents.cli.timer_utils import TimerDisplay, wrap_text_in_box
from scripts.cli_components.cursor_manager import CursorManager
from scripts.cli_components.text_editor import TextEditor


class TestAgentConfigPresets:
    """Test agent configuration presets."""

    def test_worker_preset(self):
        """Test worker preset configuration."""
        config = AgentConfigPresets.worker("test-session")
        assert config.model == "claude-sonnet-4-5"
        assert config.session_id == "test-session"
        assert config.provider == ProviderType.CLAUDE
        assert config.allowed_tools is None  # All tools allowed
        assert config.enable_hooks is True
        assert config.timeout == 180

    def test_audit_preset(self):
        """Test audit preset configuration."""
        config = AgentConfigPresets.audit("test-session")
        assert config.model == "claude-sonnet-4-5"
        assert config.session_id == "test-session"
        assert config.allowed_tools == ["WebSearch", "WebFetch"]
        assert config.enable_hooks is False
        assert config.timeout == 180

    def test_interactive_preset(self):
        """Test interactive preset configuration."""
        config = AgentConfigPresets.interactive("test-session", {"test": "mcp"})
        assert config.model == "claude-sonnet-4-5"
        assert config.session_id == "test-session"
        assert config.allowed_tools is None
        assert config.enable_hooks is True
        assert config.timeout is None  # No timeout for interactive
        assert config.mcp_servers == {"test": "mcp"}


class TestConfigService:
    """Test configuration service functionality."""

    def test_get_provider_command(self):
        """Test get_provider_command returns correct paths."""
        from unittest.mock import patch


        # Reset the singleton instance to ensure clean state
        ConfigService._instance = None
        ConfigService._config_data = None

        # Create separate mock objects for the base paths that get checked
        mock_root_base = MagicMock()
        mock_root_base.exists.return_value = True  # This should return True to be selected

        mock_other_base = MagicMock()
        mock_other_base.exists.return_value = False  # This should return False

        # Create parent path mocks
        mock_root = MagicMock()
        mock_other = MagicMock()

        # Set up the division operations
        mock_root.__truediv__ = MagicMock(return_value=mock_root_base)
        mock_other.__truediv__ = MagicMock(return_value=mock_other_base)

        # Create the file mock
        mock_file = MagicMock()
        mock_file.resolve.return_value = mock_file
        mock_file.parents = [mock_root, mock_other]  # First parent has base, second doesn't

        # String representation for path construction - need to take 'self' parameter
        mock_root.__str__ = lambda self: "/mock/root"

        with patch("scripts.agents.cli.config_service.Path") as path_mock:
            # Configure the path mock to return our mock file when called
            path_mock.return_value = mock_file

            # Mock yaml loading
            with patch("scripts.agents.cli.config_service.yaml.safe_load") as mock_yaml:
                mock_yaml.return_value = {"test": "data"}

                # Create config service instance
                config_service = ConfigService()

                # Test provider commands
                claude_cmd = config_service.get_provider_command(ProviderType.CLAUDE)
                assert claude_cmd == "/mock/root/.venv/node_modules/.bin/claude"

                qwen_cmd = config_service.get_provider_command(ProviderType.QWEN)
                assert qwen_cmd == "/mock/root/.venv/node_modules/.bin/qwen"

                gemini_cmd = config_service.get_provider_command(ProviderType.GEMINI)
                assert gemini_cmd == "/mock/root/.venv/node_modules/.bin/gemini"


class TestFactory:
    """Test agent CLI factory functionality."""

    def test_get_agent_cli_default(self):
        """Test factory returns default Claude CLI."""

        cli = get_agent_cli()
        assert isinstance(cli, ClaudeAgentCLI)

    def test_get_agent_cli_with_config(self):
        """Test factory returns correct CLI based on provider."""

        # Test Claude provider
        config = AgentConfig("test", "session", ProviderType.CLAUDE)
        cli = get_agent_cli(config)
        assert isinstance(cli, ClaudeAgentCLI)

        # Test Qwen provider
        config = AgentConfig("test", "session", ProviderType.QWEN)
        cli = get_agent_cli(config)
        assert isinstance(cli, QwenAgentCLI)


class TestTimerUtils:
    """Test timer and text wrapping utilities."""

    def test_wrap_text_in_box_simple(self):
        """Test wrapping simple text in a box."""
        result = wrap_text_in_box("Hello world")
        lines = result.split("\n")
        assert lines[0].startswith("┌") and lines[0].endswith("┐")
        # The actual content after stripping should just be the original text
        assert lines[1].strip() == "Hello world"
        assert lines[2].startswith("└") and lines[2].endswith("┘")

    def test_wrap_text_in_box_multiline(self):
        """Test wrapping multiline text in a box."""
        text = "Line 1\nLine 2\nLine 3"
        result = wrap_text_in_box(text)
        lines = result.split("\n")
        assert len(lines) == 5  # Top border + 3 content lines + bottom border
        assert lines[0].startswith("┌") and lines[0].endswith("┐")
        assert all("  Line" in line for line in lines[1:-1] if line.strip())
        assert lines[-1].startswith("└") and lines[-1].endswith("┘")

    def test_wrap_text_in_box_long_line(self):
        """Test wrapping a long line that needs to be broken."""
        long_text = "This is a very long line that exceeds the standard 76 character width and will need to be wrapped properly"
        result = wrap_text_in_box(long_text)
        lines = result.split("\n")
        # Should wrap the long text into multiple lines within the box
        assert len(lines) > 2
        assert lines[0].startswith("┌") and lines[-1].startswith("└")


class TestCursorManager:
    """Test cursor management functionality."""

    def test_initial_position(self):
        """Test initial cursor position."""
        lines = ["Hello", "World"]
        cursor = CursorManager(lines)
        assert cursor.current_line == 1  # Last line
        assert cursor.current_col == 5  # Length of "World"

    def test_cursor_movement(self):
        """Test cursor movement operations."""
        lines = ["Hello", "World"]
        cursor = CursorManager(lines)

        # Move left
        cursor.move_cursor_left()
        assert cursor.current_col == 4

        # Move left again to previous line
        for _ in range(5):
            cursor.move_cursor_left()
        assert cursor.current_line == 0
        assert cursor.current_col == 5

        # Move right to next line
        cursor.move_cursor_right()
        assert cursor.current_line == 1
        assert cursor.current_col == 0

    def test_word_movement(self):
        """Test word movement functionality."""
        lines = ["test hello world"]
        cursor = CursorManager(lines)

        # Move to end first
        cursor.current_col = len(lines[0])

        # Move to previous word
        cursor.move_to_previous_word()
        assert cursor.current_col == 10  # Before "world"

        # Move to previous word again
        cursor.move_to_previous_word()
        assert cursor.current_col == 5  # Before "hello"


class TestTextEditor:
    """Test text editor functionality."""

    @patch.object(TextEditor, "run")
    def test_text_editor_initialization(self, mock_run):
        """Test text editor initialization."""
        editor = TextEditor("initial text")
        assert editor.lines == ["initial text"]
        mock_run.return_value = "test content"

        # The run method should return the content
        result = editor.run()
        assert result == "test content"


class TestStreamingLoops:
    """Test streaming loop functionality."""

    def test_process_chunk_text(self):
        """Test processing and wrapping text chunks."""
        chunk_text = "This is a very long line that should be wrapped to fit within the specified width"
        result = _process_chunk_text(chunk_text)

        # Should break the long line into multiple wrapped lines
        assert len(result) > 1
        assert all(line.startswith("  ") for line in result)  # Should have 2-space indentation

    def test_process_chunk_text_multiline(self):
        """Test processing multiline text chunks."""
        chunk_text = "Line 1\nLine 2\nLine 3"
        result = _process_chunk_text(chunk_text)

        # Should maintain the line breaks and add indentation
        assert len(result) == 3
        assert all(line.startswith("  ") for line in result)

    def test_process_line_with_provider_content_start(self):
        """Test processing line with provider when content starts."""
        # Create mock display context
        display_context = {
            "full_output": "",
            "started_at": time.time(),
            "session_id": "test",
            "timer": Mock(),
            "content_started": False,
            "box_displayed": False,
            "last_print_ended_with_newline": False,
            "capture_content": False,
            "response_box_started": False,
            "response_box_ended": False,
        }

        # Create mock provider that returns content
        class MockProvider:
            def _parse_stream_message(self, line, cmd, line_count, agent_config):
                return "Test content", {"test": "metadata"}

        Mock()
        mock_cmd = ["test", "cmd"]
        mock_agent_config = Mock()

        # Call the function
        _process_line_with_provider("test line", mock_cmd, display_context, MockProvider(), 0, mock_agent_config)

        # Verify content started was set
        assert display_context["content_started"] is True
        assert display_context["full_output"] == "Test content"

    def test_run_streaming_loop_with_display(self):
        """Test basic streaming loop with display."""

        # Create mock process that immediately exits to prevent timeout
        mock_process = Mock()
        mock_process.poll.return_value = 0  # Process finished immediately
        mock_stdout = Mock()
        mock_stdout.fileno.return_value = 123  # Return a valid file descriptor
        mock_process.stdout = mock_stdout
        mock_process.stdout.readline.return_value = None  # No more data to read

        mock_cmd = ["test", "cmd"]
        mock_config = Mock()
        mock_config.session_id = "test-session"
        mock_config.timeout = 10

        # Mock provider
        class MockProvider:
            def _parse_stream_message(self, line, cmd, line_count, agent_config):
                return "", None

        # Execute the function - process exits immediately, so no timeout occurs
        output, metadata = run_streaming_loop_with_display(mock_process, mock_cmd, mock_config, MockProvider())

        # Should return empty output and metadata
        assert output == ""
        assert "session_id" in metadata


class TestModeHandlers:
    """Test mode handler functions."""

    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    def test_mode_interactive_editor_success(self, mock_editor, mock_get_cli):
        """Test successful interactive editor mode."""
        # Mock the text editor to return some content
        mock_editor_instance = Mock()
        mock_editor_instance.run.return_value = "Test message"
        mock_editor.return_value = mock_editor_instance

        # Mock the CLI
        mock_cli = Mock()
        mock_cli.run_print.return_value = ("Response", {})
        mock_get_cli.return_value = mock_cli

        # Call the function
        result = mode_interactive_editor()

        # Should return success (0)
        assert result == 0
        # Should have called run_print with the content
        mock_cli.run_print.assert_called_once()

    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    def test_mode_interactive_editor_cancelled(self, mock_editor, mock_get_cli):
        """Test interactive editor mode when cancelled."""
        # Mock the text editor to return None (cancelled)
        mock_editor_instance = Mock()
        mock_editor_instance.run.return_value = None
        mock_editor.return_value = mock_editor_instance

        # Call the function
        result = mode_interactive_editor()

        # Should return success (0) as cancelled is not an error
        assert result == 0
        # Should not have called CLI since content was None
        mock_get_cli.assert_not_called()

    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    def test_mode_interactive_editor_empty(self, mock_editor, mock_get_cli):
        """Test interactive editor mode with empty content."""
        # Mock the text editor to return empty content
        mock_editor_instance = Mock()
        mock_editor_instance.run.return_value = ""
        mock_editor.return_value = mock_editor_instance

        # Call the function
        result = mode_interactive_editor()

        # Should return success (0) as empty is handled gracefully
        assert result == 0
        # Should not have called CLI since content was empty
        mock_get_cli.assert_not_called()

    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    def test_mode_interactive_editor_error(self, mock_editor, mock_get_cli):
        """Test interactive editor mode when CLI call fails."""
        # Mock the text editor to return some content
        mock_editor_instance = Mock()
        mock_editor_instance.run.return_value = "Test message"
        mock_editor.return_value = mock_editor_instance

        # Mock CLI to raise an exception
        mock_get_cli.side_effect = Exception("CLI error")

        # Call the function
        result = mode_interactive_editor()

        # Should return error (1)
        assert result == 1


class TestTimerDisplay:
    """Test timer display functionality."""

    def test_timer_display_initialization(self):
        """Test timer display initialization."""
        timer = TimerDisplay()
        assert timer.start_time is not None
        assert timer.is_running is False

    def test_timer_start_stop(self):
        """Test timer start and stop functionality."""
        timer = TimerDisplay()
        timer.start()
        assert timer.is_running is True
        timer.stop()
        assert timer.is_running is False

    def test_handle_display_cleanup(self):
        """Test display cleanup functionality."""
        mock_timer = Mock()
        mock_timer.is_running = True
        mock_timer.stop = Mock()

        _handle_display_cleanup(mock_timer)

        mock_timer.stop.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
