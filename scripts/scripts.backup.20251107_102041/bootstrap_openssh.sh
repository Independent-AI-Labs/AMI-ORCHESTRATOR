#!/usr/bin/env bash
set -euo pipefail

# OpenSSH Bootstrap Script for AMI-ORCHESTRATOR
# Downloads OpenSSH portable static build for venv installation
# Runs on non-privileged port (2222) for git-only access

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
OPENSSH_DIR="${VENV_DIR}/openssh"
SSH_PORT="${SSH_PORT:-2222}"

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
    log_error "This script only supports Linux. For other platforms, use system OpenSSH."
    exit 1
fi

# Detect architecture
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64|amd64)
        OPENSSH_ARCH="amd64"
        ;;
    aarch64|arm64)
        OPENSSH_ARCH="arm64"
        ;;
    *)
        log_error "Unsupported architecture: ${ARCH}"
        exit 1
        ;;
esac

log_info "Bootstrapping OpenSSH for ${ARCH} on port ${SSH_PORT}"

# Create OpenSSH directory structure
mkdir -p "${OPENSSH_DIR}"/{bin,sbin,etc/ssh,var/empty,var/run}

# Download OpenSSH packages using apt
# This gets us pre-built binaries for the current system without needing to compile
log_info "Downloading OpenSSH packages..."

# Use apt download to get the correct packages for this system
cd "${OPENSSH_DIR}"
apt download openssh-server openssh-client 2>/dev/null || {
    log_error "Failed to download OpenSSH packages"
    log_error "Ensure apt is configured and you have network access"
    exit 1
}

# Rename downloaded files to predictable names
mv openssh-server_*.deb openssh-server.deb
mv openssh-client_*.deb openssh-client.deb

# Extract packages without installing system-wide
log_info "Extracting OpenSSH binaries..."
cd "${OPENSSH_DIR}"
ar x openssh-server.deb
tar -xf data.tar.* -C "${OPENSSH_DIR}" --strip-components=3 ./usr/sbin/sshd

ar x openssh-client.deb
tar -xf data.tar.* -C "${OPENSSH_DIR}" --strip-components=3 \
    ./usr/bin/ssh \
    ./usr/bin/ssh-keygen \
    ./usr/bin/scp \
    ./usr/bin/sftp 2>/dev/null || true

# Move binaries to correct locations
mv "${OPENSSH_DIR}/sshd" "${OPENSSH_DIR}/sbin/"
mkdir -p "${OPENSSH_DIR}/bin"
for bin in ssh ssh-keygen scp sftp; do
    if [[ -f "${OPENSSH_DIR}/${bin}" ]]; then
        mv "${OPENSSH_DIR}/${bin}" "${OPENSSH_DIR}/bin/"
    fi
done

log_info "✓ OpenSSH binaries extracted"

# Generate host keys
log_info "Generating SSH host keys..."
export PATH="${OPENSSH_DIR}/bin:$PATH"
ssh-keygen -A -f "${OPENSSH_DIR}"

# Create sshd_config
log_info "Creating sshd configuration..."
cat > "${OPENSSH_DIR}/etc/sshd_config" <<EOF
# AMI-ORCHESTRATOR OpenSSH Server Configuration
# Non-privileged SSH server for git-only access

# Network
Port ${SSH_PORT}
AddressFamily any
ListenAddress 0.0.0.0

# Host keys
HostKey ${OPENSSH_DIR}/etc/ssh/ssh_host_rsa_key
HostKey ${OPENSSH_DIR}/etc/ssh/ssh_host_ecdsa_key
HostKey ${OPENSSH_DIR}/etc/ssh/ssh_host_ed25519_key

# Authentication
PubkeyAuthentication yes
AuthorizedKeysFile ${OPENSSH_DIR}/etc/authorized_keys
PasswordAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM no

# Security
PermitRootLogin no
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
PrintMotd no
PrintLastLog no
Compression no

# Logging
SyslogFacility AUTH
LogLevel INFO

# Process management (no strict mode checks for non-root)
PidFile ${OPENSSH_DIR}/var/run/sshd.pid
StrictModes no

# Subsystem
Subsystem sftp internal-sftp
EOF

log_info "✓ Created ${OPENSSH_DIR}/etc/sshd_config"

# Create startup script
log_info "Creating startup script..."
cat > "${VENV_DIR}/bin/sshd-venv" <<'EOFSCRIPT'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$(dirname "${SCRIPT_DIR}")"
OPENSSH_DIR="${VENV_DIR}/openssh"
SSHD_BIN="${OPENSSH_DIR}/sbin/sshd"
SSHD_CONFIG="${OPENSSH_DIR}/etc/sshd_config"
PID_FILE="${OPENSSH_DIR}/var/run/sshd.pid"

if [[ ! -f "${SSHD_BIN}" ]]; then
    echo "Error: sshd not found at ${SSHD_BIN}" >&2
    echo "Run: scripts/bootstrap_openssh.sh" >&2
    exit 1
fi

case "${1:-}" in
    start)
        if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
            echo "sshd is already running (PID: $(cat "${PID_FILE}"))"
            exit 0
        fi
        echo "Starting sshd on port $(grep "^Port" "${SSHD_CONFIG}" | awk '{print $2}')..."
        "${SSHD_BIN}" -f "${SSHD_CONFIG}" -E "${OPENSSH_DIR}/var/run/sshd.log"
        echo "✓ sshd started"
        ;;
    stop)
        if [[ -f "${PID_FILE}" ]]; then
            echo "Stopping sshd (PID: $(cat "${PID_FILE}"))"
            kill "$(cat "${PID_FILE}")"
            rm -f "${PID_FILE}"
            echo "✓ sshd stopped"
        else
            echo "sshd is not running"
        fi
        ;;
    restart)
        "$0" stop
        sleep 1
        "$0" start
        ;;
    status)
        if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
            echo "sshd is running (PID: $(cat "${PID_FILE}"))"
            PORT=$(grep "^Port" "${SSHD_CONFIG}" | awk '{print $2}')
            echo "Listening on port: ${PORT}"
            exit 0
        else
            echo "sshd is not running"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
EOFSCRIPT

chmod +x "${VENV_DIR}/bin/sshd-venv"
log_info "✓ Created ${VENV_DIR}/bin/sshd-venv"

# Create symbolic links for consistency
ln -sf "${OPENSSH_DIR}/sbin/sshd" "${VENV_DIR}/bin/sshd"
ln -sf "${OPENSSH_DIR}/bin/ssh" "${VENV_DIR}/bin/ssh"
ln -sf "${OPENSSH_DIR}/bin/ssh-keygen" "${VENV_DIR}/bin/ssh-keygen"
ln -sf "${OPENSSH_DIR}/bin/scp" "${VENV_DIR}/bin/scp"

# Clean up
rm -f "${OPENSSH_DIR}"/*.deb
rm -f "${OPENSSH_DIR}"/{control.tar.*,data.tar.*,debian-binary}

# Get installed OpenSSH version
INSTALLED_VERSION=$("${OPENSSH_DIR}/sbin/sshd" -V 2>&1 | head -n1 | awk '{print $1}')

log_info "OpenSSH bootstrap complete!"
log_info "Installed components:"
log_info "  - ${INSTALLED_VERSION}"
log_info "  - SSH server port: ${SSH_PORT}"
log_info "  - Configuration: ${OPENSSH_DIR}/etc/sshd_config"
log_info "  - Authorized keys: ${OPENSSH_DIR}/etc/authorized_keys"
log_info ""
log_info "To use SSH server:"
log_info "  1. Start server: sshd-venv start"
log_info "  2. Check status: sshd-venv status"
log_info "  3. Stop server: sshd-venv stop"
log_info ""
log_info "Configure git repositories with ami-repo:"
log_info "  ami-repo --base-path ~/git-repos init"
log_info "  ami-repo generate-key mykey"
log_info "  ami-repo add-key ~/git-repos/ssh-keys/mykey_id_ed25519.pub mykey"
log_info "  ln -sf ~/git-repos/authorized_keys ${OPENSSH_DIR}/etc/authorized_keys"
log_info ""
log_info "Connect using: ssh -p ${SSH_PORT} user@host"
