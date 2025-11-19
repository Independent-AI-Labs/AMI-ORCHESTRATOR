"""Unit tests for backup secondary module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.backup.backup_secondary import copy_to_secondary_backup


class TestCopyToSecondaryBackup:
    """Tests for copy_to_secondary_backup function with minimal mocking."""

    @patch("subprocess.run")
    @patch("shutil.copy2")
    @patch("pathlib.Path.exists", return_value=True)  # All paths exist
    @patch("pathlib.Path.is_mount", return_value=False)  # No paths are mounts
    @patch("os.listdir", return_value=[])  # Empty directory listing for common mount points
    async def test_copy_to_secondary_backup_basic(self, mock_listdir, mock_is_mount, mock_exists, mock_copy2, mock_subprocess):
        """Basic test for copy_to_secondary_backup with minimal mocking."""
        # Create a temporary archive file path in the secure temp directory
        temp_path = Path(tempfile.gettempdir()) / "test-backup.tar.zst"

        # Mock subprocess calls to return empty/no results to avoid complex drive detection
        mock_result = MagicMock()
        mock_result.stdout = ""  # No drives found
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Function should complete without errors, even if no drives are found
        await copy_to_secondary_backup(temp_path)

        # Verify that subprocess was called (the function tried to find drives)
        mock_subprocess.assert_called()

        # copy2 should not be called since no drives were found
        mock_copy2.assert_not_called()
