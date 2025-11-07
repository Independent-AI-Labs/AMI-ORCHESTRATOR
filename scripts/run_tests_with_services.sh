#!/usr/bin/env bash
# Pre-push test runner that ensures required services are running

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Function to check if port is in use
check_port_in_use() {
    local port=$1
    lsof -i ":$port" >/dev/null 2>&1
}

# Function to start secrets-broker with proper environment
start_secrets_broker() {
    echo "Starting secrets-broker via launcher..."
    python3 nodes/scripts/launch_services.py start secrets-broker --module-paths base 2>&1 | grep -v "^$" || true
    # Wait for startup
    sleep 3
}

# Check if secrets-broker is needed and start it if not running
if [ -f "base/scripts/run_secrets_broker.py" ]; then
    if check_port_in_use 8700; then
        echo "secrets-broker already running on port 8700"
    else
        echo "secrets-broker not running, starting it..."
        start_secrets_broker

        # Verify it started
        if check_port_in_use 8700; then
            echo "secrets-broker started successfully"
        else
            echo "Warning: secrets-broker failed to start, tests may fail" >&2
        fi
    fi
fi

# Run the actual tests
if [ -f scripts/run_tests.py ]; then
    exec python3 scripts/run_tests.py
else
    exec ./.venv/bin/python -m pytest -q
fi
