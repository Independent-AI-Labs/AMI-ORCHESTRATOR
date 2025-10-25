#!/usr/bin/env bash
"""'exec "$(dirname "$0")/../.venv/bin/python" "$0" "$@" #"""

"""Backup AMI Orchestrator to Google Drive.

Creates a timestamped tar.zst archive (multi-threaded zstandard compression) of the entire
repository and uploads it to Google Drive. Supports two authentication methods (in order of preference):

1. Service Account Impersonation (RECOMMENDED - No keys on disk)
2. Service Account Keys (Fallback - Security risk if leaked)

Required packages (install separately):
    ami-uv add google-auth==2.41.1
    ami-uv add google-api-python-client==2.185.0
    ami-uv add zstandard>=0.23.0

Authentication Setup:

OPTION 1: Service Account Impersonation (Recommended)
    Prerequisites:
        1. Install gcloud CLI
        2. Authenticate: gcloud auth application-default login
        3. Grant impersonation permission:
           gcloud iam service-accounts add-iam-policy-binding \\
             SERVICE_ACCOUNT_EMAIL \\
             --member="user:YOUR_EMAIL" \\
             --role="roles/iam.serviceAccountTokenCreator"

    Configuration in .env:
        GDRIVE_SERVICE_ACCOUNT_EMAIL=backup@project.iam.gserviceaccount.com  # Required
        GDRIVE_BACKUP_FOLDER_ID=folder-id                                    # Optional

OPTION 2: Service Account Keys (Less secure fallback)
    ⚠️  WARNING: Keys pose security risk if leaked. Use Option 1 if possible.

    Prerequisites:
        1. Create service account in Google Cloud Console
        2. Download JSON key file
        3. Store securely outside git (chmod 600)

    Configuration in .env:
        GDRIVE_CREDENTIALS_FILE=/path/to/service-account.json  # Required
        GDRIVE_BACKUP_FOLDER_ID=folder-id                      # Optional

Usage:
    scripts/backup_to_gdrive.py              # Upload and delete local zip
    scripts/backup_to_gdrive.py --keep-local # Upload and keep local zip
"""

import asyncio
import contextlib
import json
import os
import sys
import tarfile
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import zstandard as zstd
from dotenv import load_dotenv
from loguru import logger

# Add orchestrator root to path for imports
_repo_root = next((p for p in Path(__file__).resolve().parents if (p / "base").exists()), None)
if not _repo_root:
    raise RuntimeError("Unable to locate AMI orchestrator root")
sys.path.insert(0, str(_repo_root))

from base.backend.workers.file_subprocess import FileSubprocess


# Custom exceptions for backup operations
class BackupError(Exception):
    """Base exception for backup operations"""


class BackupConfigError(BackupError):
    """Configuration or validation errors"""


class ArchiveError(BackupError):
    """Zip archive creation errors"""


class UploadError(BackupError):
    """Google Drive upload errors"""


def find_gcloud() -> str | None:
    """Find gcloud CLI binary (local or system).

    Checks in order:
    1. Local installation: .gcloud/google-cloud-sdk/bin/gcloud
    2. System PATH: gcloud

    Returns:
        Path to gcloud binary or None if not found
    """
    # Check for local installation first
    script_dir = Path(__file__).parent.parent
    local_gcloud = script_dir / ".gcloud" / "google-cloud-sdk" / "bin" / "gcloud"

    if local_gcloud.exists():
        return str(local_gcloud)

    # Check system PATH
    import shutil

    system_gcloud = shutil.which("gcloud")
    if system_gcloud:
        return system_gcloud

    return None


class BackupConfig:
    """Backup configuration loaded from .env"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.auth_method: str  # "impersonation" or "key"
        self.service_account_email: str | None = None
        self.credentials_file: str | None = None
        self.folder_id: str | None = None
        self.gcloud_path: str | None = None

    @classmethod
    def load(cls, root_dir: Path) -> "BackupConfig":
        """Load configuration from .env file.

        Determines authentication method based on environment variables.
        Prefers impersonation over service account keys.

        Args:
            root_dir: Root directory containing .env

        Returns:
            Loaded configuration

        Raises:
            BackupConfigError: If configuration is invalid or missing
        """
        env_path = root_dir / ".env"
        if not env_path.exists():
            raise BackupConfigError(f".env file not found at {env_path}")

        load_dotenv(env_path)

        config = cls(root_dir)

        # Check for impersonation setup (preferred)
        service_account_email = os.getenv("GDRIVE_SERVICE_ACCOUNT_EMAIL")

        if service_account_email:
            # Use service account impersonation
            config.auth_method = "impersonation"
            config.service_account_email = service_account_email

            # Find gcloud CLI
            gcloud_path = find_gcloud()
            config.gcloud_path = gcloud_path

            logger.info("Using service account impersonation (secure)")
            logger.info(f"  Service Account: {service_account_email}")

            if gcloud_path:
                if ".gcloud" in gcloud_path:
                    logger.info(f"  Using local gcloud: {gcloud_path}")
                else:
                    logger.info(f"  Using system gcloud: {gcloud_path}")
                logger.info(f"  Ensure authenticated: {gcloud_path} auth application-default login")
            else:
                logger.warning("  ⚠️  gcloud CLI not found!")
                logger.warning("  Install with: ./scripts/install_gcloud.sh")
                logger.warning("  Or install system-wide: https://cloud.google.com/sdk/docs/install")

        else:
            # Fall back to service account key file
            credentials_file = os.getenv("GDRIVE_CREDENTIALS_FILE")

            if not credentials_file:
                raise BackupConfigError(
                    "No authentication configured. Set one of:\n"
                    "  GDRIVE_SERVICE_ACCOUNT_EMAIL (recommended) for impersonation\n"
                    "  GDRIVE_CREDENTIALS_FILE for service account keys\n"
                    "\nSee script docstring for setup instructions"
                )

            # Resolve credentials path
            credentials_path = Path(credentials_file)
            if not credentials_path.is_absolute():
                credentials_path = root_dir / credentials_path

            if not credentials_path.exists():
                raise BackupConfigError(
                    f"Credentials file not found at {credentials_path}\nCreate a service account and download the JSON key from Google Cloud Console"
                )

            config.auth_method = "key"
            config.credentials_file = str(credentials_path)

            # Warn about security risk
            logger.warning("⚠️  Using service account key file (security risk)")
            logger.warning("  Consider switching to service account impersonation")
            logger.warning("  See script docstring for setup instructions")

        # Load optional folder ID
        config.folder_id = os.getenv("GDRIVE_BACKUP_FOLDER_ID")

        return config


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


def _parse_upload_result(stdout: str) -> dict[str, Any]:
    """Parse upload result from subprocess stdout.

    Args:
        stdout: JSON output from upload subprocess

    Returns:
        Parsed result dictionary with file_id, name, link

    Raises:
        UploadError: If parsing fails or upload was not successful
    """
    if not stdout:
        raise UploadError("Upload subprocess returned no output")

    try:
        upload_result = cast(dict[str, Any], json.loads(stdout))
    except json.JSONDecodeError as e:
        raise UploadError(f"Failed to parse upload result: {stdout[:200]}") from e

    if not upload_result.get("success"):
        error_msg = upload_result.get("error", "Unknown error")
        raise UploadError(f"Upload failed: {error_msg}")

    file_id = upload_result.get("file_id")
    if not file_id:
        raise UploadError("Upload succeeded but no file ID returned")

    return upload_result


async def upload_to_gdrive(zip_path: Path, config: BackupConfig) -> str:
    """Upload archive file to Google Drive using configured authentication.

    Args:
        zip_path: Path to archive file to upload
        config: Backup configuration with auth method

    Returns:
        Google Drive file ID

    Raises:
        UploadError: If upload fails
    """
    logger.info("Uploading to Google Drive...")

    # Generate authentication code based on method
    if config.auth_method == "impersonation":
        auth_code = f"""
import google.auth
from google.auth import impersonated_credentials

# Get user credentials from gcloud
try:
    source_creds, project_id = google.auth.default()
except Exception as e:
    result = {{
        "success": False,
        "error": f"Failed to get default credentials: {{e}}. "
                 "Run: gcloud auth application-default login"
    }}
    print(json.dumps(result))
    sys.exit(1)

# Impersonate service account
try:
    credentials = impersonated_credentials.Credentials(
        source_credentials=source_creds,
        target_principal=r"{config.service_account_email}",
        target_scopes=["https://www.googleapis.com/auth/drive"],
        lifetime=3600  # 1 hour
    )
except Exception as e:
    result = {{
        "success": False,
        "error": f"Failed to impersonate service account: {{e}}. "
                 "Ensure you have roles/iam.serviceAccountTokenCreator permission"
    }}
    print(json.dumps(result))
    sys.exit(1)
"""
    else:  # key-based auth
        auth_code = f"""
# Authenticate with service account key file
try:
    credentials = service_account.Credentials.from_service_account_file(
        r"{config.credentials_file}",
        scopes=["https://www.googleapis.com/auth/drive"]
    )
except Exception as e:
    result = {{
        "success": False,
        "error": f"Failed to load credentials from file: {{e}}"
    }}
    print(json.dumps(result))
    sys.exit(1)
"""

    # Build search query for existing files
    search_query = f"name = '{zip_path.name}' and trashed = false"
    if config.folder_id:
        search_query += f' and "{config.folder_id}" in parents'

    # Build file metadata for new uploads
    file_metadata: dict[str, Any] = {"name": zip_path.name}
    if config.folder_id:
        file_metadata["parents"] = [config.folder_id]

    # Create embedded Python script for upload
    upload_script = f"""
import sys
import json
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    import google.auth
    from google.auth import impersonated_credentials
except ImportError as e:
    result = {{
        "success": False,
        "error": f"Required package not installed: {{e.name}}. "
                 "Install with: ami-uv add google-auth==2.41.1 google-api-python-client==2.185.0"
    }}
    print(json.dumps(result))
    sys.exit(1)

try:
{textwrap.indent(auth_code.strip(), "    ")}

    # Build Drive API service
    service = build("drive", "v3", credentials=credentials)

    # Search for existing file with same name in folder
    existing_file_id = None
    search_query = {search_query!r}

    try:
        results = service.files().list(
            q=search_query,
            spaces='drive',
            fields='files(id, name)',
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()

        files = results.get('files', [])
        if files:
            existing_file_id = files[0]['id']
    except Exception as e:
        # If search fails, continue with create
        pass

    # Upload with resumable flag for large files
    media = MediaFileUpload(
        r"{zip_path}",
        mimetype="application/zstd",
        resumable=True
    )

    if existing_file_id:
        # Update existing file (creates new version)
        file = service.files().update(
            fileId=existing_file_id,
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True
        ).execute()
    else:
        # Create new file
        file_metadata = {file_metadata!r}

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True
        ).execute()

    # Return success result
    result = {{
        "success": True,
        "file_id": file.get("id"),
        "name": file.get("name"),
        "link": file.get("webViewLink")
    }}
    print(json.dumps(result))

except Exception as e:
    result = {{
        "success": False,
        "error": str(e),
        "error_type": type(e).__name__
    }}
    print(json.dumps(result))
    sys.exit(1)
"""

    # Run upload script using FileSubprocess
    subprocess_runner = FileSubprocess(work_dir=config.root_dir)

    # Find python executable
    python_exe = sys.executable

    try:
        result = await subprocess_runner.run(
            [python_exe, "-c", upload_script],
            timeout=1800,  # 30 min timeout for large uploads
        )
    except (TimeoutError, OSError, RuntimeError) as e:
        raise UploadError(f"Upload subprocess execution failed: {e}") from e

    if not result["success"]:
        stderr = result.get("stderr", "")
        stdout = result.get("stdout", "")

        # Try to parse JSON error from stdout
        try:
            error_json = json.loads(stdout)
            if isinstance(error_json, dict) and "error" in error_json:
                raise UploadError(f"Upload failed: {error_json['error']}")
        except (json.JSONDecodeError, KeyError):
            pass

        raise UploadError(f"Upload subprocess failed:\nSTDERR: {stderr}\nSTDOUT: {stdout[:500]}")

    # Parse result from stdout
    upload_result = _parse_upload_result(result["stdout"].strip())
    file_id = cast(str, upload_result["file_id"])

    # Log success
    logger.info("✓ Upload complete")
    logger.info(f"  File ID: {file_id}")
    logger.info(f"  Name: {upload_result.get('name')}")
    if upload_result.get("link"):
        logger.info(f"  Link: {upload_result.get('link')}")

    return file_id


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


async def run_backup(keep_local: bool) -> str:
    """Run the backup process.

    Args:
        keep_local: Whether to keep local zip after upload

    Returns:
        Google Drive file ID

    Raises:
        BackupError: If any step fails
    """
    # Find root directory
    root_dir = Path(__file__).parent.parent

    # Load configuration
    config = BackupConfig.load(root_dir)

    # Create zip archive
    zip_path = await create_zip_archive(root_dir)

    # Upload to Google Drive
    file_id = await upload_to_gdrive(zip_path, config)

    # Cleanup
    await cleanup_local_zip(zip_path, keep_local)

    return file_id


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0=success, 1=failure)
    """
    logger.info("=" * 60)
    logger.info("AMI Orchestrator Backup to Google Drive")
    logger.info("=" * 60)

    # Parse arguments
    keep_local = "--keep-local" in sys.argv

    try:
        file_id = asyncio.run(run_backup(keep_local))

        logger.info("=" * 60)
        logger.info("✓ Backup completed successfully")
        logger.info(f"  Google Drive File ID: {file_id}")
        logger.info("=" * 60)

        return 0

    except BackupConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    except ArchiveError as e:
        logger.error(f"Archive creation failed: {e}")
        return 1

    except UploadError as e:
        logger.error(f"Upload failed: {e}")
        return 1

    except BackupError as e:
        logger.error(f"Backup failed: {e}")
        return 1

    except (OSError, ValueError) as e:
        logger.error(f"System error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
