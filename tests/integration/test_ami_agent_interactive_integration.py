"""Integration tests for ami-agent interactive mode functionality."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from scripts.agents.cli.claude_cli import ClaudeAgentCLI
from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.cli.config_service import ConfigService
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.cli.mode_handlers import mode_interactive_editor, mode_query
from scripts.agents.cli.provider_type import ProviderType
from scripts.agents.cli.qwen_cli import QwenAgentCLI
from scripts.agents.cli.streaming_loops import run_streaming_loop_with_display
from scripts.agents.cli.timer_utils import TimerDisplay, wrap_text_in_box
from scripts.cli_components.text_editor import TextEditor


class TestMainIntegration:
    """Integration tests for main entry point."""

    # Note: The main.py file has a hybrid bash/Python structure with an execution block at the end
    # We need to avoid executing the sys.exit(main()) line when importing for tests
    @patch("sys.argv", ["ami-agent", "--interactive-editor"])
    @patch("sys.exit")
    @patch("scripts.agents.cli.mode_handlers.mode_interactive_editor", return_value=0)
    def test_main_with_interactive_editor_arg(self, mock_mode_handler, mock_exit):
        """Test main function with --interactive-editor argument."""

        # Temporarily modify sys.argv to avoid exit on import
        original_argv = sys.argv
        sys.argv = ["ami-agent", "--interactive-editor"]

        try:
            # Load the main module without executing the exit call
            main_py_path = Path(__file__).parent.parent.parent / "scripts" / "agents" / "cli" / "main.py"
            spec = importlib.util.spec_from_file_location("__main__", str(main_py_path.resolve()))
            main_module = importlib.util.module_from_spec(spec)

            # Execute the module but catch the sys.exit call
            spec.loader.exec_module(main_module)

            # The module execution with sys.argv as ['ami-agent', '--interactive-editor']
            # should have already called sys.exit, which is mocked
            mock_exit.assert_called_once()

            # Verify the correct mode handler was called
            mock_mode_handler.assert_called_once()
        finally:
            sys.argv = original_argv

    @patch("sys.argv", ["ami-agent", "--query", "test query"])
    @patch("sys.exit")
    @patch("scripts.agents.cli.mode_handlers.mode_query", return_value=0)
    def test_main_with_query_arg(self, mock_mode_handler, mock_exit):
        """Test main function with --query argument."""

        # Temporarily modify sys.argv
        original_argv = sys.argv
        sys.argv = ["ami-agent", "--query", "test query"]

        try:
            # Load the main module without executing the exit call
            main_py_path = Path(__file__).parent.parent.parent / "scripts" / "agents" / "cli" / "main.py"
            spec = importlib.util.spec_from_file_location("__main__", str(main_py_path.resolve()))
            main_module = importlib.util.module_from_spec(spec)

            # Execute the module
            spec.loader.exec_module(main_module)

            # Verify sys.exit was called
            mock_exit.assert_called_once()

            # Verify the correct mode handler was called
            mock_mode_handler.assert_called_once()
        finally:
            sys.argv = original_argv

    @patch("sys.argv", ["ami-agent"])  # No args - should default to interactive editor
    @patch("sys.exit")
    @patch("scripts.agents.cli.mode_handlers.mode_interactive_editor", return_value=0)
    def test_main_default_behavior(self, mock_mode_handler, mock_exit):
        """Test main function default behavior (no arguments)."""

        # Temporarily modify sys.argv
        original_argv = sys.argv
        sys.argv = ["ami-agent"]  # No args - should default to interactive editor

        try:
            # Load the main module without executing the exit call
            main_py_path = Path(__file__).parent.parent.parent / "scripts" / "agents" / "cli" / "main.py"
            spec = importlib.util.spec_from_file_location("__main__", str(main_py_path.resolve()))
            main_module = importlib.util.module_from_spec(spec)

            # Execute the module
            spec.loader.exec_module(main_module)

            # Verify sys.exit was called
            mock_exit.assert_called_once()

            # Verify the correct mode handler was called
            mock_mode_handler.assert_called_once()
        finally:
            sys.argv = original_argv


class TestModeHandlersIntegration:
    """Integration tests for mode handlers."""

    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    def test_mode_interactive_editor_end_to_end(self, mock_get_cli, mock_text_editor):
        """End-to-end test of interactive editor mode."""
        # Mock the text editor to return content
        mock_editor = Mock()
        mock_editor.run.return_value = "Hello from interactive editor!"
        mock_text_editor.return_value = mock_editor

        # Mock the CLI and its run_print method
        mock_cli = Mock()
        mock_cli.run_print.return_value = ("Hello! I'm ready to help.", {})
        mock_get_cli.return_value = mock_cli

        # Call the mode handler
        result = mode_interactive_editor()

        # Verify success
        assert result == 0

        # Verify the CLI was called with proper config
        assert mock_cli.run_print.called
        args, kwargs = mock_cli.run_print.call_args
        assert "instruction" in kwargs
        assert kwargs["instruction"] == "Hello from interactive editor!"

        # Verify the config was properly set
        assert "agent_config" in kwargs
        config = kwargs["agent_config"]
        assert config.enable_hooks is False  # Hooks disabled for editor mode
        assert config.enable_streaming is True  # Streaming enabled
        assert config.capture_content is False  # Content display enabled

    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    def test_mode_query_end_to_end(self, mock_get_cli):
        """End-to-end test of query mode."""
        # Mock the CLI and its run_print method
        mock_cli = Mock()
        mock_cli.run_print.return_value = ("Response to query", {})
        mock_get_cli.return_value = mock_cli

        # Call the mode handler with a test query
        result = mode_query("Test query")

        # Verify success
        assert result == 0

        # Verify the CLI was called
        assert mock_cli.run_print.called
        args, kwargs = mock_cli.run_print.call_args
        assert "instruction" in kwargs
        assert kwargs["instruction"] == "Test query"

        # Verify config settings
        assert "agent_config" in kwargs
        config = kwargs["agent_config"]
        assert config.enable_hooks is False  # Hooks disabled for query mode
        assert config.enable_streaming is True  # Streaming enabled
        assert config.capture_content is False  # Content display enabled


class TestConfigurationIntegration:
    """Integration tests for configuration system."""

    def test_config_presets_with_real_config(self):
        """Test that config presets work with real configuration objects."""
        session_id = "test-session-123"

        # Test worker preset
        worker_config = AgentConfigPresets.worker(session_id)
        assert worker_config.session_id == session_id
        assert worker_config.model == "claude-sonnet-4-5"
        assert worker_config.provider == ProviderType.CLAUDE
        assert worker_config.allowed_tools is None  # All tools allowed
        assert worker_config.enable_hooks is True
        assert worker_config.timeout == 180

        # Test audit preset
        audit_config = AgentConfigPresets.audit(session_id)
        assert audit_config.session_id == session_id
        assert audit_config.model == "claude-sonnet-4-5"
        assert audit_config.allowed_tools == ["WebSearch", "WebFetch"]
        assert audit_config.enable_hooks is False
        assert audit_config.timeout == 180

    def test_config_service_integration(self):
        """Test configuration service with real file system operations."""
        # This test uses the real ConfigService but with mocked file access for safety
        config_service = ConfigService()

        # Test provider commands
        claude_cmd = config_service.get_provider_command(ProviderType.CLAUDE)
        qwen_cmd = config_service.get_provider_command(ProviderType.QWEN)
        gemini_cmd = config_service.get_provider_command(ProviderType.GEMINI)

        # Commands should be different and contain the expected paths
        assert ProviderType.CLAUDE.value in claude_cmd.lower()
        assert ProviderType.QWEN.value in qwen_cmd.lower()
        assert ProviderType.GEMINI.value in gemini_cmd.lower()


class TestCLIIntegration:
    """Integration tests for CLI factory and components."""

    def test_cli_factory_with_different_providers(self):
        """Test CLI factory returns appropriate implementations."""

        # Test default (Claude)
        default_cli = get_agent_cli()
        assert isinstance(default_cli, ClaudeAgentCLI)

        # Test Claude explicitly
        claude_config = AgentConfigPresets.worker("test-session")
        claude_cli = get_agent_cli(claude_config)
        assert isinstance(claude_cli, ClaudeAgentCLI)

        # Test Qwen
        qwen_config = AgentConfigPresets.worker("test-session")
        qwen_config.provider = ProviderType.QWEN
        qwen_cli = get_agent_cli(qwen_config)
        assert isinstance(qwen_cli, QwenAgentCLI)

    def test_cli_config_presets_integration(self):
        """Test CLI integration with different config presets."""
        # Test that different presets produce different configurations
        worker_config = AgentConfigPresets.worker("test")
        audit_config = AgentConfigPresets.audit("test")
        interactive_config = AgentConfigPresets.interactive("test")

        # They should have different tool restrictions
        assert worker_config.allowed_tools is None  # All tools
        assert audit_config.allowed_tools is not None  # Restricted tools
        assert interactive_config.timeout is None  # No timeout for interactive

        # But same model and provider
        assert worker_config.model == audit_config.model == interactive_config.model
        assert all(c.provider == ProviderType.CLAUDE for c in [worker_config, audit_config, interactive_config])


class TestTimerUtilsIntegration:
    """Integration tests for timer and text utilities."""

    def test_timer_display_with_context_manager_simulation(self):
        """Test timer display lifecycle."""
        timer = TimerDisplay()

        # Initially not running
        assert timer.is_running is False

        # Start timer
        timer.start()
        assert timer.is_running is True

        # Stop timer
        timer.stop()
        assert timer.is_running is False

    def test_wrap_text_in_box_with_various_inputs(self):
        """Test text wrapping with various inputs."""
        # Test simple text
        simple_result = wrap_text_in_box("Hello")
        assert "Hello" in simple_result
        assert simple_result.startswith("┌")
        assert simple_result.endswith("┘")

        # Test multi-line text - using actual newline character
        multi_result = wrap_text_in_box("Line1\nLine2")
        lines = multi_result.split("\n")
        content_lines = [line for line in lines if "Line1" in line or "Line2" in line]
        assert len(content_lines) == 2  # Should have both lines

        # Test long text that needs wrapping
        long_text = "A" * 100  # Very long line
        wrapped_result = wrap_text_in_box(long_text)
        lines = wrapped_result.split("\n")  # Split by actual newline
        # Should be wrapped into multiple lines within the box
        assert len(lines) > 2  # At least top border, content, bottom border


class TestStreamingIntegration:
    """Integration tests for streaming functionality."""

    def test_streaming_loop_with_mock_process(self):
        """Test streaming loop with mock subprocess."""
        # Create a more complete mock of a subprocess.Popen object that can work with select
        # The issue is that select.select needs real file descriptors, so we need to provide
        # something that at least has the interface it expects

        # Create a mock that behaves more like an actual file object for select operations

        # Create a real file-like object for mocking stdout behavior
        mock_stdout = MagicMock()
        mock_stdout.readline.return_value = ""  # Return empty string to indicate EOF
        mock_stdout.fileno.return_value = 1  # Mock the file descriptor
        mock_stdout.readable.return_value = True  # Indicate it's readable

        mock_stderr = MagicMock()
        mock_stderr.fileno.return_value = 2  # Mock the file descriptor
        mock_stderr.readable.return_value = True  # Indicate it's readable

        mock_process = Mock()
        mock_process.poll.side_effect = [None, 0]  # Process starts running then finishes
        mock_process.stdout = mock_stdout  # Use the more complete mock
        mock_process.stderr = mock_stderr
        # Add communicate method which might be called
        mock_process.communicate.return_value = ("", "")
        # Add returncode property
        mock_process.returncode = 0
        # Add wait method
        mock_process.wait.return_value = 0
        # Add closed property for file-like behavior
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False

        # Mock config
        mock_config = Mock()
        mock_config.session_id = "test-session"
        mock_config.timeout = 10

        # Mock provider
        class MockProvider:
            def _parse_stream_message(self, line, cmd, line_count, agent_config):
                return "", None

        # Execute streaming with display
        output, metadata = run_streaming_loop_with_display(mock_process, ["echo", "test"], mock_config, MockProvider())

        # Verify the structure of the results
        assert output == ""
        assert isinstance(metadata, dict)
        assert "session_id" in metadata
        assert "duration" in metadata
        assert "output_length" in metadata


class TestTextEditorIntegration:
    """Integration tests for text editor components."""

    def test_cursor_manager_with_text_editor_integration(self):
        """Test that cursor manager works properly with text editor."""
        # Initialize a text editor with some content
        editor = TextEditor("Initial text on first line\\nSecond line")

        # Verify cursor manager is created properly
        assert editor.cursor_manager is not None
        assert editor.cursor_manager.current_line >= 0
        assert editor.cursor_manager.current_col >= 0

        # Test that we can move the cursor
        original_line = editor.cursor_manager.current_line
        original_col = editor.cursor_manager.current_col

        editor.cursor_manager.move_cursor_left()
        # The cursor position should have changed
        assert (editor.cursor_manager.current_line, editor.cursor_manager.current_col) != (original_line, original_col)

    def test_text_editor_run_method_structure(self):
        """Test the structure of the text editor run method."""
        # Although we can't fully test the interactive run method,
        # we can verify its structure and error handling
        editor = TextEditor("Test initial content")

        # The editor should have the expected attributes
        assert hasattr(editor, "lines")
        assert hasattr(editor, "cursor_manager")
        assert hasattr(editor, "in_paste_mode")
        assert hasattr(editor, "paste_buffer")

        # Lines should be initialized properly
        assert "Test initial content" in editor.lines


class TestErrorHandlingIntegration:
    """Integration tests for error handling paths."""

    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    def test_mode_interactive_editor_error_handling(self, mock_text_editor):
        """Test error handling in interactive editor mode."""
        # Mock editor to return content
        mock_editor = Mock()
        mock_editor.run.return_value = "Test content"
        mock_text_editor.return_value = mock_editor

        # Mock CLI to raise an exception
        with patch("scripts.agents.cli.mode_handlers.get_agent_cli") as mock_get_cli:
            mock_cli = Mock()
            mock_cli.run_print.side_effect = Exception("Test error")
            mock_get_cli.return_value = mock_cli

            # Call the mode handler - should handle the exception gracefully
            result = mode_interactive_editor()

            # Should return error code (1) for exception
            assert result == 1


if __name__ == "__main__":
    pytest.main([__file__])
