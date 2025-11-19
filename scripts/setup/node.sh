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
        log_info "Removing existing node environment to ensure clean isolation..."
        rm -rf "$venv_dir"
    fi

    nodeenv "$venv_dir" || {
        log_error "Failed to create isolated Node.js environment in .boot-linux/node-env"
        return 1
    }

    # Update PATH to prioritize the local node environment for subsequent commands
    export PATH="$venv_dir/bin:$PATH"

    return 0
}

# Build Qwen CLI from source
build_qwen() {
    local qwen_dir="./cli-agents/qwen-code"
    if [ -d "$qwen_dir" ]; then
        log_info "Building Qwen CLI from source..."
        # Get the project root directory before changing directories
        local project_root
        project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../" && pwd)"

        # Make sure we have node and npm available, using nodeenv if needed
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
        (
            cd "$qwen_dir"
            # Use the npm from .boot-linux/node-env directly using the project root
            "$project_root/.boot-linux/node-env/bin/npm" run build
        ) || {
            log_error "Qwen build failed"
            return 1
        }
        log_info "✓ Qwen CLI built successfully"
    else
        log_info "Qwen source directory not found, skipping build"
    fi
    return 0
}

# Install Node.js CLI agents
install_node_agents() {
    local cli_agents_dir="./cli-agents"

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

    # Build Qwen first
    build_qwen || {
        log_warning "Qwen build failed, but continuing..."
    }

    # Install agents using npm - they will go into the existing .venv environment
    log_info "Installing Node.js CLI agents to .venv/node_modules..."

    # Install packages to the .venv directory using prefix
    # Using the npm from .boot-linux/node-env directly
    # Use --no-save to prevent creating package.json in .venv and ensure clean local installation
    "$project_root/.boot-linux/node-env/bin/npm" install --prefix "$PWD/.venv" --no-save @anthropic-ai/claude-code@2.0.10 @google/gemini-cli@0.11.3 @qwen-code/qwen-code || {
        log_error "Node.js agents installation failed"
        return 1
    }

    log_info "✓ Node.js CLI agents installed successfully to .venv/node_modules"
    return 0
}