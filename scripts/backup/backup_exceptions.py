"""Backup exceptions module.

Custom exceptions for backup operations.
"""

class BackupError(Exception):
    """Base exception for backup operations"""


class BackupConfigError(BackupError):
    """Configuration or validation errors"""


class ArchiveError(BackupError):
    """Zip archive creation errors"""


class UploadError(BackupError):
    """Google Drive upload errors"""