"""Backup utilities module.

Contains various utility functions for the backup process.
"""

import asyncio
import os
import sys
from pathlib import Path

from loguru import logger

# Add orchestrator root to path for imports
_repo_root = next((p for p in Path(__file__).resolve().parents if (p / "base").exists()), None)
if not _repo_root:
    raise RuntimeError("Unable to locate AMI orchestrator root")
sys.path.insert(0, str(_repo_root))

from scripts.backup.backup_exceptions import BackupError

async def cleanup_local_zip(zip_path: Path, keep_local: bool = False) -> None:
    """Remove local zip file after upload.

    Args:
        zip_path: Path to zip file
        keep_local: If True, keep the local file

    Raises:
        BackupError: If file deletion fails
    """
    if keep_local:
        logger.info(f"✓ Local backup kept at: {zip_path}")
    else:
        try:
            zip_path.unlink()
            logger.info(f"✓ Local backup removed: {zip_path}")
        except OSError as e:
            raise BackupError(f"Failed to delete local backup: {e}") from e