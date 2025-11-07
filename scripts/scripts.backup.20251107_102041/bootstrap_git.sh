#!/usr/bin/env bash
set -euo pipefail

# Git Bootstrap Script for AMI-ORCHESTRATOR
# Downloads Git from Ubuntu packages and installs in venv
# Creates self-contained git installation for git-daemon

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
GIT_DIR="${VENV_DIR}/git"

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
    log_error "This script only supports Linux. For other platforms, use system git."
    exit 1
fi

# Detect architecture
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64|amd64)
        GIT_ARCH="amd64"
        ;;
    aarch64|arm64)
        GIT_ARCH="arm64"
        ;;
    *)
        log_error "Unsupported architecture: ${ARCH}"
        exit 1
        ;;
esac

log_info "Bootstrapping Git for ${ARCH}"

# Create git directory structure
mkdir -p "${GIT_DIR}"/{bin,libexec}

# Download git packages using apt
log_info "Downloading Git packages..."

cd "${GIT_DIR}"
apt download git git-man 2>/dev/null || {
    log_error "Failed to download git packages"
    log_error "Ensure apt is configured and you have network access"
    exit 1
}

# Rename downloaded files to predictable names
mv git_*.deb git.deb
mv git-man_*.deb git-man.deb

# Extract packages without installing system-wide
log_info "Extracting Git binaries..."

# Extract git package
ar x git.deb

# Extract main git binary
tar -xf data.tar.* --strip-components=2 -C "${GIT_DIR}" \
    ./usr/bin/git \
    2>/dev/null || true

# Extract git-core binaries (all git subcommands like git-daemon)
tar -xf data.tar.* --strip-components=3 -C "${GIT_DIR}/libexec" \
    ./usr/lib/git-core/ 2>/dev/null || true

log_info "✓ Git binaries extracted"

# Clean up
rm -f "${GIT_DIR}"/*.deb
rm -f "${GIT_DIR}"/{control.tar.*,data.tar.*,debian-binary}

# Get installed git version
INSTALLED_VERSION=$("${GIT_DIR}/bin/git" --version 2>&1 | awk '{print $3}')

log_info "Git bootstrap complete!"
log_info "Installed components:"
log_info "  - Git ${INSTALLED_VERSION}"
log_info "  - Binary: ${GIT_DIR}/bin/git"
log_info "  - Git core: ${GIT_DIR}/libexec/git-core/"
log_info ""
log_info "Git is now available in venv"
log_info "Symlink will be created at .venv/bin/git"
