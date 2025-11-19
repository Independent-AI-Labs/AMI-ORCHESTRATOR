"""Backup configuration module.

Handles loading and validation of backup configuration from .env file.
"""

import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Add orchestrator root to path for imports
# Use sys.argv[0] if __file__ is not available (e.g., when running with string-based execution)
script_path = Path(__file__) if "__file__" in globals() else Path(sys.argv[0])
_repo_root = next((p for p in script_path.resolve().parents if (p / "base").exists()), None)
if not _repo_root:
    raise RuntimeError("Unable to locate AMI orchestrator root")
sys.path.insert(0, str(_repo_root))

from scripts.backup.backup_exceptions import BackupConfigError

def find_gcloud() -> str | None:
    """Find gcloud CLI binary (local or system).

    Checks in order:
    1. Local installation: .gcloud/google-cloud-sdk/bin/gcloud
    2. System PATH: gcloud

    Returns:
        Path to gcloud binary or None if not found
    """
    # Check for local installation first
    # Use sys.argv[0] if __file__ is not available (e.g., when running with string-based execution)
    script_path = Path(__file__) if "__file__" in globals() else Path(sys.argv[0])
    script_dir = script_path.resolve().parents[2]  # Go back from scripts/backup/ to project root
    local_gcloud = script_dir / ".gcloud" / "google-cloud-sdk" / "bin" / "gcloud"

    if local_gcloud.exists():
        return str(local_gcloud)

    # Check system PATH
    system_gcloud = shutil.which("gcloud")
    if system_gcloud:
        return system_gcloud

    return None


def check_adc_credentials_valid() -> bool:
    """Check if Application Default Credentials are valid and not expired.
    
    Returns:
        True if valid, False otherwise
    """
    import subprocess
    
    gcloud_path = find_gcloud()
    if not gcloud_path:
        return False

    try:
        # Check if ADC credentials file exists and is accessible
        adc_path = Path.home() / ".config/gcloud/application_default_credentials.json"
        if not adc_path.exists():
            return False

        # Check current token status using gcloud (same approach as refresh_adc_credentials)
        result = subprocess.run([gcloud_path, "auth", "application-default", "print-access-token"], 
                                capture_output=True, text=True, timeout=30)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        # If any error occurs, return False
        return False


def refresh_adc_credentials() -> bool:
    """Attempt to refresh Application Default Credentials using gcloud.

    Returns:
        True if refresh was successful, False otherwise
    """
    import subprocess

    gcloud_path = find_gcloud()
    if not gcloud_path:
        logger.error("gcloud CLI not found! Cannot refresh credentials.")
        return False

    try:
        # Check if ADC credentials file exists and is accessible
        adc_path = Path.home() / ".config/gcloud/application_default_credentials.json"
        if not adc_path.exists():
            logger.warning("Application Default Credentials file not found, need to set up auth first.")
            return False

        # Check current token status
        result = subprocess.run([gcloud_path, "auth", "application-default", "print-access-token"],
                                capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info("Access token is still valid.")
            return True
        else:
            logger.info("Current access token is invalid or expired, attempting refresh...")
            logger.debug(f"gcloud error output: {result.stderr}")

            # Try to refresh using gcloud
            refresh_result = subprocess.run([gcloud_path, "auth", "application-default", "login"],
                                           capture_output=True, text=True, timeout=30)

            if refresh_result.returncode == 0:
                logger.info("Credentials successfully refreshed.")
                return True
            else:
                logger.error(f"Failed to refresh credentials: {refresh_result.stderr}")
                return False

    except subprocess.TimeoutExpired:
        logger.error("Timeout while checking credentials with gcloud.")
        return False
    except Exception as e:
        logger.error(f"Error refreshing credentials: {e}")
        return False


class BackupConfig:
    """Backup configuration loaded from .env"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.auth_method: str  # "impersonation", "key", "oauth", or "user_app"
        self.service_account_email: str | None = None
        self.credentials_file: str | None = None
        self.folder_id: str | None = None
        self.gcloud_path: str | None = None

    @classmethod
    def load(cls, root_dir: Path) -> "BackupConfig":
        """Load configuration from .env file.

        Authentication method defaults to impersonation if not specified.
        This provides a secure default while still allowing explicit configuration.

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

        # Use OAuth as default auth method for user accessibility
        auth_method = os.getenv("GDRIVE_AUTH_METHOD", "oauth")

        # Validate auth method
        if auth_method not in ["impersonation", "key", "oauth", "user_app"]:
            raise BackupConfigError(
                f"Invalid GDRIVE_AUTH_METHOD: {auth_method}. Must be 'impersonation', 'key', 'oauth', or 'user_app'."
            )

        config.auth_method = auth_method

        if auth_method == "impersonation":
            # Require service account email for impersonation
            service_account_email = os.getenv("GDRIVE_SERVICE_ACCOUNT_EMAIL")
            if not service_account_email:
                raise BackupConfigError(
                    "GDRIVE_SERVICE_ACCOUNT_EMAIL must be set when using impersonation auth method.\n"
                    "Example: GDRIVE_SERVICE_ACCOUNT_EMAIL=backup@project.iam.gserviceaccount.com"
                )

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

                # Check if ADC credentials are valid
                if check_adc_credentials_valid():
                    logger.info("  ✓ Application Default Credentials are valid")
                else:
                    logger.warning("  ⚠️  Application Default Credentials may be expired or invalid")
                    logger.info(f"  To refresh: ami-gcloud auth application-default login")
            else:
                logger.error("  ❌ gcloud CLI not found!")
                logger.error("  Install with: ./scripts/install_gcloud.sh")
                logger.error("  Or install system-wide: https://cloud.google.com/sdk/docs/install")
                raise BackupConfigError("gcloud CLI required for impersonation auth method")

        elif auth_method == "key":
            # Require credentials file for key-based auth
            credentials_file = os.getenv("GDRIVE_CREDENTIALS_FILE")
            if not credentials_file:
                raise BackupConfigError(
                    "GDRIVE_CREDENTIALS_FILE must be set when using key auth method.\n"
                    "Example: GDRIVE_CREDENTIALS_FILE=/path/to/service-account.json"
                )

            # Resolve credentials path
            credentials_path = Path(credentials_file)
            if not credentials_path.is_absolute():
                credentials_path = root_dir / credentials_path

            if not credentials_path.exists():
                raise BackupConfigError(
                    f"Credentials file not found at {credentials_path}\nCreate a service account and download the JSON key from Google Cloud Console"
                )

            config.credentials_file = str(credentials_path)

            logger.warning("⚠️  Using service account key file (security risk)")
            logger.warning("  Consider switching to service account impersonation")
            logger.warning("  See script docstring for setup instructions")

        elif auth_method == "oauth":
            # For OAuth method, we don't need specific environment variables
            # The credentials will be stored in token.pickle or similar
            logger.info("Using regular user OAuth (requires initial browser authentication)")
            logger.info("  First time setup will open a browser for authentication")

        elif auth_method == "user_app":
            # For user app login method, we use embedded application credentials
            logger.info("Using user app login with pre-registered application (requires initial browser authentication)")
            logger.info("  First time setup will open a browser for authentication")

        # Load optional folder ID
        config.folder_id = os.getenv("GDRIVE_BACKUP_FOLDER_ID")

        return config