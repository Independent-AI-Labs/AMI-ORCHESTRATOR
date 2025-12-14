#!/bin/bash

# Matrix Synapse Bootstrap Script
# Automated process for initializing Matrix services with PostgreSQL

set -e  # Exit on any error

# Function to find orchestrator root
find_orchestrator_root() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local current="$script_dir"

    # Go up maximum 4 levels to find orchestrator root
    for _ in {1..4}; do
        if [[ -d "$current/base" && -d "$current/.git" ]]; then
            echo "$current"
            return 0
        fi
        if [[ "$current" == "/" ]]; then
            return 1
        fi
        current="$(dirname "$current")"
    done

    return 1
}

# Discover orchestrator root and set up podman path
ORCHESTRATOR_ROOT="$(find_orchestrator_root)"
if [[ -z "$ORCHESTRATOR_ROOT" ]]; then
    echo "ERROR: Could not find orchestrator root"
    exit 1
fi

# Set up bootstrapped podman path
BOOTSTRAPPED_PODMAN="$ORCHESTRATOR_ROOT/.boot-linux/bin/podman"

# Verify bootstrapped podman exists
if [[ ! -x "$BOOTSTRAPPED_PODMAN" ]]; then
    echo "ERROR: Bootstrapped podman not found at $BOOTSTRAPPED_PODMAN"
    echo "Please run bootstrap process first to install podman in .boot-linux"
    exit 1
fi

# Configuration variables
MATRIX_PROJECT_NAME="ami-orchestrator"
MATRIX_SERVER_NAME="matrix.openami.local"
MATRIX_UID=${MATRIX_UID:-991}
MATRIX_GID=${MATRIX_GID:-991}

# Default PostgreSQL settings
MATRIX_POSTGRES_DB=${MATRIX_POSTGRES_DB:-synapse}
MATRIX_POSTGRES_USER=${MATRIX_POSTGRES_USER:-synapse}
MATRIX_POSTGRES_PASSWORD=${MATRIX_POSTGRES_PASSWORD:-synapse_secure_password_CHANGE_ME_IN_PRODUCTION}
MATRIX_POSTGRES_PORT=${MATRIX_POSTGRES_PORT:-5432}  # Default to 5432 for internal container communication

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to determine the correct volume name
get_matrix_volume_name() {
    local project_name=$1
    local base_name="matrix_synapse_data"

    # Check if project-specific volume exists
    if $BOOTSTRAPPED_PODMAN volume ls --format "{{.Name}}" | grep -q "^${project_name}_${base_name}$"; then
        echo "${project_name}_${base_name}"
    else
        # Fallback to base name if project-specific doesn't exist
        echo "${base_name}"
    fi
}

# Function to check if a service is running
is_service_running() {
    local service_name=$1
    if ./scripts/ami-run python launcher/scripts/launch_services.py status 2>/dev/null | grep -q "${service_name}: running"; then
        return 0
    else
        return 1
    fi
}

# Function to initialize Matrix Synapse configuration
initialize_synapse_config() {
    log_info "Initializing Matrix Synapse configuration..."

    # Get the correct volume name for the project
    MATRIX_VOLUME=$(get_matrix_volume_name "${MATRIX_PROJECT_NAME}")
    log_info "Using volume: ${MATRIX_VOLUME}"

    # Check if configuration already exists in the correct volume
    if $BOOTSTRAPPED_PODMAN run --rm -v "${MATRIX_VOLUME}:/data" alpine test -f /data/homeserver.yaml 2>/dev/null; then
        log_info "Configuration already exists in volume ${MATRIX_VOLUME}, verifying content..."

        # Verify that the homeserver.yaml contains PostgreSQL configuration
        if $BOOTSTRAPPED_PODMAN run --rm -v "${MATRIX_VOLUME}:/data" alpine grep -q "name: psycopg2" /data/homeserver.yaml 2>/dev/null; then
            log_info "Configuration already contains PostgreSQL settings"
            return 0
        else
            log_warn "Configuration exists but doesn't contain PostgreSQL settings, updating..."
        fi
    else
        # Generate configuration in the correct volume (defaults to SQLite)
        log_info "Generating initial Synapse configuration in ${MATRIX_VOLUME} volume..."

        # Check if the required network exists, create it if it doesn't
        if ! $BOOTSTRAPPED_PODMAN network exists ami-isms-network >/dev/null 2>&1; then
            log_info "Creating required network: ami-isms-network"
            $BOOTSTRAPPED_PODMAN network create ami-isms-network
        fi

        $BOOTSTRAPPED_PODMAN run --rm --network ami-isms-network -v "${MATRIX_VOLUME}:/data" \
            -e SYNAPSE_SERVER_NAME="${MATRIX_SERVER_NAME}" \
            -e SYNAPSE_REPORT_STATS=no \
            -e UID="${MATRIX_UID}" \
            -e GID="${MATRIX_GID}" \
            matrixdotorg/synapse:v1.95.0 generate

        log_info "Initial configuration generated, now updating to use PostgreSQL..."
    fi

    # Set proper ownership for all files in the volume
    log_info "Setting proper file ownership in volume..."
    $BOOTSTRAPPED_PODMAN run --rm -v "${MATRIX_VOLUME}:/data" --user root alpine \
        chown -R "${MATRIX_UID}:${MATRIX_GID}" /data/

    # Update the configuration to use PostgreSQL instead of SQLite
    update_synapse_to_postgres "${MATRIX_VOLUME}"

    log_info "Synapse configuration initialized successfully with PostgreSQL"
}

# Function to update Synapse configuration from SQLite to PostgreSQL
update_synapse_to_postgres() {
    local volume_name=$1
    log_info "Updating Synapse configuration to use PostgreSQL..."

    # Create a completely new homeserver.yaml with PostgreSQL configuration
    # First, let's just completely replace the database section with sed
    $BOOTSTRAPPED_PODMAN run --rm -v "${volume_name}:/data" --user root \
        -e MATRIX_POSTGRES_USER="${MATRIX_POSTGRES_USER}" \
        -e MATRIX_POSTGRES_PASSWORD="${MATRIX_POSTGRES_PASSWORD}" \
        -e MATRIX_POSTGRES_DB="${MATRIX_POSTGRES_DB}" \
        -e MATRIX_POSTGRES_PORT="${MATRIX_POSTGRES_PORT}" \
        alpine sh -c '
            # Backup the original file
            cp /data/homeserver.yaml /data/homeserver.yaml.backup

            # Use sed to completely replace the database section
            # First, find the database lines and replace them
            awk "
                BEGIN { in_db_block = 0 }
                /^database:/ {
                    in_db_block = 1
                    print \"database:\"
                    print \"  name: psycopg2\"
                    print \"  args:\"
                    print \"    user: ${MATRIX_POSTGRES_USER}\"
                    print \"    password: ${MATRIX_POSTGRES_PASSWORD}\"
                    print \"    database: ${MATRIX_POSTGRES_DB}\"
                    print \"    host: matrix-postgres\"
                    print \"    port: ${MATRIX_POSTGRES_PORT}\"
                    print \"    cp_min: 5\"
                    print \"    cp_max: 10\"
                    next
                }
                /^[^ ]/ && in_db_block == 1 { in_db_block = 0 }  # End of db block
                in_db_block == 1 { next }  # Skip old db config lines
                { print }
            " /data/homeserver.yaml > /tmp/homeserver_new.yaml && mv /tmp/homeserver_new.yaml /data/homeserver.yaml
        '

    log_info "Synapse configuration updated to use PostgreSQL"
}

# Function to verify docker-compose configuration
verify_docker_compose_config() {
    log_info "Verifying docker-compose configuration..."
    
    # Check if the environment variables are properly set in the compose file
    if grep -q "POSTGRES_HOST:" docker-compose.services.yml && \
       grep -q "POSTGRES_DB:" docker-compose.services.yml && \
       grep -q "POSTGRES_USER:" docker-compose.services.yml && \
       grep -q "POSTGRES_PASSWORD:" docker-compose.services.yml; then
        log_warn "docker-compose.services.yml contains conflicting PostgreSQL environment variables"
        log_info "These may interfere with custom homeserver.yaml configuration"
        return 1
    else
        log_info "docker-compose.services.yml configuration verified"
        return 0
    fi
}

# Function to update docker-compose if needed
update_docker_compose_config() {
    log_info "Updating docker-compose.services.yml to remove conflicting environment variables..."
    
    # Create backup
    cp docker-compose.services.yml docker-compose.services.yml.backup.$(date +%s)
    
    # Use sed to remove conflicting environment variables while preserving other variables
    sed -i.bak '/POSTGRES_HOST:/d;/POSTGRES_PORT:/d;/POSTGRES_DB:/d;/POSTGRES_USER:/d;/POSTGRES_PASSWORD:/d' docker-compose.services.yml
    
    # Also ensure SYNAPSE_CONFIG_PATH is set
    if ! grep -A 20 "matrix-synapse:" docker-compose.services.yml | grep -q "SYNAPSE_CONFIG_PATH:"; then
        sed -i.bak '/matrix-synapse:/,/image:/{
            /image:/a\    environment:\n      SYNAPSE_CONFIG_PATH: /data/homeserver.yaml\n      UID: ${MATRIX_UID:-991}\n      GID: ${MATRIX_GID:-991}
        }' docker-compose.services.yml
    fi
    
    log_info "docker-compose.services.yml updated successfully"
}

# Function to start Matrix services in correct order
start_matrix_services() {
    log_info "Starting Matrix services in correct order..."
    
    # Start PostgreSQL first
    if ! is_service_running "matrix-postgres"; then
        log_info "Starting matrix-postgres..."
        ./scripts/ami-run python launcher/scripts/launch_services.py start matrix-postgres
    else
        log_info "matrix-postgres is already running"
    fi
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    sleep 10
    
    # Start Synapse
    if ! is_service_running "matrix-synapse"; then
        log_info "Starting matrix-synapse..."
        ./scripts/ami-run python launcher/scripts/launch_services.py start matrix-synapse
    else
        log_info "matrix-synapse is already running"
    fi
    
    # Wait for Synapse to start
    log_info "Waiting for Synapse to start..."
    sleep 15
    
    # Start Element
    if ! is_service_running "matrix-element"; then
        log_info "Starting matrix-element..."
        ./scripts/ami-run python launcher/scripts/launch_services.py start matrix-element
    else
        log_info "matrix-element is already running"
    fi
    
    log_info "Matrix services started successfully"
}

# Function to verify Matrix services are running
verify_services_running() {
    log_info "Verifying Matrix services status..."
    
    local status=$(./scripts/ami-run python launcher/scripts/launch_services.py status 2>/dev/null)
    
    local errors=0
    for service in matrix-postgres matrix-synapse matrix-element; do
        if echo "$status" | grep -q "${service}: running"; then
            log_info "${service}: running ✓"
        else
            log_error "${service}: not running ✗"
            ((errors++))
        fi
    done
    
    if [ $errors -eq 0 ]; then
        log_info "All Matrix services are running successfully"
        return 0
    else
        log_error "Some Matrix services failed to start"
        echo "$status"
        return 1
    fi
}

# Function to test PostgreSQL connection
test_postgres_connection() {
    log_info "Testing PostgreSQL connection from Synapse..."
    
    # Try to run a simple command to check if Synapse can access PostgreSQL
    local MATRIX_VOLUME=$(get_matrix_volume_name "${MATRIX_PROJECT_NAME}")
    
    # Check if Synapse can read the config and potentially connect to DB
    local connection_test=$($BOOTSTRAPPED_PODMAN run --rm --network ami-isms-network \
        -v "${MATRIX_VOLUME}:/data" \
        --user "${MATRIX_UID}:${MATRIX_GID}" \
        --entrypoint python3 matrixdotorg/synapse:v1.95.0 \
        -c "
import yaml
try:
    with open('/data/homeserver.yaml', 'r') as f:
        config = yaml.safe_load(f)
    db_config = config.get('database', {})
    if db_config.get('name') == 'psycopg2':
        print('PostgreSQL configuration found')
        args = db_config.get('args', {})
        print(f'Host: {args.get(\"host\", \"unknown\")}')
        print(f'Database: {args.get(\"database\", \"unknown\")}')
        print('Configuration: VALID')
    else:
        print('ERROR: Not using PostgreSQL')
except Exception as e:
    print(f'ERROR: Config read failed: {e}')
" 2>/dev/null || echo "ERROR: Could not test configuration")
    
    echo "$connection_test"
    
    if echo "$connection_test" | grep -q "Configuration: VALID"; then
        log_info "PostgreSQL configuration validated successfully"
        return 0
    else
        log_error "PostgreSQL configuration validation failed"
        return 1
    fi
}

# Main bootstrap function
bootstrap_matrix() {
    log_info "Starting Matrix Synapse bootstrap process..."
    
    # Check prerequisites - we now have the bootstrapped podman
    if [[ ! -x "$BOOTSTRAPPED_PODMAN" ]]; then
        log_error "Bootstrapped podman not found at $BOOTSTRAPPED_PODMAN"
        exit 1
    fi

    # Check if podman-compose is available (try both bootstrapped and system locations)
    if ! $BOOTSTRAPPED_PODMAN compose version >/dev/null 2>&1 && ! command -v podman-compose >/dev/null 2>&1; then
        log_error "podman-compose is not available (needed for docker-compose.services.yml)"
        exit 1
    fi
    
    # Check if docker-compose.services.yml exists
    if [ ! -f "docker-compose.services.yml" ]; then
        log_error "docker-compose.services.yml not found"
        exit 1
    fi
    
    # Initialize configuration
    initialize_synapse_config
    
    # Verify and update docker-compose config if needed
    if ! verify_docker_compose_config; then
        read -p "Update docker-compose.services.yml to fix configuration? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            update_docker_compose_config
        else
            log_warn "Proceeding without configuration update (may cause startup issues)"
        fi
    fi
    
    # Start services
    start_matrix_services
    
    # Verify services are running
    if verify_services_running; then
        log_info "Matrix services started successfully"
        
        # Test PostgreSQL connection
        if test_postgres_connection; then
            log_info "Matrix Synapse bootstrap completed successfully!"
            echo
            log_info "Services are now running:"
            log_info "- Matrix Synapse: http://localhost:8008"
            log_info "- Matrix Element: http://localhost:8889"
            log_info "- PostgreSQL: localhost:5433 (mapped from 5432)"
            return 0
        else
            log_error "PostgreSQL connection test failed"
            return 1
        fi
    else
        log_error "Matrix services failed to start properly"
        return 1
    fi
}

# Function to reset Matrix services (for troubleshooting)
reset_matrix() {
    log_info "Resetting Matrix services..."
    
    # Stop all Matrix services
    ./scripts/ami-run python launcher/scripts/launch_services.py stop matrix-element matrix-synapse matrix-postgres 2>/dev/null || true
    
    # Remove Matrix containers
    $BOOTSTRAPPED_PODMAN stop ami-matrix-synapse ami-matrix-postgres ami-matrix-element 2>/dev/null || true
    $BOOTSTRAPPED_PODMAN rm ami-matrix-synapse ami-matrix-postgres ami-matrix-element 2>/dev/null || true

    # Get the correct volume name and reset it
    MATRIX_VOLUME=$(get_matrix_volume_name "${MATRIX_PROJECT_NAME}")
    log_info "Resetting volume: ${MATRIX_VOLUME}"
    $BOOTSTRAPPED_PODMAN volume rm "${MATRIX_VOLUME}" 2>/dev/null || true

    # Create new volume
    $BOOTSTRAPPED_PODMAN volume create "${MATRIX_VOLUME}"
    
    log_info "Matrix services reset completed"
}

# Function to show help
show_help() {
    cat << EOF
Matrix Synapse Bootstrap Script

Usage: $0 [command]

Commands:
  bootstrap    - Initialize and start Matrix services (default)
  reset        - Reset Matrix services and configuration
  verify       - Verify Matrix services status
  help         - Show this help message

Environment Variables:
  MATRIX_UID          - Synapse user ID (default: 991)
  MATRIX_GID          - Synapse group ID (default: 991)
  MATRIX_POSTGRES_DB  - PostgreSQL database name (default: synapse)
  MATRIX_POSTGRES_USER - PostgreSQL user (default: synapse)
  MATRIX_POSTGRES_PASSWORD - PostgreSQL password
  MATRIX_POSTGRES_PORT - PostgreSQL port (default: 5432)

Examples:
  $0 bootstrap          # Bootstrap Matrix services
  $0 reset             # Reset Matrix services
  $0 verify            # Verify service status
EOF
}

# Main execution
main() {
    local command="${1:-bootstrap}"
    
    case "$command" in
        "bootstrap")
            bootstrap_matrix
            ;;
        "reset")
            reset_matrix
            ;;
        "verify")
            verify_services_running
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Only run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi