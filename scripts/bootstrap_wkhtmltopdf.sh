#!/usr/bin/env bash
set -euo pipefail

# wkhtmltopdf Bootstrap Script for AMI-ORCHESTRATOR
# Downloads and installs wkhtmltopdf in the .boot-linux environment ONLY
# This script ensures wkhtmltopdf is available without requiring system-wide installation
# FORCE INSTALLS TO .boot-linux - NO FALLBACKS, NO .venv, ONLY .boot-linux

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Force installation to .boot-linux only - no alternatives
if [ -n "${BOOT_LINUX_DIR:-}" ]; then
    VENV_DIR="${BOOT_LINUX_DIR}"
else
    # Default to .boot-linux in the repo root - this is the ONLY supported location
    VENV_DIR="${REPO_ROOT}/.boot-linux"
fi

WKHTMLTOPDF_VERSION="0.12.6.1"  # Use a stable version
WKHTMLTOPDF_DIR="${VENV_DIR}/wkhtmltopdf"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if running on Linux
if [[ "$(uname -s)" != "Linux" ]]; then
    log_error "This script only supports Linux. For other platforms, install wkhtmltopdf manually."
    exit 1
fi

# Detect architecture
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64|amd64)
        WKHTMLTOPDF_ARCH="amd64"
        ;;
    aarch64|arm64)
        WKHTMLTOPDF_ARCH="arm64"
        ;;
    *)
        log_error "Unsupported architecture: ${ARCH}"
        exit 1
        ;;
esac

log_info "Bootstrapping wkhtmltopdf ${WKHTMLTOPDF_VERSION} for ${ARCH}"

# Create wkhtmltopdf directory structure
mkdir -p "${WKHTMLTOPDF_DIR}"/bin

# Download wkhtmltopdf from GitHub releases or official sources
WKHTMLTOPDF_URL="https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTMLTOPDF_VERSION}/wkhtmltopdf_${WKHTMLTOPDF_VERSION}_linux_${WKHTMLTOPDF_ARCH}.deb"

log_info "Downloading wkhtmltopdf from ${WKHTMLTOPDF_URL}"

if command -v curl &> /dev/null; then
    curl -L -o "${WKHTMLTOPDF_DIR}/wkhtmltopdf.deb" "${WKHTMLTOPDF_URL}"
elif command -v wget &> /dev/null; then
    wget -O "${WKHTMLTOPDF_DIR}/wkhtmltopdf.deb" "${WKHTMLTOPDF_URL}"
else
    log_error "Neither curl nor wget found. Please install one of them."
    exit 1
fi

# Extract the package
cd "${WKHTMLTOPDF_DIR}"
ar x wkhtmltopdf.deb
tar -xf data.tar.* --strip-components=2 -C "${WKHTMLTOPDF_DIR}/bin" \
    ./usr/local/bin/wkhtmltopdf ./usr/bin/wkhtmltopdf 2>/dev/null || true

# Clean up if the binary is found in different locations
if [[ ! -f "${WKHTMLTOPDF_DIR}/bin/wkhtmltopdf" ]]; then
    # Try alternative paths
    tar -xf data.tar.* --strip-components=3 -C "${WKHTMLTOPDF_DIR}/bin" \
        ./usr/local/bin/wkhtmltopdf 2>/dev/null || true
fi

if [[ ! -f "${WKHTMLTOPDF_DIR}/bin/wkhtmltopdf" ]]; then
    # Try another alternative
    tar -xf data.tar.* --strip-components=1 -C "${WKHTMLTOPDF_DIR}" \
        ./usr/bin/wkhtmltopdf 2>/dev/null || true
fi

# Create symlink in venv/bin
log_info "Creating symlink in ${VENV_DIR}/bin"
if [[ -f "${WKHTMLTOPDF_DIR}/bin/wkhtmltopdf" ]]; then
    ln -sf "${WKHTMLTOPDF_DIR}/bin/wkhtmltopdf" "${VENV_DIR}/bin/wkhtmltopdf"
elif [[ -f "${WKHTMLTOPDF_DIR}/wkhtmltopdf" ]]; then
    ln -sf "${WKHTMLTOPDF_DIR}/wkhtmltopdf" "${VENV_DIR}/bin/wkhtmltopdf"
else
    log_error "wkhtmltopdf binary not found in expected location"
    log_info "Available files in ${WKHTMLTOPDF_DIR}:"
    ls -la "${WKHTMLTOPDF_DIR}" 2>&1 || true
    exit 1
fi

# Clean up
rm -f "${WKHTMLTOPDF_DIR}/wkhtmltopdf.deb"
rm -f "${WKHTMLTOPDF_DIR}"/*.tar.*

# Verify installation
log_info "Verifying wkhtmltopdf installation"
if "${VENV_DIR}/bin/wkhtmltopdf" --version; then
    log_info "wkhtmltopdf installed successfully:"
    "${VENV_DIR}/bin/wkhtmltopdf" --version
else
    log_error "wkhtmltopdf installation verification failed"
    exit 1
fi

log_info "wkhtmltopdf bootstrap complete!"
log_info "Installed components:"
log_info "  - wkhtmltopdf ${WKHTMLTOPDF_VERSION}"
log_info "  - Binary: ${VENV_DIR}/bin/wkhtmltopdf"
log_info ""
log_info "To use wkhtmltopdf:"
log_info "  1. Run: ami-run wkhtmltopdf [args] (wkhtmltopdf auto-available)"
log_info "  2. Or use scripts directly that need wkhtmltopdf"
