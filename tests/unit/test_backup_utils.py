"""Unit tests for backup utilities module."""

from pathlib import Path
from unittest.mock import patch

from scripts.backup.backup_exceptions import BackupError
from scripts.backup.backup_utils import cleanup_local_zip


class TestCleanupLocalZip:
    """Tests for cleanup_local_zip function using real file operations."""

    async def test_cleanup_local_zip_keep_file(self, tmp_path):
        """cleanup_local_zip keeps file when keep_local=True."""
        # Create a test file
        test_file = tmp_path / "test.zip"
        test_file.write_text("test content")

        # Verify file exists before
        assert test_file.exists()

        # Call cleanup with keep_local=True
        await cleanup_local_zip(test_file, keep_local=True)

        # Verify file still exists
        assert test_file.exists()
        assert test_file.read_text() == "test content"

    async def test_cleanup_local_zip_delete_file(self, tmp_path):
        """cleanup_local_zip deletes file when keep_local=False."""
        # Create a test file
        test_file = tmp_path / "test.zip"
        test_file.write_text("test content")

        # Verify file exists before
        assert test_file.exists()

        # Call cleanup with keep_local=False
        await cleanup_local_zip(test_file, keep_local=False)

        # Verify file is deleted
        assert not test_file.exists()

    async def test_cleanup_local_zip_delete_missing_file(self, tmp_path):
        """cleanup_local_zip raises BackupError when file missing and keep_local=False."""
        # Use a path that doesn't exist
        missing_file = tmp_path / "missing.zip"

        try:
            await cleanup_local_zip(missing_file, keep_local=False)
            raise AssertionError("Expected BackupError was not raised")
        except BackupError as e:
            assert "Failed to delete local backup" in str(e)

    async def test_cleanup_local_zip_permission_error(self, tmp_path):
        """cleanup_local_zip raises BackupError on permission error."""
        # This is harder to test with real files without changing system permissions,
        # so we keep the original approach that was working

        # Create a test file
        test_file = tmp_path / "test.zip"
        test_file.write_text("test content")

        # Make the file read-only to cause a permission error
        test_file.chmod(0o444)  # Read-only

        # Temporarily make it writable for cleanup after test
        try:
            # Try to delete - this should cause an error when we try to unlink
            with patch.object(Path, "unlink", side_effect=PermissionError("Permission denied")):
                try:
                    await cleanup_local_zip(test_file, keep_local=False)
                    raise AssertionError("Expected BackupError was not raised")
                except BackupError as e:
                    assert "Failed to delete local backup" in str(e)
        finally:
            # Make the file writable again for cleanup
            test_file.chmod(0o644)
