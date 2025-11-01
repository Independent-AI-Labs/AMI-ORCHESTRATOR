"""Tests for agent CLI timeout handling and hung process termination.

These tests verify that hung Claude CLI processes are properly terminated
when they exceed their timeout, preventing 8+ hour hangs.
"""

import signal
import subprocess
from unittest.mock import MagicMock, patch

import pytest

try:
    from scripts.automation.agent_cli import AgentConfig, ClaudeAgentCLI
except ImportError:
    AgentConfig = None
    ClaudeAgentCLI = None


class TestTimeoutEnforcement:
    """Tests that timeout is enforced and hung processes are killed."""

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_subprocess_run_uses_process_group(self):
        """subprocess.Popen creates new session for process group management."""
        cli = ClaudeAgentCLI()

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("success", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            config = AgentConfig(model="test", session_id="test-session", timeout=30)
            result = cli.run_print(instruction="test", agent_config=config)

            # Verify start_new_session=True for process group
            assert mock_popen.call_args[1]["start_new_session"] is True
            # Verify stdout returned on success
            assert result == ("success", None)

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_timeout_triggers_sigkill(self):
        """Timeout triggers SIGKILL to force-terminate hung process."""
        from scripts.automation.agent_cli import AgentTimeoutError

        cli = ClaudeAgentCLI()

        # Simulate timeout
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.communicate.side_effect = subprocess.TimeoutExpired(cmd=["claude"], timeout=5)

        with patch("subprocess.Popen", return_value=mock_process), patch("os.killpg") as mock_killpg, patch("os.getpgid", return_value=12345):
            config = AgentConfig(model="test", session_id="test-session", timeout=5)

            # Verify AgentTimeoutError raised
            with pytest.raises(AgentTimeoutError) as exc_info:
                cli.run_print(instruction="test", agent_config=config)

            # Verify timeout details in exception
            assert exc_info.value.timeout == 5
            assert exc_info.value.duration is not None

            # Verify SIGKILL sent to process group
            mock_killpg.assert_called_once_with(12345, signal.SIGKILL)

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_timeout_value_passed_to_subprocess(self):
        """AgentConfig timeout is passed to process.communicate()."""
        cli = ClaudeAgentCLI()

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("ok", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            config = AgentConfig(model="test", session_id="test-session", timeout=180)
            result = cli.run_print(instruction="test", agent_config=config)

            # Verify timeout parameter passed to communicate()
            assert mock_process.communicate.call_args[1]["timeout"] == 180
            assert result == ("ok", None)

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_none_timeout_allows_unlimited_runtime(self):
        """timeout=None allows process to run without time limit."""
        cli = ClaudeAgentCLI()

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("ok", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            config = AgentConfig(model="test", session_id="test-session", timeout=None)
            result = cli.run_print(instruction="test", agent_config=config)

            # Verify no timeout passed to communicate()
            assert mock_process.communicate.call_args[1]["timeout"] is None
            assert result == ("ok", None)


class TestTimeoutLogging:
    """Tests that timeout events are properly logged."""

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_timeout_logs_error(self):
        """Timeout logs error with timeout duration."""
        from scripts.automation.agent_cli import AgentTimeoutError

        cli = ClaudeAgentCLI()

        mock_process = MagicMock()
        mock_process.pid = 99999
        mock_process.communicate.side_effect = subprocess.TimeoutExpired(cmd=["claude"], timeout=60)

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("os.killpg"),
            patch("os.getpgid", return_value=99999),
            patch.object(cli.logger, "error") as mock_error,
        ):
            config = AgentConfig(model="test", session_id="test-session", timeout=60)

            with pytest.raises(AgentTimeoutError):
                cli.run_print(instruction="test", agent_config=config)

            # Verify timeout logged
            mock_error.assert_called_once()
            assert "agent_print_timeout" in str(mock_error.call_args)
            assert "timeout" in str(mock_error.call_args)

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_kill_success_logs_info(self):
        """Successful SIGKILL logs info with PID."""
        from scripts.automation.agent_cli import AgentTimeoutError

        cli = ClaudeAgentCLI()

        mock_process = MagicMock()
        mock_process.pid = 54321
        mock_process.communicate.side_effect = subprocess.TimeoutExpired(cmd=["claude"], timeout=15)

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("os.killpg"),
            patch("os.getpgid", return_value=54321),
            patch.object(cli.logger, "info") as mock_info,
        ):
            config = AgentConfig(model="test", session_id="test-session", timeout=15)

            with pytest.raises(AgentTimeoutError):
                cli.run_print(instruction="test", agent_config=config)

            # Verify kill logged
            kill_calls = [call for call in mock_info.call_args_list if "agent_print_killed" in str(call)]
            assert len(kill_calls) == 1
            assert "54321" in str(kill_calls[0])

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_kill_failure_logs_error(self):
        """Failed SIGKILL with non-recoverable error raises AgentProcessKillError."""
        from scripts.automation.agent_cli import AgentProcessKillError

        cli = ClaudeAgentCLI()

        mock_process = MagicMock()
        mock_process.pid = 11111
        mock_process.communicate.side_effect = subprocess.TimeoutExpired(cmd=["claude"], timeout=20)

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("os.killpg", side_effect=PermissionError("Operation not permitted")),
            patch("os.getpgid", return_value=11111),
            patch.object(cli.logger, "error") as mock_error,
        ):
            config = AgentConfig(model="test", session_id="test-session", timeout=20)

            # Verify AgentProcessKillError raised on permission error
            with pytest.raises(AgentProcessKillError) as exc_info:
                cli.run_print(instruction="test", agent_config=config)

            assert exc_info.value.pid == 11111
            assert "Operation not permitted" in exc_info.value.reason

            # Verify error logged
            mock_error.assert_called()
            assert any("agent_print_kill_failed" in str(call) for call in mock_error.call_args_list)
