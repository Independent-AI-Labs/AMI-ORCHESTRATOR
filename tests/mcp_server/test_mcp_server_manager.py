"""
Unit tests for the MCPServerManager class.
"""

import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

from orchestrator.mcp.mcp_server_manager import LOG_FILE, PID_FILE, MCPServerManager


class TestMCPServerManager(unittest.TestCase):
    """
    Test suite for the MCPServerManager.
    """

    def setUp(self):
        """Set up the test environment."""
        self.server_script_path = "/path/to/fake_server.py"
        self.cwd = "/path/to/fake/cwd"
        self.manager = MCPServerManager(self.server_script_path, self.cwd)

    @patch("os.path.exists")
    def test_is_running_no_pid_file(self, mock_exists):
        """Test is_running when no PID file exists."""
        mock_exists.return_value = False
        self.assertFalse(self.manager.is_running())

    @patch("builtins.open")
    @patch("os.path.exists")
    def test_read_pid_file_not_found(self, mock_exists, mock_open_file):
        """Test _read_pid when the PID file does not exist."""
        mock_exists.return_value = True
        mock_open_file.side_effect = FileNotFoundError
        self.assertIsNone(self.manager._read_pid())  # pylint: disable=protected-access

    @patch("builtins.open")
    @patch("os.path.exists")
    def test_read_pid_io_error(self, mock_exists, mock_open_file):
        """Test _read_pid with an IOError."""
        mock_exists.return_value = True
        mock_open_file.side_effect = IOError("test error")
        self.assertIsNone(self.manager._read_pid())  # pylint: disable=protected-access

    @patch("subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_start_server(self, mock_exists, mock_open_file, mock_popen):
        """Test the start_server method."""
        mock_exists.return_value = False
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        self.manager.start_server()

        mock_popen.assert_called_once()
        mock_open_file.assert_any_call(LOG_FILE, "wb")
        mock_open_file.assert_any_call(PID_FILE, "w", encoding="utf-8")
        mock_open_file().write.assert_called_once_with("12345")

    @patch("os.remove")
    @patch("orchestrator.mcp.mcp_server_manager.MCPServerManager._terminate_process_windows")
    @patch("orchestrator.mcp.mcp_server_manager.MCPServerManager._read_pid")
    @patch("os.path.exists")
    def test_stop_server_windows(self, mock_exists, mock_read_pid, mock_terminate, mock_remove):
        """Test the stop_server method on Windows."""
        sys.platform = "win32"
        mock_read_pid.return_value = 12345
        mock_exists.return_value = True

        self.manager.stop_server()

        mock_terminate.assert_called_once_with(12345)
        mock_remove.assert_called_once_with(PID_FILE)


if __name__ == "__main__":
    unittest.main()
