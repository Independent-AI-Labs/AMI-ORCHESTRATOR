#!/bin/sh
# Admin Recovery SSH Server
# Part of AMI Orchestration Platform
#
# Provides emergency access when main shell is compromised
# Runs with dash POSIX shell for maximum portability
#
# Usage: ./recovery_ssh_server.sh {start|stop|restart|status}
# Environment variables:
#   RECOVERY_PORT - SSH port for recovery service (default: 2222)
#   RECOVERY_USER - SSH user for recovery service (default: admin)
#   RECOVERY_KEY_PATH - Path to authorized keys (default: /etc/admin-recovery/authorized_keys)

RECOVERY_PORT=${RECOVERY_PORT:-2222}
RECOVERY_USER=${RECOVERY_USER:-"admin"}
RECOVERY_KEY_PATH=${RECOVERY_KEY_PATH:-"/etc/admin-recovery/authorized_keys"}

# Configuration
LOG_FILE="/var/log/admin-recovery.log"
PID_FILE="/var/run/admin-recovery.pid"

# Logging function
log() {
    echo "$(date): $1" >> $LOG_FILE
}

# Check dependencies
check_dependencies() {
    if ! command -v dropbear >/dev/null 2>&1 && ! command -v sshd >/dev/null 2>&1; then
        log "ERROR: No SSH server found. Please install dropbear or openssh-server"
        exit 1
    fi
}

# Create minimal recovery environment
setup_recovery_env() {
    mkdir -p /etc/admin-recovery
    mkdir -p /var/lib/admin-recovery
    
    # Copy original bash if available for recovery
    if [ -f /bin/bash.original ]; then
        cp /bin/bash.original /var/lib/admin-recovery/bash.backup
    fi
    
    # Create recovery shell that's independent of bash
    cat > /var/lib/admin-recovery/recovery_shell.sh << 'EOF'
#!/bin/sh
# Independent recovery shell
echo "Admin Recovery Shell - Dash-based"
echo "Available commands: restore_bash, check_status, list_backups, shell"
echo ""

restore_bash() {
    if [ -f /bin/bash.original ]; then
        cp /bin/bash.original /bin/bash
        chmod +x /bin/bash
        echo "Original bash restored successfully"
    else
        echo "No backup bash available at /bin/bash.original"
    fi
}

check_status() {
    echo "System Status:"
    if [ -f /bin/bash.original ]; then
        echo "  Backup bash: Available"
    else
        echo "  Backup bash: Missing"
    fi
    
    # Try to check if current bash is working
    if [ -x /bin/bash ]; then
        if /bin/bash -c "echo 'test' > /dev/null 2>&1"; then
            echo "  Current bash: Working"
        else
            echo "  Current bash: May be broken"
        fi
    else
        echo "  Current bash: Not executable"
    fi
    
    echo "  System date: $(date)"
    echo "  Uptime: $(uptime)"
}

list_backups() {
    if [ -d /var/lib/admin-recovery ]; then
        echo "Backups in /var/lib/admin-recovery/:"
        ls -la /var/lib/admin-recovery/ 2>/dev/null
    else
        echo "No recovery directory found"
    fi
}

shell() {
    echo "Starting system shell (using /bin/sh - dash)..."
    exec /bin/sh
}

# Interactive mode
echo "Admin Recovery Shell"
echo "Commands: restore_bash, check_status, list_backups, shell, exit, help"
while true; do
    printf "recovery> "
    if read -r cmd; then
        case $cmd in
            restore_bash)
                restore_bash
                ;;
            check_status)
                check_status
                ;;
            list_backups)
                list_backups
                ;;
            shell)
                shell
                ;;
            help)
                echo "Available commands:"
                echo "  restore_bash - Restore original bash from backup"
                echo "  check_status - Check system and bash status"
                echo "  list_backups - List available backups"
                echo "  shell - Get a system shell (dash)"
                echo "  exit/quit - Exit recovery shell"
                echo "  help - Show this help"
                ;;
            exit|quit|"")
                echo "Exiting recovery shell"
                exit 0
                ;;
            *)
                echo "Unknown command: $cmd"
                echo "Type 'help' for available commands"
                ;;
        esac
    else
        # Handle EOF (Ctrl+D)
        echo
        exit 0
    fi
done
EOF

    chmod +x /var/lib/admin-recovery/recovery_shell.sh
}

# Start the recovery service
start_service() {
    log "Starting admin recovery service on port $RECOVERY_PORT"
    
    # Check if service is already running
    if [ -f $PID_FILE ] && kill -0 $(cat $PID_FILE) 2>/dev/null; then
        log "Admin recovery service already running"
        return 1
    fi
    
    # Use dropbear if available, otherwise try openssh
    if command -v dropbear >/dev/null 2>&1; then
        log "Using dropbear as SSH server"
        
        # Generate host keys if they don't exist
        if [ ! -f /etc/admin-recovery/dropbear_ecdsa_host_key ]; then
            log "Generating dropbear host keys"
            dropbearkey -t ecdsa -f /etc/admin-recovery/dropbear_ecdsa_host_key
        fi
        
        # Start dropbear with custom options
        # Use a custom login shell that points to our recovery shell
        dropbear -p $RECOVERY_PORT -r /etc/admin-recovery/dropbear_ecdsa_host_key -F -E -s -g -c "/var/lib/admin-recovery/recovery_shell.sh" &
        echo $! > $PID_FILE
        log "Admin recovery service started with PID $(cat $PID_FILE)"
        
    else
        log "SSH server not available - please install dropbear or openssh-server"
        return 1
    fi
}

# Stop the recovery service
stop_service() {
    if [ -f $PID_FILE ]; then
        PID=$(cat $PID_FILE)
        if kill -0 $PID 2>/dev/null; then
            log "Stopping admin recovery service with PID $PID"
            kill $PID
            rm -f $PID_FILE
            return 0
        else
            log "PID file exists but process not running, cleaning up"
            rm -f $PID_FILE
        fi
    else
        log "No PID file found, service may not be running"
    fi
}

# Main execution
case "$1" in
    start)
        check_dependencies
        setup_recovery_env
        start_service
        ;;
    stop)
        stop_service
        log "Admin recovery service stopped"
        ;;
    restart)
        stop_service
        sleep 1
        check_dependencies
        setup_recovery_env
        start_service
        ;;
    status)
        if [ -f $PID_FILE ] && kill -0 $(cat $PID_FILE) 2>/dev/null; then
            echo "Admin recovery service is running (PID: $(cat $PID_FILE))"
            log "Status: Service running"
        else
            echo "Admin recovery service is not running"
            log "Status: Service not running"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac