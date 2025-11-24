#!/bin/bash
# Installation script for AMI Admin Recovery Service
# Sets up the recovery SSH service for emergency access

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECOVERY_SCRIPT="$PROJECT_ROOT/scripts/admin/recovery_ssh_server.sh"
SYSTEMD_SERVICE_SRC="$PROJECT_ROOT/base/config/system/admin-recovery-ssh.service"
SYSTEMD_SERVICE_DEST="/etc/systemd/system/admin-recovery-ssh.service"
RECOVERY_PORT=${RECOVERY_PORT:-2222}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root"
        exit 1
    fi
}

# Function to check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    if ! command -v dropbear >/dev/null 2>&1; then
        warn "Dropbear SSH server not found. Installing..."
        if command -v apt-get >/dev/null 2>&1; then
            apt-get update && apt-get install -y dropbear
        elif command -v yum >/dev/null 2>&1; then
            yum install -y dropbear
        else
            error "No supported package manager found. Please install dropbear manually."
            exit 1
        fi
    fi
    
    log "Dependencies satisfied"
}

# Function to setup recovery keys
setup_recovery_keys() {
    log "Setting up recovery SSH keys..."
    
    # Create recovery directory
    mkdir -p /etc/admin-recovery
    
    # Generate host key if it doesn't exist
    if [ ! -f /etc/admin-recovery/dropbear_ecdsa_host_key ]; then
        log "Generating dropbear host key..."
        dropbearkey -t ecdsa -f /etc/admin-recovery/dropbear_ecdsa_host_key
    fi
    
    # Check if authorized_keys exists, if not, warn user
    if [ ! -f /etc/admin-recovery/authorized_keys ]; then
        warn "No authorized_keys file found at /etc/admin-recovery/authorized_keys"
        warn "Please add your public SSH keys to this file to enable access"
        warn "Example: echo 'your-public-key-here' > /etc/admin-recovery/authorized_keys"
    fi
}

# Function to install systemd service
install_systemd_service() {
    log "Installing systemd service..."
    
    if [ -f "$SYSTEMD_SERVICE_SRC" ]; then
        cp "$SYSTEMD_SERVICE_SRC" "$SYSTEMD_SERVICE_DEST"
        systemctl daemon-reload
        log "Systemd service installed"
    else
        error "Systemd service file not found: $SYSTEMD_SERVICE_SRC"
        exit 1
    fi
}

# Function to enable and start the service
enable_service() {
    log "Enabling admin recovery service..."
    
    systemctl enable admin-recovery-ssh.service
    
    if systemctl start admin-recovery-ssh.service; then
        log "Admin recovery service started successfully"
        log "Service listening on port $RECOVERY_PORT"
    else
        error "Failed to start admin recovery service"
        error "Check the service status with: systemctl status admin-recovery-ssh.service"
        exit 1
    fi
}

# Function to verify installation
verify_installation() {
    log "Verifying installation..."
    
    if systemctl is-active --quiet admin-recovery-ssh.service; then
        log "✓ Service is running"
    else
        error "✗ Service is not running"
        systemctl status admin-recovery-ssh.service
        exit 1
    fi
    
    # Check if port is open
    if netstat -tuln | grep -q ":$RECOVERY_PORT "; then
        log "✓ Port $RECOVERY_PORT is listening"
    else
        warn "Port $RECOVERY_PORT may not be listening, check service logs"
    fi
    
    log "Installation verification complete"
}

# Function to display instructions
show_instructions() {
    log "Installation complete! Here's how to use the admin recovery service:"
    echo ""
    echo -e "${BLUE}Service Management:${NC}"
    echo "  Start:      sudo systemctl start admin-recovery-ssh.service"
    echo "  Stop:       sudo systemctl stop admin-recovery-ssh.service"  
    echo "  Restart:    sudo systemctl restart admin-recovery-ssh.service"
    echo "  Status:     sudo systemctl status admin-recovery-ssh.service"
    echo "  Logs:       sudo journalctl -u admin-recovery-ssh.service -f"
    echo ""
    echo -e "${BLUE}Access:${NC}"
    echo "  SSH access: ssh -p $RECOVERY_PORT username@your-server-ip"
    echo "  The recovery shell provides commands: restore_bash, check_status, list_backups, shell"
    echo ""
    echo -e "${BLUE}Configuration:${NC}"
    echo "  Service file: $SYSTEMD_SERVICE_DEST"
    echo "  Recovery scripts: $PROJECT_ROOT/scripts/admin/"
    echo "  Configuration: /etc/admin-recovery/"
    echo ""
}

# Main installation process
main() {
    log "Starting AMI Admin Recovery Service installation"
    log "Project root: $PROJECT_ROOT"
    log "Recovery port: $RECOVERY_PORT"
    
    check_root
    check_dependencies
    setup_recovery_keys
    install_systemd_service
    enable_service
    verify_installation
    show_instructions
    
    log "AMI Admin Recovery Service installation completed successfully!"
}

# Run main function
main "$@"