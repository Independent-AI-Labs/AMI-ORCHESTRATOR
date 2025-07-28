"""
Unit tests for the MCPServerManager class.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

from orchestrator.mcp.mcp_server_manager import MCPServerManager


class TestMCPServerManager(unittest.TestCase):
    """
    Test suite for the MCPServerManager.
    """

    def setUp(self):
        """Set up the test environment."""
        self.server_script_path = "/path/to/fake_server.py"
        self.cwd = "/path/to/fake/cwd"
        self.manager = MCPServerManager(self.server_script_path, self.cwd)

    @patch("orchestrator.mcp.mcp_server_manager.MCPServerManager._read_pid")
    @patch("os.path.exists")
    def test_is_running_no_pid_file(self, mock_exists, mock_read_pid):
        """Test is_running when no PID file exists."""
        mock_exists.return_value = False
        mock_read_pid.return_value = None
        self.assertFalse(self.manager.is_running())

    @patch("orchestrator.mcp.mcp_server_manager.PID_FILE")
    @patch("os.path.exists")
    def test_read_pid_file_not_found(self, mock_exists, mock_pid_file):
        """Test _read_pid when the PID file does not exist."""
        mock_exists.return_value = True
        mock_pid_file.read_text.side_effect = FileNotFoundError
        self.assertIsNone(self.manager._read_pid())  # pylint: disable=protected-access

    @patch("orchestrator.mcp.mcp_server_manager.PID_FILE")
    @patch("os.path.exists")
    def test_read_pid_io_error(self, mock_exists, mock_pid_file):
        """Test _read_pid with an IOError."""
        mock_exists.return_value = True
        mock_pid_file.read_text.side_effect = OSError("test error")
        self.assertIsNone(self.manager._read_pid())  # pylint: disable=protected-access

    @patch("subprocess.Popen")
    @patch("orchestrator.mcp.mcp_server_manager.LOG_FILE")
    @patch("orchestrator.mcp.mcp_server_manager.PID_FILE")
    @patch("os.path.exists")
    @patch("orchestrator.mcp.mcp_server_manager.subprocess.run")
    def test_start_server(self, mock_subprocess_run, mock_exists, mock_pid_file, mock_log_file, mock_popen):
        """Test the start_server method."""
        mock_exists.return_value = False
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        mock_log_file.open.return_value = MagicMock()  # Mock the file object returned by .open()
        mock_subprocess_run.return_value = MagicMock(stdout="", returncode=1)  # Mock subprocess.run for is_running to return False

        self.manager.start_server()

        mock_popen.assert_called_once()
        mock_log_file.open.assert_called_once_with("wb")
        mock_pid_file.write_text.assert_called_once_with("12345", encoding="utf-8")

    @patch("orchestrator.mcp.mcp_server_manager.PID_FILE")
    @patch("orchestrator.mcp.mcp_server_manager.MCPServerManager._terminate_process_windows")
    @patch("orchestrator.mcp.mcp_server_manager.MCPServerManager._read_pid")
    @patch("os.path.exists")
    def test_stop_server_windows(self, mock_exists, mock_read_pid, mock_terminate, mock_pid_file):
        """Test the stop_server method on Windows."""
        sys.platform = "win32"
        mock_read_pid.return_value = 12345
        mock_exists.return_value = True

        self.manager.stop_server()

        mock_terminate.assert_called_once_with(12345)
        mock_pid_file.unlink.assert_called_once()


if __name__ == "__main__":
    unittest.main()
