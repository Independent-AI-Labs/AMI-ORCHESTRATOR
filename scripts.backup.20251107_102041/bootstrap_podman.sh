#!/usr/bin/env bash
set -euo pipefail

# Podman Bootstrap Script for AMI-ORCHESTRATOR
# Downloads and installs Podman and podman-compose in the virtual environment
# This script ensures Podman is available without requiring system-wide installation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
PODMAN_DIR="${VENV_DIR}/podman"
PODMAN_VERSION="5.6.2"
PODMAN_COMPOSE_VERSION="1.5.0"
CONMON_VERSION="2.1.13"
NETAVARK_VERSION="1.16.1"
AARDVARK_DNS_VERSION="1.16.0"

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
    log_error "This script only supports Linux. For other platforms, install Podman manually."
    exit 1
fi

# Detect architecture
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64)
        PODMAN_ARCH="amd64"
        ;;
    aarch64|arm64)
        PODMAN_ARCH="arm64"
        ;;
    *)
        log_error "Unsupported architecture: ${ARCH}"
        exit 1
        ;;
esac

log_info "Bootstrapping Podman ${PODMAN_VERSION} for ${ARCH}"

# Check and install system dependencies for rootless mode
log_info "Checking system dependencies for Podman rootless mode"

# Check for uidmap (newuidmap/newgidmap)
if ! command -v newuidmap &> /dev/null; then
    log_warn "newuidmap not found - required for Podman rootless mode"
    log_info "Installing uidmap package (requires sudo)..."
    if sudo apt-get update && sudo apt-get install -y uidmap; then
        log_info "✓ uidmap package installed successfully"
    else
        log_error "Failed to install uidmap package"
        log_error "Please install manually: sudo apt-get install uidmap"
        exit 1
    fi
else
    log_info "✓ newuidmap found at $(command -v newuidmap)"
fi

# Check for slirp4netns (rootless networking)
if ! command -v slirp4netns &> /dev/null; then
    log_warn "slirp4netns not found - required for Podman rootless networking"
    log_info "Installing slirp4netns package (requires sudo)..."
    if sudo apt-get install -y slirp4netns; then
        log_info "✓ slirp4netns package installed successfully"
    else
        log_error "Failed to install slirp4netns package"
        log_error "Please install manually: sudo apt-get install slirp4netns"
        exit 1
    fi
else
    log_info "✓ slirp4netns found at $(command -v slirp4netns)"
fi

# Create venv if it doesn't exist
if [[ ! -d "${VENV_DIR}" ]]; then
    log_info "Creating virtual environment at ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
fi

# Create Podman directory
mkdir -p "${PODMAN_DIR}"/{bin,lib}

# Download Podman static binary
PODMAN_URL="https://github.com/mgoltzsche/podman-static/releases/download/v${PODMAN_VERSION}/podman-linux-${PODMAN_ARCH}.tar.gz"
PODMAN_TARBALL="${PODMAN_DIR}/podman.tar.gz"

log_info "Downloading Podman from ${PODMAN_URL}"
if command -v curl &> /dev/null; then
    curl -L -o "${PODMAN_TARBALL}" "${PODMAN_URL}"
elif command -v wget &> /dev/null; then
    wget -O "${PODMAN_TARBALL}" "${PODMAN_URL}"
else
    log_error "Neither curl nor wget found. Please install one of them."
    exit 1
fi

# Extract Podman
log_info "Extracting Podman to ${PODMAN_DIR}"
tar -xzf "${PODMAN_TARBALL}" -C "${PODMAN_DIR}" --strip-components=1

# Download conmon
CONMON_URL="https://github.com/containers/conmon/releases/download/v${CONMON_VERSION}/conmon.${PODMAN_ARCH}"
CONMON_BIN="${PODMAN_DIR}/bin/conmon"

log_info "Downloading conmon from ${CONMON_URL}"
if command -v curl &> /dev/null; then
    curl -L -o "${CONMON_BIN}" "${CONMON_URL}"
elif command -v wget &> /dev/null; then
    wget -O "${CONMON_BIN}" "${CONMON_URL}"
fi
chmod +x "${CONMON_BIN}"

# Download netavark (networking)
NETAVARK_URL="https://github.com/containers/netavark/releases/download/v${NETAVARK_VERSION}/netavark.gz"
NETAVARK_BIN="${PODMAN_DIR}/bin/netavark"

log_info "Downloading netavark from ${NETAVARK_URL}"
if command -v curl &> /dev/null; then
    curl -L "${NETAVARK_URL}" | gunzip > "${NETAVARK_BIN}"
elif command -v wget &> /dev/null; then
    wget -O - "${NETAVARK_URL}" | gunzip > "${NETAVARK_BIN}"
fi
chmod +x "${NETAVARK_BIN}"

# Download aardvark-dns (DNS for netavark)
AARDVARK_URL="https://github.com/containers/aardvark-dns/releases/download/v${AARDVARK_DNS_VERSION}/aardvark-dns.gz"
AARDVARK_BIN="${PODMAN_DIR}/bin/aardvark-dns"

log_info "Downloading aardvark-dns from ${AARDVARK_URL}"
if command -v curl &> /dev/null; then
    curl -L "${AARDVARK_URL}" | gunzip > "${AARDVARK_BIN}"
elif command -v wget &> /dev/null; then
    wget -O - "${AARDVARK_URL}" | gunzip > "${AARDVARK_BIN}"
fi
chmod +x "${AARDVARK_BIN}"

# Create symlinks in venv/bin
log_info "Creating symlinks in ${VENV_DIR}/bin"
for binary in podman conmon netavark aardvark-dns; do
    if [[ -f "${PODMAN_DIR}/usr/local/bin/${binary}" ]]; then
        ln -sf "${PODMAN_DIR}/usr/local/bin/${binary}" "${VENV_DIR}/bin/${binary}"
    elif [[ -f "${PODMAN_DIR}/bin/${binary}" ]]; then
        ln -sf "${PODMAN_DIR}/bin/${binary}" "${VENV_DIR}/bin/${binary}"
    fi
done

# Create symlink for rootlessport (required for port forwarding in rootless mode)
if [[ -f "${PODMAN_DIR}/usr/local/lib/podman/rootlessport" ]]; then
    ln -sf "${PODMAN_DIR}/usr/local/lib/podman/rootlessport" "${VENV_DIR}/bin/rootlessport"
fi

# Note: podman-compose is installed via pyproject.toml dependencies
# Run: uv sync or ami-uv sync to install it

# Create Docker alias symlinks for seamless migration
log_info "Creating Docker alias symlinks"
ln -sf "${VENV_DIR}/bin/podman" "${VENV_DIR}/bin/docker"
ln -sf "${VENV_DIR}/bin/podman-compose" "${VENV_DIR}/bin/docker-compose"

# Create containers.conf to point Podman to helper binaries in venv
log_info "Configuring Podman to use venv helper binaries"
CONTAINERS_CONF_DIR="${HOME}/.config/containers"
CONTAINERS_CONF="${CONTAINERS_CONF_DIR}/containers.conf"
mkdir -p "${CONTAINERS_CONF_DIR}"

cat > "${CONTAINERS_CONF}" <<EOF
[engine]
helper_binaries_dir = ["${VENV_DIR}/bin"]
conmon_path = ["${VENV_DIR}/bin/conmon"]

[network]
network_backend = "netavark"
default_rootless_network_cmd = "slirp4netns"
EOF

# Create registries.conf for image pulling
REGISTRIES_CONF="${CONTAINERS_CONF_DIR}/registries.conf"
cat > "${REGISTRIES_CONF}" <<EOF
unqualified-search-registries = ["docker.io"]

[[registry]]
location = "docker.io"
EOF

log_info "✓ Created ${REGISTRIES_CONF}"

# Create policy.json for image signature verification
POLICY_JSON="${CONTAINERS_CONF_DIR}/policy.json"
cat > "${POLICY_JSON}" <<EOF
{
  "default": [
    {
      "type": "insecureAcceptAnything"
    }
  ],
  "transports": {
    "docker-daemon": {
      "": [{"type": "insecureAcceptAnything"}]
    }
  }
}
EOF

log_info "✓ Created ${POLICY_JSON}"

log_info "✓ Created ${CONTAINERS_CONF}"

# Verify installation
log_info "Verifying Podman installation"
if "${VENV_DIR}/bin/podman" --version; then
    log_info "Podman installed successfully: $(${VENV_DIR}/bin/podman --version)"
else
    log_error "Podman installation verification failed"
    exit 1
fi

# Verify podman-compose with PATH set
export PATH="${VENV_DIR}/bin:$PATH"
if podman-compose --version; then
    log_info "podman-compose installed successfully: $(podman-compose --version)"
else
    log_error "podman-compose installation verification failed"
    log_warn "This may be OK if podman is not yet fully configured"
fi

# Clean up
rm -f "${PODMAN_TARBALL}"

log_info "Podman bootstrap complete!"
log_info "Installed components:"
log_info "  - Podman ${PODMAN_VERSION}"
log_info "  - conmon ${CONMON_VERSION}"
log_info "  - netavark ${NETAVARK_VERSION}"
log_info "  - aardvark-dns ${AARDVARK_DNS_VERSION}"
log_info "  - podman-compose ${PODMAN_COMPOSE_VERSION} (installed via pyproject.toml)"
log_info ""
log_info "Docker alias symlinks created: docker -> podman, docker-compose -> podman-compose"
log_info ""
log_info "To use Podman:"
log_info "  1. Run: ami-run or ami-uv commands (Podman is auto-available)"
log_info "  2. Or activate venv: source ${VENV_DIR}/bin/activate"
log_info "  3. Run podman commands: podman ps, podman-compose up, etc."
log_info "  4. Or use docker commands: docker ps, docker-compose up (they map to podman)"
