#!/usr/bin/env bash
set -euo pipefail

# Pandoc Bootstrap Script for AMI-ORCHESTRATOR
# Downloads and installs Pandoc in the .boot-linux environment ONLY
# This script ensures Pandoc is available without requiring system-wide installation
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

PANDOC_VERSION="3.1.11.1"  # Use the latest stable version
PANDOC_DIR="${VENV_DIR}/pandoc"

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
    log_error "This script only supports Linux. For other platforms, install Pandoc manually."
    exit 1
fi

# Detect architecture
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64|amd64)
        PANDOC_ARCH="amd64"
        ;;
    aarch64|arm64)
        PANDOC_ARCH="arm64"
        ;;
    *)
        log_error "Unsupported architecture: ${ARCH}"
        exit 1
        ;;
esac

log_info "Bootstrapping Pandoc ${PANDOC_VERSION} for ${ARCH}"

# Create pandoc directory structure
mkdir -p "${PANDOC_DIR}"/bin

# Download Pandoc from GitHub releases
PANDOC_URL="https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-${PANDOC_ARCH}.tar.gz"
PANDOC_TARBALL="${PANDOC_DIR}/pandoc.tar.gz"

log_info "Downloading Pandoc from ${PANDOC_URL}"

if command -v curl &> /dev/null; then
    curl -L -o "${PANDOC_TARBALL}" "${PANDOC_URL}"
elif command -v wget &> /dev/null; then
    wget -O "${PANDOC_TARBALL}" "${PANDOC_URL}"
else
    log_error "Neither curl nor wget found. Please install one of them."
    exit 1
fi

# Extract Pandoc
log_info "Extracting Pandoc to ${PANDOC_DIR}"
tar -xzf "${PANDOC_TARBALL}" -C "${PANDOC_DIR}" --strip-components=1

# Create symlink in venv/bin
log_info "Creating symlink in ${VENV_DIR}/bin"
if [[ -f "${PANDOC_DIR}/bin/pandoc" ]]; then
    ln -sf "${PANDOC_DIR}/bin/pandoc" "${VENV_DIR}/bin/pandoc"
else
    # Alternative location in extracted archive
    if [[ -f "${PANDOC_DIR}/pandoc-${PANDOC_VERSION}/bin/pandoc" ]]; then
        ln -sf "${PANDOC_DIR}/pandoc-${PANDOC_VERSION}/bin/pandoc" "${VENV_DIR}/bin/pandoc"
    else
        log_error "Pandoc binary not found in expected location"
        exit 1
    fi
fi

# Clean up
rm -f "${PANDOC_TARBALL}"

# Verify installation
log_info "Verifying Pandoc installation"
if "${VENV_DIR}/bin/pandoc" --version; then
    log_info "Pandoc installed successfully: $(${VENV_DIR}/bin/pandoc --version)"
else
    log_error "Pandoc installation verification failed"
    exit 1
fi

log_info "Pandoc bootstrap complete!"
log_info "Installed components:"
log_info "  - Pandoc ${PANDOC_VERSION}"
log_info "  - Binary: ${VENV_DIR}/bin/pandoc"
log_info ""
log_info "To use Pandoc:"
log_info "  1. Run: ami-run pandoc [args] (Pandoc auto-available)"
log_info "  2. Or use scripts directly that need Pandoc"
