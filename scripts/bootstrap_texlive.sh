#!/usr/bin/env bash
set -euo pipefail

# TeXLive Bootstrap Script for AMI-ORCHESTRATOR
# Downloads and installs minimal TeXLive in the .boot-linux environment ONLY
# This script ensures pdflatex and related tools are available without system-wide installation
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

# Use a minimal texlive scheme to keep size reasonable
TEXLIVE_DIR="${VENV_DIR}/texlive"
INSTALLER_DIR="${TEXLIVE_DIR}/installer"

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
    log_error "This script only supports Linux. For other platforms, install TeXLive manually."
    exit 1
fi

log_info "Bootstrapping minimal TeXLive for PDF generation"

# Create texlive directory structure
mkdir -p "${INSTALLER_DIR}"

# Download the TeXLive installer
log_info "Downloading TeXLive installer..."
INSTALLER_URL="https://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz"
INSTALLER_TARBALL="${INSTALLER_DIR}/install-tl-unx.tar.gz"

if command -v curl &> /dev/null; then
    curl -L -o "${INSTALLER_TARBALL}" "${INSTALLER_URL}"
elif command -v wget &> /dev/null; then
    wget -O "${INSTALLER_TARBALL}" "${INSTALLER_URL}"
else
    log_error "Neither curl nor wget found. Please install one of them."
    exit 1
fi

# Extract the installer
log_info "Extracting TeXLive installer..."
cd "${INSTALLER_DIR}"
tar -xzf "${INSTALLER_TARBALL}"

# Find the installer directory (it has a date in the name)
INSTALLER_SUBDIR=$(find . -maxdepth 1 -type d -name "install-tl-*" | head -n1)

if [[ -z "${INSTALLER_SUBDIR}" ]]; then
    log_error "Could not find installer directory"
    exit 1
fi

cd "${INSTALLER_SUBDIR}"

# Create a profile file for automated installation
mkdir -p "${TEXLIVE_DIR}/texmf"
cat > texlive.profile << EOF
selected_scheme scheme-minimal
TEXDIR ${TEXLIVE_DIR}/texmf
TEXMFCONFIG ${TEXLIVE_DIR}/texmf-config
TEXMFVAR ${TEXLIVE_DIR}/texmf-var
TEXMFHOME ${TEXLIVE_DIR}/texmf-home
TEXMFLOCAL ${TEXLIVE_DIR}/texmf-local
option_doc 0
option_src 0
binary_x86_64-linux 1
instopt_adjustpath 0
instopt_letter 0
tlpdbopt_autobackup 0
EOF

# Run the installer with environment variables to avoid system directories
export TEXLIVE_INSTALL_PREFIX="${TEXLIVE_DIR}"
export TEXDIR="${TEXLIVE_DIR}/texmf"
export TEXMFCONFIG="${TEXLIVE_DIR}/texmf-config"
export TEXMFVAR="${TEXLIVE_DIR}/texmf-var"
export TEXMFHOME="${TEXLIVE_DIR}/texmf-home"
export TEXMFLOCAL="${TEXLIVE_DIR}/texmf-local"

log_info "Installing minimal TeXLive (this may take several minutes)..."
./install-tl --profile=texlive.profile --no-gui --texdir="${TEXLIVE_DIR}/texmf"

# Install additional packages needed for PDF generation
BINARY_BASE_DIR="${TEXLIVE_DIR}/texmf/bin"
if [[ -f "${BINARY_BASE_DIR}/x86_64-linux/tlmgr" ]]; then
    # Try to install additional packages, but don't fail if some packages don't exist
    "${BINARY_BASE_DIR}/x86_64-linux/tlmgr" install collection-latex collection-latexrecommended || true
    "${BINARY_BASE_DIR}/x86_64-linux/tlmgr" install latex-bin xetex fontspec montserrat lato noto || true  # lualatex may already be installed as part of xetex
elif [[ -f "${BINARY_BASE_DIR}/aarch64-linux/tlmgr" ]]; then
    "${BINARY_BASE_DIR}/aarch64-linux/tlmgr" install collection-latex collection-latexrecommended || true
    "${BINARY_BASE_DIR}/aarch64-linux/tlmgr" install latex-bin xetex fontspec montserrat lato noto || true
else
    # Look for tlmgr in any architecture directory
    for arch_dir in "${BINARY_BASE_DIR}"/*; do
        if [[ -d "$arch_dir" && -f "$arch_dir/tlmgr" ]]; then
            "$arch_dir/tlmgr" install collection-latex collection-latexrecommended || true
            "$arch_dir/tlmgr" install latex-bin xetex fontspec montserrat lato noto || true
            break
        fi
    done
fi

# Create symlinks in venv/bin for the necessary binaries
log_info "Creating symlinks in ${VENV_DIR}/bin"

# Find the binary directory (it may vary by architecture)
BINARY_DIR=""
for dir in "${TEXLIVE_DIR}/texmf/bin/"*; do
    if [[ -d "$dir" && -f "$dir/pdflatex" ]]; then
        BINARY_DIR="$dir"
        break
    fi
done

if [[ -z "${BINARY_DIR}" ]]; then
    log_error "Could not find TeXLive binary directory with pdflatex"
    exit 1
fi

log_info "Found binaries in: ${BINARY_DIR}"

# Create symlinks for essential PDF generation tools
for binary in pdflatex xelatex lualatex latex kpsewhich mktexlsr; do
    if [[ -f "${BINARY_DIR}/${binary}" ]]; then
        ln -sf "${BINARY_DIR}/${binary}" "${VENV_DIR}/bin/${binary}"
        log_info "Created symlink for ${binary}"
    fi
done

# Set up environment for TeXLive
export PATH="${BINARY_DIR}:${PATH}"
export TEXMFCNF="${TEXLIVE_DIR}/texmf/texmf.cnf"

# Verify installation
log_info "Verifying pdflatex installation"
if "${VENV_DIR}/bin/pdflatex" --version >/dev/null 2>&1; then
    log_info "pdflatex installed successfully:"
    "${VENV_DIR}/bin/pdflatex" --version | head -n 1
else
    log_error "pdflatex installation verification failed"
    exit 1
fi

# Clean up installer
rm -rf "${INSTALLER_DIR}"

log_info "TeXLive bootstrap complete!"
log_info "Installed components:"
log_info "  - pdflatex"
log_info "  - xelatex"
log_info "  - lualatex"
log_info "  - latex"
log_info "  - Binary: ${VENV_DIR}/bin/[engine-name]"
log_info ""
log_info "To use TeXLive PDF engines:"
log_info "  1. Run: ami-run pdflatex [args] (Engines auto-available)"
log_info "  2. Or use scripts directly that need PDF engines"
