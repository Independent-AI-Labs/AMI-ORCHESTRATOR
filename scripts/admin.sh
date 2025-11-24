#!/bin/bash
# Admin Management Script for AMI Orchestration Platform
# Provides easy access to admin and recovery functions

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADMIN_SCRIPTS_DIR="$PROJECT_ROOT/scripts/admin"

# Logging function
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "AMI Admin Management Script"
    echo "Usage: $0 [command]"
    echo ""
    echo "Available commands:"
    echo "  install-recovery     Install the admin recovery SSH service"
    echo "  start-recovery       Start the admin recovery service"
    echo "  stop-recovery        Stop the admin recovery service" 
    echo "  restart-recovery     Restart the admin recovery service"
    echo "  status-recovery      Check status of admin recovery service"
    echo "  logs-recovery        View recovery service logs"
    echo "  help                 Show this help"
    echo ""
}

# Main command routing
case "$1" in
    install-recovery)
        if [ "$EUID" -ne 0 ]; then
            error "Installation requires root privileges"
            exit 1
        fi
        log "Installing admin recovery service..."
        exec "$ADMIN_SCRIPTS_DIR/install_admin_recovery.sh"
        ;;
    start-recovery)
        log "Starting admin recovery service..."
        sudo systemctl start admin-recovery-ssh.service
        log "Admin recovery service started"
        ;;
    stop-recovery)
        log "Stopping admin recovery service..."
        sudo systemctl stop admin-recovery-ssh.service
        log "Admin recovery service stopped"
        ;;
    restart-recovery)
        log "Restarting admin recovery service..."
        sudo systemctl restart admin-recovery-ssh.service
        log "Admin recovery service restarted"
        ;;
    status-recovery)
        log "Checking admin recovery service status..."
        sudo systemctl status admin-recovery-ssh.service
        ;;
    logs-recovery)
        log "Showing admin recovery service logs..."
        sudo journalctl -u admin-recovery-ssh.service -f
        ;;
    help|"")
        show_usage
        ;;
    *)
        error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac