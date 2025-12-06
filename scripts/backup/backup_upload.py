"""Backup upload module.

Handles uploading archives to Google Drive using configured authentication.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, cast, Optional

from loguru import logger

# Add orchestrator root to path for imports
_repo_root = next((p for p in Path(__file__).resolve().parents if (p / "base").exists()), None)
if not _repo_root:
    raise RuntimeError("Unable to locate AMI orchestrator root")
sys.path.insert(0, str(_repo_root))

from base.backend.workers.file_subprocess import FileSubprocess

from scripts.backup.backup_config import BackupConfig
from scripts.backup.backup_exceptions import UploadError

# Google API related imports for authentication methods
import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth import impersonated_credentials
import google.auth
from google.auth.credentials import Credentials as GoogleAuthCredentials
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials
from google.auth.transport.requests import Request as GoogleRequest

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


def get_credentials(config: BackupConfig) -> GoogleAuthCredentials:  # Return type is GoogleAuthCredentials which covers all our auth types
    """Get credentials based on configuration method.

    Args:
        config: Backup configuration with auth method

    Returns:
        Google credentials object

    Raises:
        UploadError: If credential acquisition fails
    """
    if config.auth_method == "impersonation":
        try:

            # Get source credentials (user credentials from gcloud)
            from google.auth.credentials import Credentials as GoogleCredentials

            # Get source credentials - for now, we'll call directly but handle the error appropriately
            auth_result: tuple[GoogleAuthCredentials, Optional[str]] = google.auth.default()
            source_creds: GoogleCredentials = auth_result[0]
            project_id: Optional[str] = auth_result[1]
            logger.debug(f"Got source credentials for project: {project_id}")
            logger.debug(f"Source credentials type: {type(source_creds)}")
            logger.debug(f"Source credentials valid: {source_creds.valid}")

            # Check if source credentials are already impersonated credentials
            if isinstance(source_creds, impersonated_credentials.Credentials):
                logger.warning("Source credentials are already impersonated credentials, which may cause issues")
                # Use the existing credentials if they're valid
                if source_creds.valid:
                    logger.debug("Using existing impersonated credentials")
                    return source_creds
                else:
                    # If invalid, we need to get non-impersonated source credentials
                    logger.error("Invalid impersonated source credentials, authentication may fail")

            # Impersonate the service account
            from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials

            # Validate service account email is provided
            if not config.service_account_email:
                raise UploadError("Service account email is required for impersonation auth method")

            # Create impersonated credentials with proper error handling
            credentials: ImpersonatedCredentials = impersonated_credentials.Credentials(
                source_credentials=source_creds,
                target_principal=config.service_account_email,
                target_scopes=["https://www.googleapis.com/auth/drive"],
                lifetime=3600  # 1 hour
            )
            
            logger.debug("Created impersonated credentials")
            logger.debug(f"Impersonated credentials type: {type(credentials)}")
            
            # Explicitly refresh to test if impersonation works
            from google.auth.transport.requests import Request as GoogleRequest

            impersonation_request_obj: GoogleRequest = Request()
            credentials.refresh(impersonation_request_obj)
            logger.debug("Successfully refreshed impersonated credentials")
            
            return credentials
        except Exception as e:
            raise UploadError(
                f"Failed to impersonate service account: {e}. "
                "Ensure you have roles/iam.serviceAccountTokenCreator permission"
            )

    elif config.auth_method == "key":
        try:
            from google.oauth2 import service_account
            from google.oauth2.service_account import Credentials as ServiceAccountCredentials

            # Validate credentials file exists
            if not config.credentials_file:
                raise UploadError("Credentials file path is required for key auth method")

            credentials_file_path = Path(config.credentials_file)
            if not credentials_file_path.exists():
                raise UploadError(f"Credentials file does not exist: {credentials_file_path}")

            key_credentials: ServiceAccountCredentials = service_account.Credentials.from_service_account_file(
                credentials_file_path,
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            return key_credentials
        except Exception as e:
            raise UploadError(f"Failed to load service account credentials from file: {e}")

    elif config.auth_method == "oauth":
        try:

            # Define the scopes required for Google Drive API
            scopes = ["https://www.googleapis.com/auth/drive"]

            creds = None
            token_path = config.root_dir / "token.pickle"

            # The file token.pickle stores the user's access and refresh tokens.
            if token_path.exists():
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)

            # If there are no valid credentials available, request authorization
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # Refresh the token
                    oauth_request_obj: GoogleRequest = Request()
                    creds.refresh(oauth_request_obj)
                else:
                    # Check if credentials.json exists for the OAuth flow
                    credentials_json_path = config.root_dir / "credentials.json"
                    if not credentials_json_path.exists():
                        raise UploadError(
                            f"credentials.json not found at {credentials_json_path}\n"
                            "For OAuth method, create credentials.json from Google Cloud Console.\n"
                            "Go to APIs & Services > Credentials, create OAuth 2.0 Client ID for Desktop application."
                        )

                    # Run the OAuth flow to get new credentials
                    from google_auth_oauthlib.flow import Flow as OAuthFlow
                    flow: OAuthFlow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_json_path),
                        scopes
                    )
                    creds = flow.run_local_server(port=0)  # This will open a browser window

                # Save the credentials for the next run
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)

            return creds
        except Exception as e:
            raise UploadError(f"Failed to authenticate with regular user OAuth: {e}. "
                              "Ensure you have set up OAuth credentials in Google Cloud Console.")

    elif config.auth_method == "user_app":
        try:
            import json

            # Define the scopes required for Google Drive API
            scopes = ["https://www.googleapis.com/auth/drive"]

            creds = None
            token_path = config.root_dir / "user_app_token.pickle"

            # The file user_app_token.pickle stores the user's access and refresh tokens.
            if token_path.exists():
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)

            # If there are no valid credentials available, request authorization
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # Refresh the token
                    user_app_request_obj: GoogleRequest = Request()
                    creds.refresh(user_app_request_obj)
                else:
                    # For user_app method, use embedded application credentials
                    # These would be the client_id and client_secret of the pre-registered application
                    # In a real implementation, these would come from a secure source
                    # For demonstration, we'll create a temporary credentials structure
                    temp_credentials_path = config.root_dir / "temp_user_app_credentials.json"

                    # Create temporary embedded credentials structure for the pre-registered app
                    # NOTE: In production, these should be obtained securely
                    app_credentials = {
                        "installed": {
                            "client_id": "embedded_client_id_for_user_app",  # Template - will be replaced with real client ID
                            "project_id": "ami-orchestrator-app",
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                            "client_secret": "embedded_client_secret_for_user_app",  # Template - will be replaced with real secret
                            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                        }
                    }

                    # Write the temporary credentials file
                    with open(temp_credentials_path, 'w') as f:
                        json.dump(app_credentials, f)

                    try:
                        # Run the OAuth flow to get new credentials using the embedded app credentials
                        flow_user_app: Any = InstalledAppFlow.from_client_config(
                            app_credentials,
                            scopes
                        )
                        creds = flow_user_app.run_local_server(port=0)  # This will open a browser window
                    finally:
                        # Clean up the temporary credentials file
                        if temp_credentials_path.exists():
                            temp_credentials_path.unlink()

                # Save the credentials for the next run
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)

            return creds
        except Exception as e:
            raise UploadError(f"Failed to authenticate with user app login: {e}. "
                              "Please ensure you have properly authenticated with the app.")
    else:
        raise UploadError(f"Unknown authentication method: {config.auth_method}")


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

    # This function now uses FileSubprocess to execute the upload in a subprocess
    # to isolate Google API dependencies and authentication
    executor = FileSubprocess(work_dir=config.root_dir)
    
    # Prepare command arguments for subprocess execution
    cmd_args = [
        sys.executable, "-c",
        f"""
import json
import sys
from pathlib import Path

# Add orchestrator root to path for imports
# Use sys.argv[0] if __file__ is not available (e.g., when running with string-based execution)
script_path = Path(__file__) if "__file__" in globals() else Path(sys.argv[0])
_repo_root = next((p for p in script_path.resolve().parents if (p / "base").exists()), None)
if not _repo_root:
    raise RuntimeError("Unable to locate AMI orchestrator root")
sys.path.insert(0, str(_repo_root))

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError as e:
    result = {{
        "success": False,
        "error": f"Required Google API package not installed: {{e}}. Install with: ami-uv add google-auth==2.41.1 google-api-python-client==2.185.0"
    }}
    print(json.dumps(result))
    sys.exit(1)

# Import config and auth functions
from scripts.backup.backup_config import BackupConfig
from scripts.backup.backup_exceptions import UploadError

from scripts.backup.backup_upload import get_credentials

# Create config object with provided settings
config = BackupConfig(Path('.'))
config.auth_method = '{config.auth_method}'
config.service_account_email = '{config.service_account_email or ""}'
config.credentials_file = '{config.credentials_file or ""}'
config.folder_id = '{config.folder_id or ""}'
config.root_dir = Path('.')

try:
    # Get credentials based on configuration
    credentials = get_credentials(config)

    # Build Drive API service
    service = build("drive", "v3", credentials=credentials)

    # Build search query for existing files
    search_query = f'name = \\\'{zip_path.name}\\\' and trashed = false'
    if '{config.folder_id}':
        search_query += f' and \\\'{config.folder_id}\\\' in parents'

    # Build file metadata for new uploads
    file_metadata = {{"name": "{zip_path.name}"}}
    if '{config.folder_id}':
        file_metadata["parents"] = ["{config.folder_id}"]

    # Search for existing file with same name in folder
    existing_file_id = None
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
        '{str(zip_path)}',
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
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True
        ).execute()

    file_id = file.get("id")
    if not file_id:
        raise UploadError("Upload succeeded but no file ID returned")

    # Log success and return result
    result = {{
        "success": True,
        "file_id": file_id,
        "name": file.get('name'),
        "link": file.get('webViewLink')
    }}
    print(json.dumps(result))
    
except Exception as e:
    result = {{
        "success": False,
        "error": str(e)
    }}
    print(json.dumps(result))
    sys.exit(1)
        """
    ]

    # Run the subprocess
    result = await executor.run(cmd_args)

    if not result["success"]:
        stderr_output = result.get("stderr", "No stderr output")
        raise UploadError(f"Upload failed:\\nError output:\\n{stderr_output}\\n\\n{result.get('stdout', '')}")

    # Parse the output
    try:
        output = json.loads(result["stdout"])
    except json.JSONDecodeError as e:
        raise UploadError(f"Failed to parse upload result: {result['stdout'][:200]}") from e

    if not output.get("success"):
        error_msg = output.get("error", "Unknown error")
        raise UploadError(f"Upload failed: {error_msg}")

    file_id: str = output.get("file_id")
    if not file_id:
        raise UploadError("Upload succeeded but no file ID returned")

    # Log success
    logger.info("✓ Upload complete")
    logger.info(f"  File ID: {file_id}")
    if output.get("name"):
        logger.info(f"  Name: {output.get('name')}")
    if output.get("link"):
        logger.info(f"  Link: {output.get('link')}")

    return file_id
