"""Backup main module.

Contains the main backup execution logic and CLI entry point.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

from loguru import logger

from typing import cast

# Add orchestrator root to path for imports
# Use sys.argv[0] if __file__ in globals() else Path(sys.argv[0])
script_path = Path(__file__) if "__file__" in globals() else Path(sys.argv[0])
_repo_root = next((p for p in script_path.resolve().parents if (p / "base").exists()), None)
if not _repo_root:
    raise RuntimeError("Unable to locate AMI orchestrator root")
sys.path.insert(0, str(_repo_root))

from scripts.backup.backup_archive import create_zip_archive
from scripts.backup.backup_config import BackupConfig, check_adc_credentials_valid, refresh_adc_credentials, find_gcloud
from scripts.backup.backup_exceptions import ArchiveError, BackupConfigError, BackupError, UploadError
from scripts.backup.backup_secondary import copy_to_secondary_backup
from scripts.backup.backup_upload import upload_to_gdrive
from scripts.backup.backup_utils import cleanup_local_zip

async def run_backup(keep_local: bool, retry_auth: bool = True) -> str:
    """Run the backup process.

    Args:
        keep_local: Whether to keep local zip after upload
        retry_auth: Whether to attempt credential refresh on auth failures

    Returns:
        Google Drive file ID

    Raises:
        BackupError: If any step fails
    """
    # _repo_root is guaranteed to be not None due to the module level check
    root_dir: Path = cast(Path, _repo_root)

    # Load configuration
    config = BackupConfig.load(root_dir)

    # Create zip archive
    zip_path = await create_zip_archive(root_dir)

    # Upload to Google Drive
    try:
        file_id = await upload_to_gdrive(zip_path, config)
    except UploadError as e:
        # Check if it's an authentication error and we should retry
        if (retry_auth and ("reauthentication" in str(e).lower() or 
                            "authenticated" in str(e).lower() or 
                            ("credentials" in str(e).lower() and "impersonated" not in str(e).lower()) or 
                            "invalid_grant" in str(e).lower())):
            
            logger.warning(f"Authentication error detected: {e}")
            logger.info("Attempting to refresh credentials...")
            
            if refresh_adc_credentials():
                logger.info("Credentials refreshed successfully, retrying upload...")
                # Retry the upload with refreshed credentials
                file_id = await upload_to_gdrive(zip_path, config)
            else:
                logger.error("Failed to refresh credentials.")
                raise e
        else:
            raise e

    # Copy to secondary backup location if AMI-BACKUP drives are mounted
    await copy_to_secondary_backup(zip_path)

    # Cleanup
    await cleanup_local_zip(zip_path, keep_local)

    return file_id


def setup_auth() -> int:
    """Set up Google Cloud authentication using local gcloud binary.
    
    Returns:
        Exit code from the gcloud auth command
    """
    logger.info("Setting up Google Cloud authentication...")
    
    gcloud_path = find_gcloud()
    if not gcloud_path:
        logger.error("gcloud CLI not found! Please install with: ./scripts/install_gcloud.sh")
        return 1
    
    logger.info(f"Using gcloud binary: {gcloud_path}")
    logger.info("Running: ami-gcloud auth application-default login")
    logger.info("Please follow the instructions in your browser to complete authentication...")
    
    try:
        # Run the gcloud auth command directly
        result = subprocess.run([gcloud_path, "auth", "application-default", "login"], check=True)
        if result.returncode == 0:
            logger.info("✓ Authentication setup completed successfully!")
            logger.info("You can now run the backup script.")
            return 0
        else:
            logger.error(f"Authentication setup failed with return code: {result.returncode}")
            return result.returncode
    except subprocess.CalledProcessError as e:
        logger.error(f"Authentication setup failed: {e}")
        return e.returncode
    except Exception as e:
        logger.error(f"Unexpected error during authentication setup: {e}")
        return 1


def print_help() -> None:
    """Print help information for the backup script."""
    print("""AMI Orchestrator Backup to Google Drive

Usage:
  scripts/backup_to_gdrive.py                       # Upload and delete local zip (default oauth)
  scripts/backup_to_gdrive.py --keep-local          # Upload and keep local zip
  scripts/backup_to_gdrive.py --setup-auth          # Set up authentication
  scripts/backup_to_gdrive.py --no-auth-retry       # Disable auth retry on failure
  scripts/backup_to_gdrive.py --auth-mode oauth     # Use OAuth authentication
  scripts/backup_to_gdrive.py --auth-mode impersonation  # Use service account impersonation
  scripts/backup_to_gdrive.py --auth-mode key       # Use service account keys
  scripts/backup_to_gdrive.py --auth-mode user_app  # Use pre-registered app
  scripts/backup_to_gdrive.py -h|--help             # Show this help

Authentication Configuration:
  Set GDRIVE_AUTH_METHOD in your .env file to one of:
    - oauth (default): Regular User OAuth via browser authentication
    - impersonation: Service Account Impersonation (requires gcloud setup)
    - key: Service Account Keys (less secure)
    - user_app: Pre-registered application OAuth

  Additional .env variables:
    - GDRIVE_SERVICE_ACCOUNT_EMAIL: For impersonation method
    - GDRIVE_CREDENTIALS_FILE: For key-based method
    - GDRIVE_BACKUP_FOLDER_ID: Google Drive folder ID (optional)

Examples:
  # Use default OAuth authentication
  echo "GDRIVE_AUTH_METHOD=oauth" >> .env
  scripts/backup_to_gdrive.py

  # Use service account impersonation
  echo "GDRIVE_AUTH_METHOD=impersonation" >> .env
  echo "GDRIVE_SERVICE_ACCOUNT_EMAIL=backup@project.iam.gserviceaccount.com" >> .env
  scripts/backup_to_gdrive.py

  # Use service account keys
  echo "GDRIVE_AUTH_METHOD=key" >> .env
  echo "GDRIVE_CREDENTIALS_FILE=/path/to/service-account.json" >> .env
  scripts/backup_to_gdrive.py

  # Override auth mode via command line (temporarily)
  scripts/backup_to_gdrive.py --auth-mode impersonation

  # Keep local archive after upload
  scripts/backup_to_gdrive.py --keep-local

  # Setup authentication for impersonation method
  scripts/backup_to_gdrive.py --setup-auth
""")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0=success, 1=failure)
    """
    import os  # Import at the beginning of the function

    # Parse arguments
    if "-h" in sys.argv or "--help" in sys.argv:
        print_help()
        return 0

    logger.info("=" * 60)
    logger.info("AMI Orchestrator Backup to Google Drive")
    logger.info("=" * 60)

    # Parse command line arguments
    keep_local = "--keep-local" in sys.argv
    setup_auth_flag = "--setup-auth" in sys.argv
    no_retry_auth = "--no-auth-retry" in sys.argv  # Option to disable auth retry

    # Check for auth mode override
    auth_mode_override = None
    for i, arg in enumerate(sys.argv):
        if arg == "--auth-mode" and i + 1 < len(sys.argv):
            auth_mode_override = sys.argv[i + 1]
            # Validate the auth mode
            if auth_mode_override not in ["oauth", "impersonation", "key", "user_app"]:
                logger.error(f"Invalid auth mode: {auth_mode_override}")
                logger.error("Valid options are: oauth, impersonation, key, user_app")
                return 1
            break

    # If setup-auth flag is present, perform authentication setup
    if setup_auth_flag:
        return setup_auth()

    # Temporarily override the environment variable if auth-mode is specified
    original_auth_method = None
    if auth_mode_override:
        original_auth_method = os.environ.get("GDRIVE_AUTH_METHOD")
        os.environ["GDRIVE_AUTH_METHOD"] = auth_mode_override
        logger.info(f"Using command-line auth mode override: {auth_mode_override}")

    # Otherwise, run the backup as normal
    auth_retry_enabled = not no_retry_auth
    try:
        file_id = asyncio.run(run_backup(keep_local, retry_auth=auth_retry_enabled))

        logger.info("=" * 60)
        logger.info("✓ Backup completed successfully")
        logger.info(f"  Google Drive File ID: {file_id}")
        logger.info("=" * 60)

        # Restore original environment variable if it was overridden
        if auth_mode_override and original_auth_method is not None:
            os.environ["GDRIVE_AUTH_METHOD"] = original_auth_method
        elif auth_mode_override:  # If original was None (not set), remove the override
            if "GDRIVE_AUTH_METHOD" in os.environ:
                del os.environ["GDRIVE_AUTH_METHOD"]

        return 0

    except BackupConfigError as e:
        logger.error(f"Configuration error: {e}")
        # Check if it's an authentication error and suggest setup-auth
        if "credentials" in str(e).lower() or "authenticated" in str(e).lower():
            logger.info("  To set up authentication, run: scripts/backup_to_gdrive.py --setup-auth")
        elif "GDRIVE_AUTH_METHOD" in str(e):
            logger.info("  GDRIVE_AUTH_METHOD can be set in your .env file to 'impersonation', 'key', 'oauth', or 'user_app'. Or use --auth-mode command line option.")
        # Restore original environment variable if it was overridden before exiting with error
        if auth_mode_override and original_auth_method is not None:
            os.environ["GDRIVE_AUTH_METHOD"] = original_auth_method
        elif auth_mode_override and "GDRIVE_AUTH_METHOD" in os.environ:
            del os.environ["GDRIVE_AUTH_METHOD"]
        return 1

    except ArchiveError as e:
        logger.error(f"Archive creation failed: {e}")
        # Restore original environment variable if it was overridden before exiting with error
        if auth_mode_override and original_auth_method is not None:
            os.environ["GDRIVE_AUTH_METHOD"] = original_auth_method
        elif auth_mode_override and "GDRIVE_AUTH_METHOD" in os.environ:
            del os.environ["GDRIVE_AUTH_METHOD"]
        return 1

    except UploadError as e:
        logger.error(f"Upload failed: {e}")
        # Check if it's an authentication error
        if "reauthentication" in str(e).lower() or "authenticated" in str(e).lower():
            logger.info("  Authentication may be needed. To set up authentication, run: scripts/backup_to_gdrive.py --setup-auth")
            if auth_retry_enabled:
                logger.info("  (Auth retry was attempted but failed)")
        # Restore original environment variable if it was overridden before exiting with error
        if auth_mode_override and original_auth_method is not None:
            os.environ["GDRIVE_AUTH_METHOD"] = original_auth_method
        elif auth_mode_override and "GDRIVE_AUTH_METHOD" in os.environ:
            del os.environ["GDRIVE_AUTH_METHOD"]
        return 1

    except BackupError as e:
        logger.error(f"Backup failed: {e}")
        # Restore original environment variable if it was overridden before exiting with error
        if auth_mode_override and original_auth_method is not None:
            os.environ["GDRIVE_AUTH_METHOD"] = original_auth_method
        elif auth_mode_override and "GDRIVE_AUTH_METHOD" in os.environ:
            del os.environ["GDRIVE_AUTH_METHOD"]
        return 1

    except (OSError, ValueError) as e:
        logger.error(f"System error: {e}")
        # Restore original environment variable if it was overridden before exiting with error
        if auth_mode_override and original_auth_method is not None:
            os.environ["GDRIVE_AUTH_METHOD"] = original_auth_method
        elif auth_mode_override and "GDRIVE_AUTH_METHOD" in os.environ:
            del os.environ["GDRIVE_AUTH_METHOD"]
        return 1


if __name__ == "__main__":
    sys.exit(main())
