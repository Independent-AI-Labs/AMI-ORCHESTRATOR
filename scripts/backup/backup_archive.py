"""Backup archive module.

Handles creating compressed tar.zst archives of the repository.
"""

import asyncio
import contextlib
import os
import shutil
import sys
import tarfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import zstandard as zstd
from loguru import logger

# Add orchestrator root to path for imports
# Use sys.argv[0] if __file__ is not available (e.g., when running with string-based execution)
script_path = Path(__file__) if "__file__" in globals() else Path(sys.argv[0])
_repo_root = next((p for p in script_path.resolve().parents if (p / "base").exists()), None)
if not _repo_root:
    raise RuntimeError("Unable to locate AMI orchestrator root")
sys.path.insert(0, str(_repo_root))

from scripts.backup.backup_exceptions import ArchiveError

def _create_archive_filter(exclude_patterns: list[str]) -> Callable[[Any], Any | None]:
    """Create a tarfile filter function with exclusion patterns.

    Args:
        exclude_patterns: List of patterns to exclude from archive

    Returns:
        Filter function for tarfile.add()
    """

    def exclude_filter(tarinfo: Any) -> Any | None:
        """Filter function to exclude certain files/directories from archive."""
        # Get relative path
        path_parts = Path(tarinfo.name).parts

        # Exclude module venvs but keep root .venv
        # If .venv is not at root level (has parent directories), exclude it
        if ".venv" in path_parts and len(path_parts) > 1 and ".venv" in path_parts[1:]:
            return None

        # Exclude matching patterns
        for pattern in exclude_patterns:
            if pattern in tarinfo.name:
                return None

        return tarinfo

    return exclude_filter


def _get_archive_size_mb(archive_path: Path) -> float:
    """Get archive file size in megabytes.

    Args:
        archive_path: Path to archive file

    Returns:
        File size in MB

    Raises:
        ArchiveError: If file size cannot be determined
    """
    try:
        return archive_path.stat().st_size / (1024 * 1024)
    except OSError as e:
        raise ArchiveError(f"Failed to get file size: {e}") from e


async def create_zip_archive(root_dir: Path) -> Path:
    """Create tar.zst archive with multi-threaded compression.

    Uses zstandard compression with all available CPU cores for faster compression.
    Creates a fixed filename that will be versioned in Google Drive.

    Args:
        root_dir: Root directory to archive

    Returns:
        Path to created archive file

    Raises:
        ArchiveError: If archive creation fails
    """
    archive_name = "ami-orchestrator-backup.tar.zst"
    archive_path = root_dir / archive_name

    # Remove existing archive if present
    if archive_path.exists():
        try:
            archive_path.unlink()
            logger.info(f"Removed existing archive: {archive_name}")
        except OSError as e:
            raise ArchiveError(f"Failed to remove existing archive: {e}") from e

    logger.info(f"Creating archive: {archive_name}")
    logger.info("  Using multi-threaded zstandard compression")

    # Define exclusion patterns
    exclude_patterns = [
        "__pycache__",
        ".pyc",
        "node_modules",
        ".cache",
        ".tar.zst",
        ".zip",
        ".gcloud",
    ]

    # Create filter function
    exclude_filter = _create_archive_filter(exclude_patterns)

    try:
        # Create multi-threaded zstandard compressor
        # level=3 is default, good balance of speed/compression
        # threads=-1 means use all available CPU cores
        cctx = zstd.ZstdCompressor(level=3, threads=-1)

        logger.info("  Compression level: 3, threads: all cores")

        # Create tar.zst archive
        with (
            archive_path.open("wb") as fh,
            cctx.stream_writer(fh) as compressor,
            tarfile.open(fileobj=compressor, mode="w") as tar,
        ):
            # Add root directory with exclusion filter
            tar.add(
                root_dir,
                arcname=".",
                filter=exclude_filter,
                recursive=True,
            )

            # Add Claude transcripts directory if it exists
            claude_dir = Path.home() / ".claude"
            if claude_dir.exists():
                logger.info(f"Adding Claude directory: {claude_dir}")
                tar.add(
                    claude_dir,
                    arcname=".claude",
                    filter=exclude_filter,
                    recursive=True,
                )
            else:
                logger.info("Claude directory does not exist, skipping: ~/.claude")

            # Add Qwen directory if it exists
            qwen_dir = Path.home() / ".qwen"
            if qwen_dir.exists():
                logger.info(f"Adding Qwen directory: {qwen_dir}")
                tar.add(
                    qwen_dir,
                    arcname=".qwen",
                    filter=exclude_filter,
                    recursive=True,
                )
            else:
                logger.info("Qwen directory does not exist, skipping: ~/.qwen")

    except (OSError, tarfile.TarError, zstd.ZstdError) as e:
        # Clean up partial archive if it exists
        if archive_path.exists():
            with contextlib.suppress(OSError):
                archive_path.unlink()
        raise ArchiveError(f"Archive creation failed: {e}") from e

    # Verify archive was created
    if not archive_path.exists():
        raise ArchiveError("Archive file was not created")

    # Get file size
    file_size_mb = _get_archive_size_mb(archive_path)

    logger.info(f"✓ Archive created: {archive_path}")
    logger.info(f"  Size: {file_size_mb:.1f} MB")

    return archive_path