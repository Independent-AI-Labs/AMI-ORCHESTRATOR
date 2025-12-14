#!/usr/bin/env bash

# Node.js setup functions for AMI Orchestrator

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_SCRIPT="$SCRIPT_DIR/common.sh"
if [ -f "$COMMON_SCRIPT" ]; then
    source "$COMMON_SCRIPT"
else
    echo "ERROR: common.sh not found at $COMMON_SCRIPT"
    exit 1
fi

# Function to check if node and npm are available in the bootstrapped environment
check_node() {
    # Look for node and npm in the .boot-linux/node-env directory
    if [ -x "$PWD/.boot-linux/node-env/bin/node" ] && [ -x "$PWD/.boot-linux/node-env/bin/npm" ]; then
        return 0
    else
        return 1
    fi
}

# Install nodeenv to create Node.js environment (using bootstrapped binary)
install_nodeenv() {
    local python_cmd
    if [ -n "${PYTHON_CMD:-}" ] && [ -x "$PYTHON_CMD" ]; then
        python_cmd="$PYTHON_CMD"
    elif [ -x "$PWD/.boot-linux/bin/python" ]; then
        python_cmd="$PWD/.boot-linux/bin/python"
    else
        log_error "No bootstrapped Python available. Run bootstrap first."
        return 1
    fi

    log_info "Installing nodeenv..."
    "$python_cmd" -m pip install nodeenv || {
        log_error "Failed to install nodeenv"
        return 1
    }
}

# Create node environment - always ensure local environment exists (using bootstrapped binary)
setup_node_env() {
    local venv_dir="${1:-.boot-linux/node-env}"
    local python_cmd
    if [ -n "${PYTHON_CMD:-}" ] && [ -x "$PYTHON_CMD" ]; then
        python_cmd="$PYTHON_CMD"
    elif [ -x "$PWD/.boot-linux/bin/python" ]; then
        python_cmd="$PWD/.boot-linux/bin/python"
    else
        log_error "No bootstrapped Python available. Run bootstrap first."
        return 1
    fi

    # Always ensure nodeenv is available in the specified Python environment
    if ! "$python_cmd" -c "import nodeenv" 2>/dev/null; then
        log_info "Installing nodeenv..."
        "$python_cmd" -m pip install nodeenv || {
            log_error "Failed to install nodeenv"
            return 1
        }
    fi

    log_info "Creating Node.js environment in $venv_dir (ensuring isolated environment)..."
    # Create fresh node environment to ensure isolation
    if [ -d "$venv_dir" ]; then
        log_warning "⚠️  Found existing node environment at $venv_dir"
        # Check if user wants to overwrite
        log_info "Removing existing node environment to ensure clean isolation..."
        rm -rf "$venv_dir"
    fi

    nodeenv --node=24.11.1 "$venv_dir" || {
        log_error "Failed to create isolated Node.js environment in .boot-linux/node-env with Node.js 24.11.1"
        return 1
    }

    # Update PATH to prioritize the local node environment for subsequent commands
    export PATH="$venv_dir/bin:$PATH"

    return 0
}

# Install Node.js CLI agents
install_node_agents() {
    # Get the project root directory before any potential directory changes
    local project_root
    project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../" && pwd)"

    # First make sure we have node and npm available - set up node environment if needed
    if ! check_node; then
        log_info "Node.js or npm not found, installing via nodeenv..."
        install_nodeenv || {
            log_error "Failed to install nodeenv"
            return 1
        }
        setup_node_env || {
            log_error "Failed to set up node environment"
            return 1
        }
    else
        # Even if node/npm exist, ensure we're using an isolated environment
        setup_node_env || {
            log_error "Failed to set up node environment"
            return 1
        }
    fi

    # Install agents using npm from the scripts/package.json - they will go into the existing .venv environment
    log_info "Installing Node.js CLI agents to .venv/node_modules from scripts/package.json..."

    # Change to the scripts directory and install packages to the .venv directory using prefix
    # Use --no-save to prevent creating package.json in .venv and ensure clean local installation
    # Use --ignore-scripts to avoid running postinstall scripts that might create unwanted node_modules
    # Use --force to ensure latest compatible versions according to package.json
    # Install production dependencies only (skip devDependencies)
    if [ ! -f "$project_root/scripts/package.json" ]; then
        log_error "scripts/package.json not found, cannot install Node.js agents"
        return 1
    fi

    # Remove existing node_modules to ensure clean installation with latest compatible versions
    if [ -d "$project_root/.venv/node_modules" ]; then
        log_info "Removing existing node_modules to ensure clean installation..."
        rm -rf "$project_root/.venv/node_modules"
    fi

    # Copy the package.json to .venv to ensure npm reads dependencies from it
    cp "$project_root/scripts/package.json" "$project_root/.venv/package.json"
    # Run npm install in .venv directory to install dependencies specified in package.json
    cd "$project_root/.venv" && "$project_root/.boot-linux/node-env/bin/npm" install --no-save --ignore-scripts --force --production
    # Remove the temporary package.json after installation
    rm -f "$project_root/.venv/package.json"
    cd "$project_root"  # Return to original directory

    log_info "✓ Node.js CLI agents installed successfully to .venv/node_modules"
    return 0
}