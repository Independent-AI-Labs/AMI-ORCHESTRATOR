#!/usr/bin/env bash

# Script to create the bootstrap environment (.boot-linux)
# This contains only the essential tools needed to bootstrap the rest of the system: Python, uv
# Uses standalone uv to install Python without requiring system Python

set -euo pipefail

# Logging functions
log_info() {
    echo "$1" >&2
}

log_error() {
    echo "ERROR: $1" >&2
}

log_warning() {
    echo "WARNING: $1" >&2
}

log_success() {
    echo "✓ $1" >&2
}

# Store the original directory to create .boot-linux there
ORIGINAL_DIR="$PWD"
BOOT_DIR="$ORIGINAL_DIR/.boot-linux"

create_bootstrap_environment() {
    log_info "Creating bootstrap environment in $BOOT_DIR..."

    # Check if bootstrap environment already exists
    if [ -d "$BOOT_DIR" ]; then
        log_info "Bootstrap environment already exists at $BOOT_DIR"
        return 0
    fi

    # Download uv binary directly without system installation
    log_info "Downloading portable uv binary..."
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"

    # Detect architecture and OS
    ARCH=$(uname -m)
    OS=$(uname -s)

    case $OS in
        Linux*)
            PLATFORM="unknown-linux-gnu"
            ;;
        Darwin*)
            PLATFORM="apple-darwin"
            ;;
        *)
            log_error "Unsupported platform: $OS"
            cd - > /dev/null
            rm -rf "$TEMP_DIR"
            return 1
            ;;
    esac

    case $ARCH in
        x86_64*)
            ARCH="x86_64"
            ;;
        arm64*|aarch64*)
            ARCH="aarch64"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            cd - > /dev/null
            rm -rf "$TEMP_DIR"
            return 1
            ;;
    esac

    # Download uv binary based on platform
    UV_BINARY_NAME="uv-$ARCH-$PLATFORM"

    # Define file extension based on platform
    if [[ "$PLATFORM" == "unknown-linux-gnu" || "$PLATFORM" == "unknown-linux-musl" || "$PLATFORM" == "apple-darwin" ]]; then
        # Linux and macOS versions are distributed as .tar.gz
        UV_FILE_NAME="$UV_BINARY_NAME.tar.gz"
        curl -LsSf "https://github.com/astral-sh/uv/releases/latest/download/$UV_FILE_NAME" -o "$UV_FILE_NAME" || {
            # If latest doesn't work, try using a specific version
            log_info "Latest version failed, trying stable version..."
            # Get the latest release tag
            VERSION=$(curl -s https://api.github.com/repos/astral-sh/uv/releases/latest | grep '"tag_name"' | sed -E 's/.*"tag_name": "([^"]+)",.*/\1/')
            # Remove the 'v' prefix if it exists
            VERSION=${VERSION#v}
            curl -LsSf "https://github.com/astral-sh/uv/releases/download/$VERSION/$UV_FILE_NAME" -o "$UV_FILE_NAME"
        }
        tar -xzf "$UV_FILE_NAME"
        # The tarball contains a directory with the uv binary inside
        # Move the binary from the subdirectory to current directory
        if [ -d "$UV_BINARY_NAME" ]; then
            # Use a temporary rename to avoid path conflicts
            mv "$UV_BINARY_NAME/uv" "temp_uv_binary"
            rm -rf "$UV_BINARY_NAME"  # Remove the directory
            mv "temp_uv_binary" "$UV_BINARY_NAME"  # Rename the binary to the expected name
        fi
    else
        # Windows version is distributed as .zip
        UV_FILE_NAME="$UV_BINARY_NAME.zip"
        curl -LsSf "https://github.com/astral-sh/uv/releases/latest/download/$UV_FILE_NAME" -o "$UV_FILE_NAME" || {
            # If latest doesn't work, try using a specific version
            log_info "Latest version failed, trying stable version..."
            # Get the latest release tag
            VERSION=$(curl -s https://api.github.com/repos/astral-sh/uv/releases/latest | grep '"tag_name"' | sed -E 's/.*"tag_name": "([^"]+)",.*/\1/')
            # Remove the 'v' prefix if it exists
            VERSION=${VERSION#v}
            curl -LsSf "https://github.com/astral-sh/uv/releases/download/$VERSION/$UV_FILE_NAME" -o "$UV_FILE_NAME"
        }
        unzip "$UV_FILE_NAME"
    fi

    # Make it executable
    chmod +x "$UV_BINARY_NAME"

    # Use the downloaded binary to bootstrap
    log_info "Installing Python 3.12 and creating bootstrap environment with portable uv..."
    "./$UV_BINARY_NAME" python install 3.12
    "./$UV_BINARY_NAME" venv --python 3.12 --seed "$BOOT_DIR"

    # Install uv itself in the bootstrap environment
    log_info "Installing uv into the bootstrap environment..."
    "$BOOT_DIR/bin/python" -m pip install uv

    # Verify essential tools are available in the bootstrap environment
    if [ ! -x "$BOOT_DIR/bin/python" ]; then
        log_error "Python not available in bootstrap environment"
        cd - > /dev/null
        rm -rf "$TEMP_DIR"
        return 1
    fi

    if [ ! -x "$BOOT_DIR/bin/uv" ]; then
        log_error "uv not available in bootstrap environment"
        cd - > /dev/null
        rm -rf "$TEMP_DIR"
        return 1
    fi

    # Clean up
    cd - > /dev/null
    rm -rf "$TEMP_DIR"

    log_success "Bootstrap environment created successfully at $BOOT_DIR"
    log_info "Essential tools installed: python, uv"

    return 0
}

# Run the bootstrap creation
create_bootstrap_environment