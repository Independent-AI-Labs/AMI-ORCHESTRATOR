"""Unit tests for backup upload module."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from scripts.backup.backup_config import BackupConfig
from scripts.backup.backup_exceptions import UploadError
from scripts.backup.backup_upload import _parse_upload_result, upload_to_gdrive


class TestParseUploadResult:
    """Unit tests for _parse_upload_result function."""

    def test_parse_upload_result_success(self):
        """_parse_upload_result parses successful upload result."""
        stdout = json.dumps({"success": True, "file_id": "12345", "name": "test.zip", "link": "https://drive.google.com/file/d/12345"})

        result = _parse_upload_result(stdout)

        assert result["success"] is True
        assert result["file_id"] == "12345"
        assert result["name"] == "test.zip"
        assert result["link"] == "https://drive.google.com/file/d/12345"

    def test_parse_upload_result_empty_stdout(self):
        """_parse_upload_result raises UploadError for empty stdout."""
        try:
            _parse_upload_result("")
            raise AssertionError("Expected UploadError was not raised")
        except UploadError as e:
            assert "no output" in str(e).lower()

    def test_parse_upload_result_invalid_json(self):
        """_parse_upload_result raises UploadError for invalid JSON."""
        try:
            _parse_upload_result("invalid json")
            raise AssertionError("Expected UploadError was not raised")
        except UploadError as e:
            assert "Failed to parse upload result" in str(e)

    def test_parse_upload_result_failure(self):
        """_parse_upload_result raises UploadError for failed upload."""
        stdout = json.dumps({"success": False, "error": "Upload failed"})

        try:
            _parse_upload_result(stdout)
            raise AssertionError("Expected UploadError was not raised")
        except UploadError as e:
            assert "Upload failed" in str(e)

    def test_parse_upload_result_missing_file_id(self):
        """_parse_upload_result raises UploadError when file_id is missing."""
        stdout = json.dumps(
            {
                "success": True
                # No file_id field
            }
        )

        try:
            _parse_upload_result(stdout)
            raise AssertionError("Expected UploadError was not raised")
        except UploadError as e:
            assert "no file ID returned" in str(e)


class TestUploadToGdrive:
    """Tests for upload_to_gdrive function - these would require complex mocking due to Google API dependency,
    so we focus on testing the subprocess execution and JSON parsing logic."""

    @patch("scripts.backup.backup_upload.FileSubprocess")
    async def test_upload_to_gdrive_success(self, mock_file_subprocess_class):
        """Test upload_to_gdrive with mocked subprocess (Google API calls are external)."""
        # This test still requires some mocking due to external API dependency,
        # but we minimize it to only the subprocess execution part

        # Create mock subprocess runner
        mock_subprocess_runner = AsyncMock()
        mock_file_subprocess_class.return_value = mock_subprocess_runner

        # Mock successful subprocess result
        mock_result = {
            "success": True,
            "stdout": json.dumps({"success": True, "file_id": "12345", "name": "test.tar.zst", "link": "https://drive.google.com/file/d/12345"}),
        }
        mock_subprocess_runner.run.return_value = mock_result

        # Create config for impersonation
        config = BackupConfig(Path("/test"))
        config.auth_method = "impersonation"
        config.service_account_email = "test@serviceaccount.com"
        config.root_dir = Path("/test")

        # Create a test zip path
        zip_path = Path("/test/test.tar.zst")

        # Perform the upload
        file_id = await upload_to_gdrive(zip_path, config)

        # Verify the result
        assert file_id == "12345"

        # Verify subprocess was called
        mock_subprocess_runner.run.assert_called_once()

    @patch("scripts.backup.backup_upload.FileSubprocess")
    async def test_upload_to_gdrive_subprocess_error(self, mock_file_subprocess_class):
        """Test upload_to_gdrive handles subprocess errors."""

        # Create mock subprocess runner
        mock_subprocess_runner = AsyncMock()
        mock_file_subprocess_class.return_value = mock_subprocess_runner

        # Mock failed subprocess result with JSON error
        mock_result = {"success": False, "stderr": "Upload failed", "stdout": json.dumps({"error": "Upload error"})}
        mock_subprocess_runner.run.return_value = mock_result

        # Create config
        config = BackupConfig(Path("/test"))
        config.auth_method = "impersonation"
        config.service_account_email = "test@serviceaccount.com"
        config.root_dir = Path("/test")

        # Create a test zip path
        zip_path = Path("/test/test.tar.zst")

        # Try to upload - should raise UploadError
        try:
            await upload_to_gdrive(zip_path, config)
            raise AssertionError("Expected UploadError was not raised")
        except UploadError as e:
            # The error might come from JSON parsing or general subprocess failure
            assert "Upload" in str(e)  # Check that the error message contains "Upload"
