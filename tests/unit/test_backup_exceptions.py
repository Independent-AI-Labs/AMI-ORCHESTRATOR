"""Unit tests for backup exceptions module."""

from scripts.backup.backup_exceptions import ArchiveError, BackupConfigError, BackupError, UploadError


class TestBackupExceptions:
    """Unit tests for backup exception classes."""

    def test_backup_error_base_class(self):
        """BackupError is base exception class."""
        error = BackupError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_backup_config_error_inheritance(self):
        """BackupConfigError inherits from BackupError."""
        error = BackupConfigError("Config error")
        assert isinstance(error, BackupError)
        assert str(error) == "Config error"

    def test_archive_error_inheritance(self):
        """ArchiveError inherits from BackupError."""
        error = ArchiveError("Archive error")
        assert isinstance(error, BackupError)
        assert str(error) == "Archive error"

    def test_upload_error_inheritance(self):
        """UploadError inherits from BackupError."""
        error = UploadError("Upload error")
        assert isinstance(error, BackupError)
        assert str(error) == "Upload error"

    def test_exception_raising(self):
        """Backup exceptions can be raised."""
        try:
            raise BackupConfigError("Configuration issue")
        except BackupConfigError as e:
            assert str(e) == "Configuration issue"

        try:
            raise ArchiveError("Archive issue")
        except ArchiveError as e:
            assert str(e) == "Archive issue"
