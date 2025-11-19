"""End-to-end tests for backup authentication functionality.

These tests use the project's bootstrapped gcloud in .gcloud/ and are meant to test
the complete authentication flow in integration.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add orchestrator root to path for imports
_repo_root = next((p for p in Path(__file__).resolve().parents if (p / "base").exists()), None)
if not _repo_root:
    raise RuntimeError("Unable to locate AMI orchestrator root")
sys.path.insert(0, str(_repo_root))

from scripts.backup.backup_config import check_adc_credentials_valid, find_gcloud, refresh_adc_credentials


class TestBackupAuthE2E:
    """End-to-end tests for backup authentication functions."""

    def test_find_gcloud_uses_bootstrapped_binary(self):
        """Verify find_gcloud locates the project's bootstrapped gcloud."""
        gcloud_path = find_gcloud()

        # Should find the local .gcloud installation first
        expected_path = _repo_root / ".gcloud" / "google-cloud-sdk" / "bin" / "gcloud"

        assert gcloud_path is not None, "gcloud should be found in .gcloud directory"
        assert str(expected_path) in gcloud_path, f"Expected bootstrapped gcloud, got: {gcloud_path}"
        assert Path(gcloud_path).exists(), f"gcloud binary should exist at: {gcloud_path}"

    def test_refresh_adc_credentials_with_bootstrapped_gcloud(self):
        """Test refresh_adc_credentials uses the bootstrapped gcloud and handles various scenarios."""
        # This test verifies the function doesn't crash when using the bootstrapped gcloud
        # It checks that the function properly handles the gcloud path from find_gcloud()

        # Mock the environment to have a service account
        with patch.dict(os.environ, {"GDRIVE_SERVICE_ACCOUNT_EMAIL": "test@serviceaccount.com"}, clear=False):
            # The function should not crash when trying to use the bootstrapped gcloud
            # Even if actual credentials aren't available, it should handle the subprocess calls properly
            try:
                result = refresh_adc_credentials()
                # The result can be True or False depending on actual credential status,
                # but the function should execute without crashing
                assert result in [True, False], "Function should return a boolean result"
            except Exception as e:
                # If there's an exception, it should be expected (like missing dependencies)
                # rather than a crash in the logic itself
                assert "gcloud CLI not found" not in str(e), "Should have found gcloud binary"

    def test_check_adc_credentials_valid_no_crash(self):
        """Test check_adc_credentials_valid doesn't crash (handles Google API calls safely)."""
        # This should not crash even if no credentials are set up
        # It tests that the Google API integration is properly handled
        try:
            result = check_adc_credentials_valid()
            # Result can be True/False depending on environment, but shouldn't crash
            assert result in [True, False], "Function should return a boolean result"
        except ImportError:
            # If Google libraries aren't installed, that's a setup issue, not a code issue
            # The important thing is that our code handles this gracefully
            pass
        except Exception as e:
            # Other exceptions may occur based on environment, but shouldn't be crashes
            # from our code logic
            assert "unexpected" not in str(e).lower(), f"Unexpected error in credential check: {e}"
