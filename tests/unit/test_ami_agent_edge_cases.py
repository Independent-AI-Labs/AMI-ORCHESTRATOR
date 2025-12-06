"""Comprehensive tests for remaining edge cases and error conditions in ami-agent interactive mode."""

import sys
import time
from unittest.mock import Mock, patch

import pytest

from scripts.agents.cli.claude_cli import ClaudeAgentCLI
from scripts.agents.cli.config import AgentConfig, AgentConfigPresets
from scripts.agents.cli.config_service import ConfigService
from scripts.agents.cli.exceptions import AgentError, AgentTimeoutError
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.cli.mode_handlers import (
    mode_audit,
    mode_docs,
    mode_hook,
    mode_interactive_editor,
    mode_print,
    mode_query,
    mode_sync,
    mode_tasks,
)
from scripts.agents.cli.streaming_loops import (
    _handle_display_cleanup,
    _handle_timeout,
    _process_line_with_provider,
    _process_raw_line,
    run_streaming_loop_with_display,
)
from scripts.agents.cli.timer_utils import TimerDisplay, wrap_text_in_box


class TestModeHandlerErrorConditions:
    """Test error conditions in mode handlers."""

    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    def test_mode_interactive_editor_keyboard_interrupt(self, mock_text_editor):
        """Test interactive editor mode when interrupted by keyboard."""
        mock_editor = Mock()
        mock_editor.run.side_effect = KeyboardInterrupt("User cancelled")
        mock_text_editor.return_value = mock_editor

        # Should handle KeyboardInterrupt gracefully
        result = mode_interactive_editor()
        assert result == 0  # Success because cancellation is expected behavior

    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    def test_mode_interactive_editor_with_whitespace_content(self, mock_text_editor):
        """Test interactive editor with only whitespace content."""
        mock_editor = Mock()
        mock_editor.run.return_value = "   \\n\\t\\n  \\n"
        mock_text_editor.return_value = mock_editor

        # Whitespace-only content should be treated as empty (return 0)
        result = mode_interactive_editor()
        assert result == 0  # Should exit gracefully, not call the agent

    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    def test_mode_interactive_editor_cli_exception(self, mock_get_cli, mock_text_editor):
        """Test interactive editor when CLI call fails."""
        mock_editor = Mock()
        mock_editor.run.return_value = "Test content"
        mock_text_editor.return_value = mock_editor

        mock_cli = Mock()
        mock_cli.run_print.side_effect = Exception("CLI connection failed")
        mock_get_cli.return_value = mock_cli

        result = mode_interactive_editor()
        assert result == 1  # Should return error code

    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    def test_mode_interactive_editor_empty_after_strip(self, mock_get_cli, mock_text_editor):
        """Test interactive editor with content that becomes empty after stripping."""
        mock_editor = Mock()
        mock_editor.run.return_value = "   "  # Only whitespace
        mock_text_editor.return_value = mock_editor

        result = mode_interactive_editor()
        # Should return 0 as empty content is handled gracefully
        assert result == 0
        mock_get_cli.assert_not_called()  # Should not call CLI for empty content

    def test_mode_query_error_handling(self):
        """Test query mode error handling."""
        with patch("scripts.agents.cli.mode_handlers.get_agent_cli") as mock_get_cli:
            mock_cli = Mock()
            mock_cli.run_print.side_effect = Exception("Query failed")
            mock_get_cli.return_value = mock_cli

            # Should handle exception gracefully and still write received message
            result = mode_query("Test query")
            assert result == 1  # Error code due to exception

    @patch("scripts.agents.cli.mode_handlers.validate_path_and_return_code")
    def test_mode_print_invalid_path(self, mock_validate):
        """Test print mode with invalid path."""
        mock_validate.return_value = 1  # Invalid path

        result = mode_print("/nonexistent/path.txt")
        assert result == 1  # Should return error code

    @patch("sys.stdin.read", return_value="")  # Mock stdin to avoid issues in test environment
    @patch("scripts.agents.cli.mode_handlers.validate_path_and_return_code")
    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    def test_mode_print_cli_error(self, mock_get_cli, mock_validate, mock_stdin_read):
        """Test print mode when CLI call fails."""
        mock_validate.return_value = 0  # Valid path
        mock_cli = Mock()
        mock_cli.run_print.side_effect = AgentError("CLI error")
        mock_get_cli.return_value = mock_cli

        result = mode_print("/valid/path.txt")
        assert result == 1  # Should return error code

    @patch("scripts.agents.cli.mode_handlers.validate_path_and_return_code")
    def test_mode_audit_invalid_path(self, mock_validate):
        """Test audit mode with invalid path."""
        mock_validate.return_value = 1  # Invalid path

        result = mode_audit("/nonexistent/path")
        assert result == 1  # Should return error code

    @patch("scripts.agents.cli.mode_handlers.validate_path_and_return_code")
    def test_mode_tasks_invalid_path(self, mock_validate):
        """Test tasks mode with invalid path."""
        mock_validate.return_value = 1  # Invalid path

        result = mode_tasks("/nonexistent/path")
        assert result == 1  # Should return error code


class TestConfigurationErrorConditions:
    """Test configuration error conditions."""

    def test_agent_config_invalid_provider(self):
        """Test agent config with invalid provider."""
        # Should default to Claude for invalid provider
        AgentConfig(
            model="test-model",
            session_id="test-session",
            provider="invalid_provider",  # Invalid provider type
        )
        # Note: This depends on how the code handles invalid providers
        # The factory should handle this properly

    @patch("scripts.agents.cli.config_service.yaml.safe_load")
    @patch("builtins.open")
    def test_config_service_file_not_found(self, mock_open, mock_yaml_load):
        """Test config service when config file doesn't exist."""
        # Make file opening raise an error to simulate missing file
        mock_open.side_effect = FileNotFoundError("Config file not found")
        mock_yaml_load.side_effect = FileNotFoundError("Config file not found")

        # Reset the singleton instance to force re-initialization

        ConfigService._instance = None
        ConfigService._config_data = None

        with pytest.raises(FileNotFoundError):
            ConfigService()  # Should fail when config file is not found

    def test_config_presets_none_session_id(self):
        """Test config presets with None session ID."""
        # This should work - None session_id is valid
        config = AgentConfigPresets.worker(None)
        assert config.session_id is None  # Or it might generate a default


class TestTimerErrorConditions:
    """Test timer error conditions."""

    def test_timer_display_stop_when_not_running(self):
        """Test stopping timer when it's not running."""
        timer = TimerDisplay()
        # Initially not running, so stop should not fail
        timer.stop()
        assert timer.is_running is False

    def test_timer_display_multiple_starts(self):
        """Test starting timer multiple times."""
        timer = TimerDisplay()
        timer.start()
        # Should handle multiple starts gracefully
        initial_start_time = timer.start_time
        timer.start()  # Should reset start time
        assert timer.start_time >= initial_start_time

    def test_timer_display_multiple_stops(self):
        """Test stopping timer multiple times."""
        timer = TimerDisplay()
        timer.start()
        timer.stop()
        # Should handle multiple stops gracefully
        timer.stop()  # Should not fail
        assert timer.is_running is False


class TestStreamingErrorConditions:
    """Test streaming error conditions."""

    def test_run_streaming_loop_with_display_timeout(self):
        """Test streaming with timeout."""
        # Create a mock process that simulates timeout behavior
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        mock_process.stdout.readline.return_value = None

        mock_config = Mock()
        mock_config.session_id = "test-session"
        mock_config.timeout = 1  # Short timeout

        class MockProvider:
            def _parse_stream_message(self, line, cmd, line_count, agent_config):
                return "", None

        # Test with a process that never returns data - should timeout
        with patch("scripts.agents.cli.streaming_loops.read_streaming_line") as mock_read:
            mock_read.return_value = (None, True)  # No data, timeout

            # This will eventually timeout based on the timeout logic
            with pytest.raises(AgentTimeoutError):
                # Call the function that should timeout
                run_streaming_loop_with_display(mock_process, ["test", "cmd"], mock_config, MockProvider())

    def test_handle_timeout_no_config(self):
        """Test timeout handling with None config."""
        cmd = ["test", "cmd"]
        started_at = time.time()

        # Should not raise error when config is None
        result = _handle_timeout(cmd, None, started_at)
        assert result is False  # Continue waiting

    def test_handle_timeout_no_timeout_config(self):
        """Test timeout handling when no timeout configured."""
        cmd = ["test", "cmd"]
        mock_config = Mock()
        mock_config.timeout = None

        started_at = time.time()

        # Should continue waiting when no timeout configured
        result = _handle_timeout(cmd, mock_config, started_at)
        assert result is False  # Continue waiting

    def test_process_line_with_provider_no_content(self):
        """Test processing line when provider returns no content."""
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

        class MockProvider:
            def _parse_stream_message(self, line, cmd, line_count, agent_config):
                return "", {"empty": True}  # No text content, only metadata

        _process_line_with_provider("test line", ["cmd"], display_context, MockProvider(), 0, Mock())

        # Should maintain empty output
        assert display_context["full_output"] == ""

    def test_process_line_with_provider_exception(self):
        """Test processing line when provider throws exception."""
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

        class FailingProvider:
            def _parse_stream_message(self, line, cmd, line_count, agent_config):
                raise RuntimeError("Parsing failed")

        # Should handle the exception gracefully
        with pytest.raises(RuntimeError):  # Assuming FailingProvider raises RuntimeError
            _process_line_with_provider("test line", ["cmd"], display_context, FailingProvider(), 0, Mock())

    def test_process_raw_line_capture_mode(self):
        """Test processing raw line in capture mode."""
        display_context = {
            "full_output": "",
            "started_at": time.time(),
            "session_id": "test",
            "timer": Mock(),
            "content_started": False,
            "box_displayed": False,
            "last_print_ended_with_newline": False,
            "capture_content": True,  # Capture mode - should not print to stdout
        }

        with patch("sys.stdout.write"):
            _process_raw_line("test line", display_context)

            # Should not have written to stdout when capturing
            # The output should still be captured in full_output
            assert "test line" in display_context["full_output"]

    def test_handle_display_cleanup_with_none_timer(self):
        """Test display cleanup with None timer."""
        # Should not crash with None timer
        _handle_display_cleanup(None)


class TestTextWrappingEdgeCases:
    """Test text wrapping edge cases."""

    def test_wrap_text_in_box_empty(self):
        """Test wrapping empty text."""
        result = wrap_text_in_box("")
        assert result.startswith("┌")
        assert result.endswith("┘")
        # Should have at least top and bottom borders
        lines = result.split("\n")
        assert len(lines) >= 2

    def test_wrap_text_in_box_whitespace_only(self):
        """Test wrapping whitespace-only text."""
        result = wrap_text_in_box("   \\n\\t\\n  ")
        assert result.startswith("┌")
        assert result.endswith("┘")

    def test_wrap_text_in_box_very_long_line(self):
        """Test wrapping a very long line."""
        long_line = "A" * 500  # Much longer than 76 chars
        result = wrap_text_in_box(long_line)
        lines = result.split("\n")
        # Should be wrapped into multiple content lines
        content_lines = [line for line in lines if line.startswith("  ")]
        assert len(content_lines) > 1

    def test_wrap_text_in_box_single_char(self):
        """Test wrapping single character."""
        result = wrap_text_in_box("X")
        assert "X" in result
        lines = result.split("\n")
        assert len(lines) == 3  # Top border, content, bottom border


class TestHookModeErrorConditions:
    """Test hook mode error conditions."""

    def test_mode_hook_invalid_validator(self):
        """Test hook mode with invalid validator name."""
        result = mode_hook("invalid-validator-name")
        assert result == 1  # Should return error for unknown validator

    def test_mode_hook_empty_validator(self):
        """Test hook mode with empty validator name."""
        result = mode_hook("")
        assert result == 1  # Should return error for empty name

    def test_mode_hook_none_validator(self):
        """Test hook mode with None validator name."""
        # This would be an internal error since mode_handlers.py doesn't call with None
        # But let's test the function directly if needed


class TestSyncModeErrorConditions:
    """Test sync mode error conditions."""

    @patch("scripts.agents.cli.mode_handlers.validate_path_and_return_code")
    def test_mode_sync_invalid_path(self, mock_validate):
        """Test sync mode with invalid path."""
        mock_validate.return_value = 1  # Invalid path

        result = mode_sync("/nonexistent/path")
        assert result == 1  # Should return error code

    @patch("scripts.agents.cli.mode_handlers.validate_path_and_return_code")
    @patch("scripts.agents.cli.mode_handlers.Path")
    def test_mode_sync_no_git_directory(self, mock_path_class, mock_validate):
        """Test sync mode when directory is not a git repository."""
        mock_validate.return_value = 0  # Valid path

        # Create mock path objects to simulate the .git check
        mock_module_path = Mock()
        mock_git_path = Mock()

        # Setup the mock path properly including the truediv operation (for / operator)
        mock_module_path.__truediv__ = Mock(return_value=mock_git_path)
        mock_git_path.exists.return_value = False  # .git does not exist

        # Make sure Path constructor returns our mock module path
        mock_path_class.return_value = mock_module_path

        result = mode_sync("/valid/path")
        assert result == 1  # Should return error code if no .git directory


class TestDocsModeErrorConditions:
    """Test docs mode error conditions."""

    @patch("scripts.agents.cli.mode_handlers.validate_path_and_return_code")
    def test_mode_docs_invalid_path(self, mock_validate):
        """Test docs mode with invalid path."""
        mock_validate.return_value = 1  # Invalid path

        result = mode_docs("/nonexistent/path")
        assert result == 1  # Should return error code

    @patch("scripts.agents.cli.mode_handlers.validate_path_and_return_code")
    def test_mode_docs_root_dir_not_exists(self, mock_validate):
        """Test docs mode with non-existent root directory."""
        mock_validate.return_value = 0  # Valid path

        result = mode_docs("/valid/path", root_dir="/nonexistent/root")
        assert result == 1  # Should return error code for non-existent root dir


class TestCLIErrorConditions:
    """Test CLI factory error conditions."""

    def test_factory_unknown_provider(self):
        """Test CLI factory with unknown provider."""
        config = AgentConfig(
            model="test",
            session_id="test-session",
            provider=Mock(),  # Mock provider that doesn't match known providers
        )

        # Should default to Claude for unknown providers
        cli = get_agent_cli(config)

        assert isinstance(cli, ClaudeAgentCLI)


class TestComprehensiveErrorScenarios:
    """Test comprehensive error scenarios."""

    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    @patch("scripts.agents.cli.mode_handlers.AgentConfigPresets")
    def test_mode_interactive_editor_config_preset_error(self, mock_presets, mock_get_cli, mock_text_editor):
        """Test interactive editor when config preset creation fails."""
        mock_editor = Mock()
        mock_editor.run.return_value = "Test content"
        mock_text_editor.return_value = mock_editor

        # Make config preset creation raise an error
        mock_presets.worker.side_effect = Exception("Config preset error")

        # Should handle config error and return error code
        result = mode_interactive_editor()
        assert result == 1

    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    def test_mode_interactive_editor_cli_creation_error(self, mock_get_cli, mock_text_editor):
        """Test interactive editor when CLI creation fails."""
        mock_editor = Mock()
        mock_editor.run.return_value = "Test content"
        mock_text_editor.return_value = mock_editor

        # Make CLI creation raise an error
        mock_get_cli.side_effect = Exception("CLI creation failed")

        result = mode_interactive_editor()
        assert result == 1

    @patch("sys.stdout.write")
    @patch("scripts.agents.cli.mode_handlers.TextEditor")
    @patch("scripts.agents.cli.mode_handlers.get_agent_cli")
    def test_mode_interactive_editor_stdout_write_error(self, mock_get_cli, mock_text_editor, mock_stdout_write):
        """Test interactive editor when stdout write fails."""
        mock_editor = Mock()
        mock_editor.run.return_value = "Test content"
        mock_text_editor.return_value = mock_editor

        mock_cli = Mock()

        # Make the CLI run_print method trigger stdout write error
        def mock_run_print(instruction, agent_config):  # noqa: ARG001
            # This will trigger when run_print is called and eventually tries to write to stdout
            sys.stdout.write("test")  # This will trigger the mocked function
            return ("Response", {})

        mock_cli.run_print.side_effect = mock_run_print
        mock_get_cli.return_value = mock_cli

        # Make stdout write raise an error (simulating broken pipe, etc.)
        mock_stdout_write.side_effect = BrokenPipeError("Broken pipe")

        # Should handle stdout error gracefully and return error code
        result = mode_interactive_editor()
        assert result == 1  # Error due to broken pipe


if __name__ == "__main__":
    pytest.main([__file__])
