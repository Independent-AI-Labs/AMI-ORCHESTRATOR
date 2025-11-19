"""Unit tests for backup config module."""

from unittest.mock import patch

from scripts.backup.backup_config import BackupConfig, find_gcloud
from scripts.backup.backup_exceptions import BackupConfigError


class TestBackupConfig:
    """Unit tests for BackupConfig class."""

    def test_config_initialization(self, tmp_path):
        """BackupConfig initializes with correct attributes."""
        config = BackupConfig(root_dir=tmp_path)

        assert config.root_dir == tmp_path
        # auth_method is not set until load() is called
        assert not hasattr(config, "auth_method") or config.auth_method is None
        assert config.service_account_email is None
        assert config.credentials_file is None
        assert config.folder_id is None
        assert config.gcloud_path is None

    @patch.dict(
        "os.environ",
        {"GDRIVE_AUTH_METHOD": "impersonation", "GDRIVE_SERVICE_ACCOUNT_EMAIL": "test@serviceaccount.com", "GDRIVE_BACKUP_FOLDER_ID": "folder123"},
        clear=True,
    )
    def test_load_with_explicit_impersonation(self, tmp_path):
        """BackupConfig.load creates impersonation config when explicitly set."""
        # Create a dummy .env file
        env_file = tmp_path / ".env"
        env_file.write_text("")

        with (
            patch("scripts.backup.backup_config.find_gcloud", return_value="/mocked/gcloud/path"),
            patch("scripts.backup.backup_config.check_adc_credentials_valid", return_value=True),
        ):
            config = BackupConfig.load(tmp_path)

        assert config.auth_method == "impersonation"
        assert config.service_account_email == "test@serviceaccount.com"
        assert config.folder_id == "folder123"
        assert config.gcloud_path == "/mocked/gcloud/path"

    @patch.dict(
        "os.environ", {"GDRIVE_AUTH_METHOD": "key", "GDRIVE_CREDENTIALS_FILE": "/path/to/credentials.json", "GDRIVE_BACKUP_FOLDER_ID": "folder123"}, clear=True
    )
    def test_load_with_explicit_key_auth(self, tmp_path):
        """BackupConfig.load creates key-based config when explicitly set."""
        # Create a dummy .env file
        env_file = tmp_path / ".env"
        env_file.write_text("")

        # Mock credentials file existence
        with patch("pathlib.Path.exists", return_value=True), patch("scripts.backup.backup_config.find_gcloud", return_value=None):
            config = BackupConfig.load(tmp_path)

        assert config.auth_method == "key"
        assert config.credentials_file == "/path/to/credentials.json"
        assert config.folder_id == "folder123"

    @patch.dict("os.environ", {"GDRIVE_SERVICE_ACCOUNT_EMAIL": "test@serviceaccount.com"}, clear=True)
    def test_load_without_auth_config_uses_default_oauth(self, tmp_path):
        """BackupConfig.load uses oauth as default when no auth method specified."""
        # Create a dummy .env file
        env_file = tmp_path / ".env"
        env_file.write_text("")

        config = BackupConfig.load(tmp_path)

        assert config.auth_method == "oauth"  # Default value
        # Service account email is not used with OAuth method, so it remains None
        assert config.service_account_email is None

    @patch.dict("os.environ", {"GDRIVE_AUTH_METHOD": "invalid_method", "GDRIVE_SERVICE_ACCOUNT_EMAIL": "test@serviceaccount.com"}, clear=True)
    def test_load_with_invalid_auth_method_raises_error(self, tmp_path):
        """BackupConfig.load raises error with invalid auth method."""
        # Create a dummy .env file
        env_file = tmp_path / ".env"
        env_file.write_text("")

        try:
            BackupConfig.load(tmp_path)
            raise AssertionError("Expected BackupConfigError was not raised")
        except BackupConfigError as e:
            # Verify that the correct error message is raised
            assert "Invalid GDRIVE_AUTH_METHOD" in str(e)
        except Exception as e:
            raise AssertionError(f"Expected BackupConfigError but got {type(e).__name__}: {e}") from e

    @patch.dict("os.environ", {"GDRIVE_AUTH_METHOD": "impersonation"}, clear=True)
    def test_load_with_impersonation_but_no_service_account_raises_error(self, tmp_path):
        """BackupConfig.load raises error when using impersonation but no service account is provided."""
        # Create a dummy .env file
        env_file = tmp_path / ".env"
        env_file.write_text("")

        try:
            BackupConfig.load(tmp_path)
            raise AssertionError("Expected BackupConfigError was not raised")
        except BackupConfigError as e:
            # Verify that the correct error message is raised
            assert "GDRIVE_SERVICE_ACCOUNT_EMAIL must be set when using impersonation auth method" in str(e)
        except Exception as e:
            raise AssertionError(f"Expected BackupConfigError but got {type(e).__name__}: {e}") from e

    @patch.dict("os.environ", {"GDRIVE_AUTH_METHOD": "key"}, clear=True)
    def test_load_with_key_auth_but_no_credentials_raises_error(self, tmp_path):
        """BackupConfig.load raises error when using key auth but no credentials file is provided."""
        # Create a dummy .env file
        env_file = tmp_path / ".env"
        env_file.write_text("")

        try:
            BackupConfig.load(tmp_path)
            raise AssertionError("Expected BackupConfigError was not raised")
        except BackupConfigError as e:
            # Verify that the correct error message is raised
            assert "GDRIVE_CREDENTIALS_FILE must be set when using key auth method" in str(e)
        except Exception as e:
            raise AssertionError(f"Expected BackupConfigError but got {type(e).__name__}: {e}") from e

    @patch.dict("os.environ", {"GDRIVE_AUTH_METHOD": "oauth", "GDRIVE_BACKUP_FOLDER_ID": "folder123"}, clear=True)
    def test_load_with_oauth_auth(self, tmp_path):
        """BackupConfig.load creates OAuth-based config when explicitly set to oauth."""
        # Create a dummy .env file
        env_file = tmp_path / ".env"
        env_file.write_text("")

        config = BackupConfig.load(tmp_path)

        assert config.auth_method == "oauth"
        assert config.folder_id == "folder123"


class TestFindGcloud:
    """Tests for find_gcloud function."""

    @patch("pathlib.Path.exists", return_value=False)  # Local installation doesn't exist
    def test_find_gcloud_system_path(self, mock_exists):
        """find_gcloud finds system gcloud when local not available."""
        with patch("shutil.which", return_value="/usr/bin/gcloud"):  # System gcloud exists
            result = find_gcloud()
            assert result == "/usr/bin/gcloud"

    @patch("pathlib.Path.exists", return_value=False)  # Local installation doesn't exist
    def test_find_gcloud_not_found(self, mock_exists):
        """find_gcloud returns None when not found."""
        with patch("shutil.which", return_value=None):  # System gcloud doesn't exist
            result = find_gcloud()
            assert result is None
