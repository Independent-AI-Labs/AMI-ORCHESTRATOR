#!/usr/bin/env bash

# Testing functions for AMI Orchestrator

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_SCRIPT="$SCRIPT_DIR/common.sh"
if [ -f "$COMMON_SCRIPT" ]; then
    source "$COMMON_SCRIPT"
else
    echo "ERROR: common.sh not found at $COMMON_SCRIPT"
    exit 1
fi

# Ensure dependencies are synced before running tests (using bootstrapped binary)
sync_before_tests() {
    log_info "Syncing dependencies before running tests..."

    if [ -f "pyproject.toml" ]; then
        if [ -n "${UV_CMD:-}" ] && [ -x "$UV_CMD" ]; then
            # Run uv sync to ensure environment is up-to-date before tests
            output=$("$UV_CMD" sync --dev 2>&1)
            local exit_code=$?
            echo "$output"
            # Check for actual errors
            if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
                log_error "uv sync before tests failed with code $exit_code:"
                echo "$output" >&2
                return 1
            elif [[ "$output" == *"ERROR"* ]] || [[ "$output" == *"error"* ]]; then
                log_error "uv sync before tests reported errors:"
                echo "$output" >&2
                return 1
            fi
            log_info "Dependencies synced successfully before running tests"
        else
            log_warning "uv not available, skipping dependency sync before tests"
        fi
    else
        log_warning "pyproject.toml not found, skipping dependency sync before tests"
    fi

    return 0
}

# Run tests using run_tests.py
run_tests() {
    log_info "Running tests for root module..."

    # Ensure dependencies are synced before running tests
    if ! sync_before_tests; then
        log_error "Dependency sync before tests failed"
        return 1
    fi

    if [ -f "base/scripts/run_tests.py" ]; then
        # Use ami-run to execute the test script
        if ./scripts/ami-run base/scripts/run_tests.py .; then
            log_success "All tests passed!"
            return 0
        else
            log_error "Tests failed - aborting installation"
            return 1
        fi
    else
        log_error "Test runner not found at base/scripts/run_tests.py"
        return 1
    fi
}

