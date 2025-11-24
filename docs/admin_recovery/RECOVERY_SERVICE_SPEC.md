# Admin Recovery Service Specification

## Overview
A failsafe SSH recovery service that runs as a system daemon to provide emergency access to the system, especially when the main shell (bash) is compromised by the wrapper implementation.

## Architecture

### Core Components

1. **Minimal SSH Server (using dash)**
   - Lightweight SSH daemon using minimal dependencies
   - Runs with dash shell instead of bash to remain unaffected by bash wrapper
   - Provides basic command execution and file transfer capabilities

2. **System Service (init.d/systemd)**
   - Auto-starts on boot
   - Monitors system health
   - Provides recovery shell access

3. **Recovery Shell Script**
   - Standalone script that can be run from any shell
   - Can restore original bash if wrapper breaks

## Implementation Plan

### 1. Recovery SSH Service

`/etc/systemd/system/admin-recovery-ssh.service`:
```ini
[Unit]
Description=Admin Recovery SSH Service
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/recovery_ssh_server.sh
Restart=always
RestartSec=5
User=root
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

[Install]
WantedBy=multi-user.target
```

### 2. Recovery SSH Server Script (recovery_ssh_server.sh)

```bash
#!/bin/sh
# Recovery SSH server using dropbear or basic openssh
# Runs with dash POSIX shell for maximum compatibility

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
echo "Available commands: restore_bash, check_status, list_backups"
echo ""

restore_bash() {
    if [ -f /bin/bash.original ]; then
        cp /bin/bash.original /bin/bash
        chmod +x /bin/bash
        echo "Original bash restored"
    else
        echo "No backup bash available"
    fi
}

check_status() {
    echo "System Status:"
    if [ -f /bin/bash.original ]; then
        echo "  Backup bash: Available"
    else
        echo "  Backup bash: Missing"
    fi
    
    if command -v /bin/bash >/dev/null 2>&1; then
        echo "  Current bash: Working"
        /bin/bash -c "echo 'Current bash test: OK'"
    else
        echo "  Current bash: Broken"
    fi
}

list_backups() {
    ls -la /var/lib/admin-recovery/ 2>/dev/null || echo "No backups found"
}

# Export functions so they're available
export -f restore_bash check_status list_backups

# Interactive mode
while true; do
    printf "recovery> "
    read -r cmd
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
        exit|quit)
            exit 0
            ;;
        *)
            echo "Unknown command: $cmd"
            echo "Available: restore_bash, check_status, list_backups, exit"
            ;;
    esac
done
EOF

    chmod +x /var/lib/admin-recovery/recovery_shell.sh
}

# Start the recovery service
start_service() {
    log "Starting admin recovery service on port $RECOVERY_PORT"
    
    # Use dropbear if available, otherwise try basic openssh setup
    if command -v dropbear >/dev/null 2>&1; then
        # Generate host keys if they don't exist
        if [ ! -f /etc/admin-recovery/dropbear_ecdsa_host_key ]; then
            mkdir -p /etc/admin-recovery
            dropbearkey -t ecdsa -f /etc/admin-recovery/dropbear_ecdsa_host_key
        fi
        
        # Start dropbear with custom shell
        dropbear -p $RECOVERY_PORT -r /etc/admin-recovery/dropbear_ecdsa_host_key -F -E
    else
        # For openssh, configure to use our recovery shell
        log "Starting with openssh configuration"
        # This would require more complex setup
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
        pkill -f "recovery_ssh_server"
        log "Admin recovery service stopped"
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac
```

### 3. Init.d Service Script

`/etc/init.d/admin-recovery`:
```bash
#!/bin/sh
### BEGIN INIT INFO
# Provides:          admin-recovery
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Admin Recovery Service
# Description:       Provides emergency access when main shell is broken
### END INIT INFO

PATH=/sbin:/usr/sbin:/bin:/usr/bin
DESC="Admin Recovery Service"
NAME=admin-recovery
DAEMON=/usr/local/bin/recovery_ssh_server.sh
PIDFILE=/var/run/$NAME.pid
SCRIPTNAME=/etc/init.d/$NAME

# Exit if the package is not installed
[ -x "$DAEMON" ] || exit 0

# Load the VERBOSE setting and other rcS variables
. /lib/init/vars.sh

# Define LSB log_* functions.
# Based on lsb-base-logging.sh, but copied here to make it independent of
# the presence of that file.
# Source: https://bugs.debian.org/700327
do_start() {
    # Return
    #   0 if daemon has been started
    #   1 if daemon was already running
    #   2 if daemon could not be started
    start-stop-daemon --start --quiet --pidfile $PIDFILE --exec $DAEMON --test > /dev/null || return 1
    start-stop-daemon --start --quiet --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_ARGS || return 2
}

do_stop() {
    # Return
    #   0 if daemon has been stopped
    #   1 if daemon was already stopped
    #   2 if daemon could not be stopped
    #   other if a failure occurred
    start-stop-daemon --stop --quiet --retry=TERM/30/KILL/5 --pidfile $PIDFILE --name $NAME
    RETVAL="$?"
    [ "$RETVAL" = 2 ] && return 2

    # Many daemons don't delete their pidfiles when they exit.
    rm -f $PIDFILE
    return "$RETVAL"
}

case "$1" in
    start)
        [ "$VERBOSE" != no ] && log_daemon_msg "Starting $DESC" "$NAME"
        do_start
        case "$?" in
            0|1) [ "$VERBOSE" != no ] && log_end_msg 0 ;;
            2) [ "$VERBOSE" != no ] && log_end_msg 1 ;;
        esac
        ;;
    stop)
        [ "$VERBOSE" != no ] && log_daemon_msg "Stopping $DESC" "$NAME"
        do_stop
        case "$?" in
            0|1) [ "$VERBOSE" != no ] && log_end_msg 0 ;;
            2) [ "$VERBOSE" != no ] && log_end_msg 1 ;;
        esac
        ;;
    restart|force-reload)
        log_daemon_msg "Restarting $DESC" "$NAME"
        do_stop
        case "$?" in
            0|1)
                do_start
                case "$?" in
                    0) log_end_msg 0 ;;
                    1) log_end_msg 1 ;; # Old process is still running
                    *) log_end_msg 1 ;; # Failed to start
                esac
                ;;
            *)
                # Failed to stop
                log_end_msg 1
                ;;
        esac
        ;;
    *)
        echo "Usage: $SCRIPTNAME {start|stop|restart|force-reload}" >&2
        exit 3
        ;;
esac

:
```

### 4. Configuration Management

The service should:
- Auto-start on boot
- Use dash shell for independence from bash
- Provide recovery commands for restoring original bash
- Have minimal dependencies to ensure availability
- Support SSH key authentication for secure access

### 5. Security Considerations

- Use dedicated SSH key pair for recovery access
- Run on non-standard port (e.g., 2222) to avoid conflicts
- Implement rate limiting and connection limits
- Log all recovery access attempts
- Encrypt recovery communication

## Deployment Steps

1. Install the recovery scripts and service configuration
2. Generate SSH keys for recovery access
3. Configure the service to start at boot
4. Test the recovery functionality before enabling bash wrapper