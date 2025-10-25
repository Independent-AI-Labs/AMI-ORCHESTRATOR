"""Comprehensive test suite for backup_to_gdrive.py script.

Test Coverage:
- Unit tests: Configuration, gcloud detection, path handling
- Integration tests: Archive creation, compression, exclusions
- E2E tests: Full backup with real credentials (conditional)
- Mock tests: API interactions without real credentials

Run modes:
    pytest tests/test_backup_to_gdrive.py -m "not e2e"  # Unit/integration only
    pytest tests/test_backup_to_gdrive.py                # All tests (requires creds)
    pytest tests/test_backup_to_gdrive.py -m e2e         # E2E only
"""

import os

# Import script functions
import sys
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import zstandard as zstd

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))

# Import after path setup
from scripts import backup_to_gdrive


class TestGcloudDetection:
    """Test gcloud CLI detection logic."""

    def test_find_gcloud_local_installation(self, tmp_path, monkeypatch):
        """Test detection of local .gcloud installation."""
        # Create mock local gcloud
        local_gcloud = tmp_path / ".gcloud" / "google-cloud-sdk" / "bin" / "gcloud"
        local_gcloud.parent.mkdir(parents=True)
        local_gcloud.touch()

        # Mock script location
        with patch("scripts.backup_to_gdrive.Path") as mock_path:
            mock_file = MagicMock()
            mock_file.parent.parent = tmp_path
            mock_path(__file__).parent.parent = tmp_path
            mock_path.return_value.parent.parent = tmp_path

            result = backup_to_gdrive.find_gcloud()

        # Should prefer local installation
        assert result is not None
        assert ".gcloud" in result

    def test_find_gcloud_system_path(self, monkeypatch):
        """Test detection of system gcloud from PATH."""
        # Mock shutil.which to return system gcloud
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/gcloud"

            # Mock no local installation
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                result = backup_to_gdrive.find_gcloud()

        assert result == "/usr/bin/gcloud"

    def test_find_gcloud_not_found(self, monkeypatch):
        """Test when gcloud is not found anywhere."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False
            with patch("shutil.which") as mock_which:
                mock_which.return_value = None

                result = backup_to_gdrive.find_gcloud()

        assert result is None


class TestBackupConfig:
    """Test BackupConfig class and configuration loading."""

    def test_config_no_auth_configured(self, tmp_path, monkeypatch):
        """Test error when no authentication is configured."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        monkeypatch.setenv("GDRIVE_SERVICE_ACCOUNT_EMAIL", "")
        monkeypatch.setenv("GDRIVE_CREDENTIALS_FILE", "")

        with pytest.raises(backup_to_gdrive.BackupConfigError) as exc_info:
            backup_to_gdrive.BackupConfig.load(tmp_path)

        assert "No authentication configured" in str(exc_info.value)

    def test_config_impersonation_method(self, tmp_path, monkeypatch):
        """Test configuration with service account impersonation."""
        env_file = tmp_path / ".env"
        env_file.write_text("GDRIVE_SERVICE_ACCOUNT_EMAIL=backup@project.iam.gserviceaccount.com\n")

        monkeypatch.setenv("GDRIVE_SERVICE_ACCOUNT_EMAIL", "backup@project.iam.gserviceaccount.com")

        with patch("scripts.backup_to_gdrive.find_gcloud") as mock_find:
            mock_find.return_value = "/usr/bin/gcloud"

            config = backup_to_gdrive.BackupConfig.load(tmp_path)

        assert config.auth_method == "impersonation"
        assert config.service_account_email == "backup@project.iam.gserviceaccount.com"
        assert config.gcloud_path == "/usr/bin/gcloud"

    def test_config_key_file_method(self, tmp_path, monkeypatch):
        """Test configuration with service account key file."""
        # Create dummy credentials file
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"type":"service_account"}')

        env_file = tmp_path / ".env"
        env_file.write_text(f"GDRIVE_CREDENTIALS_FILE={creds_file}\n")

        monkeypatch.setenv("GDRIVE_CREDENTIALS_FILE", str(creds_file))
        monkeypatch.delenv("GDRIVE_SERVICE_ACCOUNT_EMAIL", raising=False)

        config = backup_to_gdrive.BackupConfig.load(tmp_path)

        assert config.auth_method == "key"
        assert config.credentials_file == str(creds_file)

    def test_config_missing_credentials_file(self, tmp_path, monkeypatch):
        """Test error when credentials file doesn't exist."""
        env_file = tmp_path / ".env"
        env_file.write_text("GDRIVE_CREDENTIALS_FILE=/nonexistent/creds.json\n")

        monkeypatch.setenv("GDRIVE_CREDENTIALS_FILE", "/nonexistent/creds.json")
        monkeypatch.delenv("GDRIVE_SERVICE_ACCOUNT_EMAIL", raising=False)

        with pytest.raises(backup_to_gdrive.BackupConfigError) as exc_info:
            backup_to_gdrive.BackupConfig.load(tmp_path)

        assert "Credentials file not found" in str(exc_info.value)

    def test_config_relative_credentials_path(self, tmp_path, monkeypatch):
        """Test resolution of relative credentials file path."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"type":"service_account"}')

        env_file = tmp_path / ".env"
        env_file.write_text("GDRIVE_CREDENTIALS_FILE=creds.json\n")

        monkeypatch.setenv("GDRIVE_CREDENTIALS_FILE", "creds.json")
        monkeypatch.delenv("GDRIVE_SERVICE_ACCOUNT_EMAIL", raising=False)

        config = backup_to_gdrive.BackupConfig.load(tmp_path)

        assert config.credentials_file == str(tmp_path / "creds.json")

    def test_config_folder_id_optional(self, tmp_path, monkeypatch):
        """Test that folder ID is optional."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"type":"service_account"}')

        env_file = tmp_path / ".env"
        env_file.write_text(f"GDRIVE_CREDENTIALS_FILE={creds_file}\n")

        monkeypatch.setenv("GDRIVE_CREDENTIALS_FILE", str(creds_file))
        monkeypatch.delenv("GDRIVE_SERVICE_ACCOUNT_EMAIL", raising=False)
        monkeypatch.delenv("GDRIVE_BACKUP_FOLDER_ID", raising=False)

        config = backup_to_gdrive.BackupConfig.load(tmp_path)

        assert config.folder_id is None


@pytest.mark.asyncio
class TestArchiveCreation:
    """Integration tests for archive creation and compression."""

    async def test_create_archive_basic(self, tmp_path):
        """Test basic archive creation."""
        # Create minimal repo structure
        (tmp_path / "base").mkdir()
        (tmp_path / "test_file.txt").write_text("test content")

        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)

        assert archive_path.exists()
        assert archive_path.suffix == ".zst"
        assert "ami-orchestrator-" in archive_path.name

        # Verify it's a valid zstd archive
        dctx = zstd.ZstdDecompressor()
        with (
            archive_path.open("rb") as fh,
            dctx.stream_reader(fh) as reader,
            tarfile.open(fileobj=reader, mode="r|") as tar,
        ):
            members = tar.getnames()
            assert any("test_file.txt" in m for m in members)

        # Cleanup
        archive_path.unlink()

    async def test_archive_excludes_pycache(self, tmp_path):
        """Test that __pycache__ directories are excluded."""
        (tmp_path / "base").mkdir()
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "module.pyc").write_text("compiled")

        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)

        # Verify __pycache__ is NOT in archive
        dctx = zstd.ZstdDecompressor()
        with (
            archive_path.open("rb") as fh,
            dctx.stream_reader(fh) as reader,
            tarfile.open(fileobj=reader, mode="r|") as tar,
        ):
            members = tar.getnames()
            assert not any("__pycache__" in m for m in members)

        archive_path.unlink()

    async def test_archive_excludes_node_modules(self, tmp_path):
        """Test that node_modules directories are excluded."""
        (tmp_path / "base").mkdir()
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "package").mkdir()

        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)

        dctx = zstd.ZstdDecompressor()
        with (
            archive_path.open("rb") as fh,
            dctx.stream_reader(fh) as reader,
            tarfile.open(fileobj=reader, mode="r|") as tar,
        ):
            members = tar.getnames()
            assert not any("node_modules" in m for m in members)

        archive_path.unlink()

    async def test_archive_includes_root_venv(self, tmp_path):
        """Test that root .venv is included but module .venvs are excluded."""
        (tmp_path / "base").mkdir()
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib").mkdir()
        (tmp_path / "base" / ".venv").mkdir()

        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)

        dctx = zstd.ZstdDecompressor()
        with (
            archive_path.open("rb") as fh,
            dctx.stream_reader(fh) as reader,
            tarfile.open(fileobj=reader, mode="r|") as tar,
        ):
            members = tar.getnames()
            # Root .venv should be included
            root_venv_found = any(".venv" in m and "base" not in m for m in members)
            # Module .venv should be excluded
            module_venv_found = any("base/.venv" in m for m in members)

            assert root_venv_found
            assert not module_venv_found

        archive_path.unlink()

    async def test_archive_includes_git(self, tmp_path):
        """Test that .git directory is included."""
        (tmp_path / "base").mkdir()
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main")

        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)

        dctx = zstd.ZstdDecompressor()
        with (
            archive_path.open("rb") as fh,
            dctx.stream_reader(fh) as reader,
            tarfile.open(fileobj=reader, mode="r|") as tar,
        ):
            members = tar.getnames()
            assert any(".git" in m for m in members)

        archive_path.unlink()

    async def test_archive_compression_ratio(self, tmp_path):
        """Test that compression provides reasonable ratio."""
        (tmp_path / "base").mkdir()
        # Create compressible data
        for i in range(100):
            (tmp_path / f"file_{i}.txt").write_text("A" * 1000)

        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)

        original_size = sum(f.stat().st_size for f in tmp_path.rglob("*") if f.is_file())
        compressed_size = archive_path.stat().st_size

        # Compression ratio should be significant for repetitive data
        ratio = compressed_size / original_size
        assert ratio < 0.1  # Should compress to less than 10%

        archive_path.unlink()


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("GDRIVE_SERVICE_ACCOUNT_EMAIL") and not os.getenv("GDRIVE_CREDENTIALS_FILE"),
    reason="No Google Drive credentials configured (set GDRIVE_SERVICE_ACCOUNT_EMAIL or GDRIVE_CREDENTIALS_FILE)",
)
@pytest.mark.asyncio
class TestE2EBackup:
    """End-to-end tests with real Google Drive credentials.

    These tests require actual Google Drive configuration and will be skipped if:
    - GDRIVE_SERVICE_ACCOUNT_EMAIL is not set (for impersonation)
    - GDRIVE_CREDENTIALS_FILE is not set (for key auth)
    """

    async def test_e2e_full_backup_impersonation(self, tmp_path):
        """Test complete backup flow with service account impersonation."""
        if not os.getenv("GDRIVE_SERVICE_ACCOUNT_EMAIL"):
            pytest.skip("Impersonation not configured")

        # Create minimal repo
        (tmp_path / "base").mkdir()
        (tmp_path / ".env").write_text(f"GDRIVE_SERVICE_ACCOUNT_EMAIL={os.getenv('GDRIVE_SERVICE_ACCOUNT_EMAIL')}\n")
        (tmp_path / "test.txt").write_text("test data")

        # Run full backup
        config = backup_to_gdrive.BackupConfig.load(tmp_path)
        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)
        file_id = await backup_to_gdrive.upload_to_gdrive(archive_path, config)

        assert file_id is not None
        assert len(file_id) > 0

        # Cleanup
        archive_path.unlink()

    async def test_e2e_full_backup_key_file(self, tmp_path):
        """Test complete backup flow with service account key file."""
        if not os.getenv("GDRIVE_CREDENTIALS_FILE"):
            pytest.skip("Key file auth not configured")

        # Create minimal repo
        (tmp_path / "base").mkdir()
        (tmp_path / ".env").write_text(f"GDRIVE_CREDENTIALS_FILE={os.getenv('GDRIVE_CREDENTIALS_FILE')}\n")
        (tmp_path / "test.txt").write_text("test data")

        # Run full backup
        config = backup_to_gdrive.BackupConfig.load(tmp_path)
        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)
        file_id = await backup_to_gdrive.upload_to_gdrive(archive_path, config)

        assert file_id is not None
        assert len(file_id) > 0

        # Cleanup
        archive_path.unlink()


class TestMockBackup:
    """Mock tests for Google Drive API interactions."""

    @pytest.mark.asyncio
    async def test_mock_upload_success(self, tmp_path, mocker):
        """Test upload with mocked successful Google Drive API."""
        # Create test archive
        (tmp_path / "base").mkdir()
        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)

        # Mock config
        config = backup_to_gdrive.BackupConfig(tmp_path)
        config.auth_method = "key"
        config.credentials_file = "/fake/creds.json"

        # Mock FileSubprocess to return successful upload
        mock_result = {
            "success": True,
            "stdout": '{"success": true, "file_id": "fake-file-id-123", "name": "test.tar.zst", "link": "https://drive.google.com/file/d/fake-file-id-123"}',
            "stderr": "",
        }

        with patch.object(backup_to_gdrive.FileSubprocess, "run", return_value=mock_result):
            file_id = await backup_to_gdrive.upload_to_gdrive(archive_path, config)

        assert file_id == "fake-file-id-123"

        archive_path.unlink()

    @pytest.mark.asyncio
    async def test_mock_upload_api_failure(self, tmp_path, mocker):
        """Test upload handling of Google Drive API failure."""
        # Create test archive
        (tmp_path / "base").mkdir()
        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)

        # Mock config
        config = backup_to_gdrive.BackupConfig(tmp_path)
        config.auth_method = "key"
        config.credentials_file = "/fake/creds.json"

        # Mock FileSubprocess to return API error
        mock_result = {
            "success": True,
            "stdout": '{"success": false, "error": "API quota exceeded"}',
            "stderr": "",
        }

        with (
            patch.object(backup_to_gdrive.FileSubprocess, "run", return_value=mock_result),
            pytest.raises(backup_to_gdrive.UploadError) as exc_info,
        ):
            await backup_to_gdrive.upload_to_gdrive(archive_path, config)

        assert "API quota exceeded" in str(exc_info.value)

        archive_path.unlink()

    @pytest.mark.asyncio
    async def test_mock_upload_auth_failure(self, tmp_path, mocker):
        """Test upload handling of authentication failure."""
        # Create test archive
        (tmp_path / "base").mkdir()
        archive_path = await backup_to_gdrive.create_zip_archive(tmp_path)

        # Mock config
        config = backup_to_gdrive.BackupConfig(tmp_path)
        config.auth_method = "impersonation"
        config.service_account_email = "fake@project.iam.gserviceaccount.com"

        # Mock FileSubprocess to return auth error
        mock_result = {
            "success": True,
            "stdout": '{"success": false, "error": "Failed to get default credentials"}',
            "stderr": "",
        }

        with (
            patch.object(backup_to_gdrive.FileSubprocess, "run", return_value=mock_result),
            pytest.raises(backup_to_gdrive.UploadError) as exc_info,
        ):
            await backup_to_gdrive.upload_to_gdrive(archive_path, config)

        assert "Failed to get default credentials" in str(exc_info.value)

        archive_path.unlink()


class TestCleanupLocalZip:
    """Test cleanup_local_zip function."""

    @pytest.mark.asyncio
    async def test_cleanup_deletes_file(self, tmp_path):
        """Test that cleanup deletes the archive file."""
        test_file = tmp_path / "test.tar.zst"
        test_file.write_bytes(b"fake archive data")

        await backup_to_gdrive.cleanup_local_zip(test_file, keep_local=False)

        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_keeps_file_when_requested(self, tmp_path):
        """Test that cleanup keeps file when keep_local=True."""
        test_file = tmp_path / "test.tar.zst"
        test_file.write_bytes(b"fake archive data")

        await backup_to_gdrive.cleanup_local_zip(test_file, keep_local=True)

        assert test_file.exists()
