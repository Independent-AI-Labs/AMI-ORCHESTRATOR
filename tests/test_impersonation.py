#!/usr/bin/env bash
""":'
exec "$(dirname "$0")/../scripts/ami-run" "$0" "$@"
"""

"""Test script to verify service account impersonation works."""

import sys
import traceback
from pathlib import Path

# Add orchestrator root to path for imports
_repo_root = next((p for p in Path(__file__).resolve().parents if (p / "base").exists()), None)
if not _repo_root:
    raise RuntimeError("Unable to locate AMI orchestrator root")
sys.path.insert(0, str(_repo_root))

import google.auth
from google.auth import impersonated_credentials
from google.auth.transport.requests import Request
from loguru import logger


def test_impersonation():
    """Test if service account impersonation works."""
    logger.info("Testing service account impersonation...")

    try:
        # Get source credentials (ADC - Application Default Credentials)
        logger.info("Getting default credentials...")
        source_credentials, project = google.auth.default()
        logger.info(f"Got credentials for project: {project}")
        logger.info(f"Source credentials valid: {source_credentials.valid}")

        # Define the service account to impersonate
        service_account_email = "ami-orchestrator-backup@system-service-475913.iam.gserviceaccount.com"
        logger.info(f"Attempting to impersonate: {service_account_email}")

        # Create impersonated credentials
        logger.info("Creating impersonated credentials...")
        target_credentials = impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=service_account_email,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/drive"],
            lifetime=3600,  # 1 hour
        )

        # Try to refresh the impersonated credentials to test if impersonation works
        logger.info("Refreshing impersonated credentials...")
        target_credentials.refresh(Request())
        logger.info(f"Impersonated credentials valid: {target_credentials.valid}")

        if target_credentials.valid:
            logger.info("SUCCESS: Service account impersonation is working!")
            return True
        logger.error("FAILED: Impersonated credentials are not valid")
        return False

    except Exception as e:
        logger.error(f"FAILED: Service account impersonation error: {e}")

        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = test_impersonation()
    sys.exit(0 if success else 1)
