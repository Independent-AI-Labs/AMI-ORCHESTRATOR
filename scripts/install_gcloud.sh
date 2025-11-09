#!/usr/bin/env bash
# Install Google Cloud CLI locally to project
#
# Downloads and installs gcloud CLI to .gcloud/ directory
# This allows the backup script to use service account impersonation
# without requiring system-wide gcloud installation.
#
# Usage: ./scripts/install_gcloud.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
GCLOUD_DIR="$ROOT_DIR/.gcloud"
GCLOUD_SDK_DIR="$GCLOUD_DIR/google-cloud-sdk"

echo "================================"
echo "Google Cloud CLI Local Installer"
echo "================================"
echo

# Detect platform
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$PLATFORM" in
    linux)
        if [ "$ARCH" = "x86_64" ]; then
            ARCHIVE_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz"
            ARCHIVE_FILE="google-cloud-cli-linux-x86_64.tar.gz"
        elif [ "$ARCH" = "aarch64" ]; then
            ARCHIVE_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-arm.tar.gz"
            ARCHIVE_FILE="google-cloud-cli-linux-arm.tar.gz"
        else
            echo "Error: Unsupported Linux architecture: $ARCH"
            exit 1
        fi
        ;;
    darwin)
        if [ "$ARCH" = "x86_64" ]; then
            ARCHIVE_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-x86_64.tar.gz"
            ARCHIVE_FILE="google-cloud-cli-darwin-x86_64.tar.gz"
        elif [ "$ARCH" = "arm64" ]; then
            ARCHIVE_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-arm.tar.gz"
            ARCHIVE_FILE="google-cloud-cli-darwin-arm.tar.gz"
        else
            echo "Error: Unsupported macOS architecture: $ARCH"
            exit 1
        fi
        ;;
    *)
        echo "Error: Unsupported platform: $PLATFORM"
        echo "Please install gcloud manually: https://cloud.google.com/sdk/docs/install"
        exit 1
        ;;
esac

echo "Platform: $PLATFORM ($ARCH)"
echo "Download URL: $ARCHIVE_URL"
echo "Install directory: $GCLOUD_DIR"
echo

# Check if already installed
if [ -f "$GCLOUD_SDK_DIR/bin/gcloud" ]; then
    CURRENT_VERSION=$("$GCLOUD_SDK_DIR/bin/gcloud" version --format="value(Google Cloud SDK)" 2>/dev/null || echo "unknown")
    echo "gcloud CLI already installed (version: $CURRENT_VERSION)"

    # Check if running non-interactively (from ami-agent or CI)
    if [ -t 0 ]; then
        # Interactive mode - ask for confirmation
        echo
        read -p "Reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled"
            exit 0
        fi
    else
        # Non-interactive mode - skip reinstall
        echo "Running in non-interactive mode, keeping existing installation"
        exit 0
    fi

    echo "Removing existing installation..."
    rm -rf "$GCLOUD_SDK_DIR"
fi

# Create .gcloud directory
mkdir -p "$GCLOUD_DIR"

# Download gcloud CLI
echo "Downloading Google Cloud CLI..."
if ! curl -fSL "$ARCHIVE_URL" -o "$GCLOUD_DIR/$ARCHIVE_FILE"; then
    echo "Error: Failed to download gcloud CLI"
    exit 1
fi

echo "✓ Downloaded $ARCHIVE_FILE"
echo

# Extract archive
echo "Extracting archive..."
if ! tar -xzf "$GCLOUD_DIR/$ARCHIVE_FILE" -C "$GCLOUD_DIR"; then
    echo "Error: Failed to extract archive"
    rm -f "$GCLOUD_DIR/$ARCHIVE_FILE"
    exit 1
fi

echo "✓ Extracted to $GCLOUD_SDK_DIR"
echo

# Remove archive
rm -f "$GCLOUD_DIR/$ARCHIVE_FILE"

# Run install script non-interactively
echo "Running gcloud install script..."
if ! "$GCLOUD_SDK_DIR/install.sh" \
    --usage-reporting=false \
    --command-completion=false \
    --path-update=false \
    --quiet; then
    echo "Error: gcloud install script failed"
    exit 1
fi

echo
echo "✓ Installation complete"
echo

# Verify installation
GCLOUD_BIN="$GCLOUD_SDK_DIR/bin/gcloud"
if [ -x "$GCLOUD_BIN" ]; then
    VERSION=$("$GCLOUD_BIN" version --format="value(Google Cloud SDK)" 2>/dev/null || echo "unknown")
    echo "Installed version: $VERSION"
    echo "gcloud path: $GCLOUD_BIN"
else
    echo "Error: gcloud binary not found or not executable"
    exit 1
fi

echo
echo "================================"
echo "Next Steps:"
echo "================================"
echo
echo "1. Authenticate with your Google account:"
echo "   $GCLOUD_BIN auth application-default login"
echo
echo "2. Grant impersonation permission (if using service account):"
echo "   $GCLOUD_BIN iam service-accounts add-iam-policy-binding \\"
echo "     SERVICE_ACCOUNT_EMAIL \\"
echo "     --member=\"user:YOUR_EMAIL\" \\"
echo "     --role=\"roles/iam.serviceAccountTokenCreator\""
echo
echo "3. Configure .env with service account email:"
echo "   GDRIVE_SERVICE_ACCOUNT_EMAIL=backup@project.iam.gserviceaccount.com"
echo
echo "4. Run backup:"
echo "   ./scripts/backup_to_gdrive.py"
echo
