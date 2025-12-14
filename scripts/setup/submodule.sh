#!/usr/bin/env bash

# Submodule setup functions for AMI Orchestrator
# This script incorporates functionality from the old module-setup script

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_SCRIPT="$SCRIPT_DIR/common.sh"
if [ -f "$COMMON_SCRIPT" ]; then
    source "$COMMON_SCRIPT"
else
    echo "ERROR: common.sh not found at $COMMON_SCRIPT"
    exit 1
fi

# Sync dependencies with uv (using bootstrapped binary)
sync_dependencies() {
    local module_root="${1:-.}"
    log_info "Syncing dependencies with uv (including dev)..."
    cd "$module_root"
    # Run uv sync but don't fail on exit code 1 which uv sometimes returns for legitimate reasons
    output=$("$UV_CMD" sync --dev 2>&1)
    local exit_code=$?
    echo "$output"
    # uv sync can return 1 for "already synced" or other non-error conditions
    # Only fail if there are actual error messages in the output and exit code is not 1
    if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
        # If exit code is not 0 or 1, that's a real error
        log_error "uv sync failed with code $exit_code:"
        echo "$output" >&2
        return 1
    elif [[ "$output" == *"ERROR"* ]] || [[ "$output" == *"error"* ]]; then
        # If there are error messages in the output, that's a problem
        log_error "uv sync reported errors:"
        echo "$output" >&2
        return 1
    fi
    return 0
}

# Find orchestrator root by locating /base directory
_find_orchestrator_root() {
    local start_dir="${1:-.}"
    local current_dir="$(cd "$start_dir" && pwd)"

    while [ "$current_dir" != "/" ]; do
        if [ -d "$current_dir/base" ]; then
            echo "$current_dir"
            return 0
        fi
        current_dir="$(dirname "$current_dir")"
    done

    # If we reached root without finding base, return original directory
    echo "$start_dir"
}

# Install pre-commit hooks
install_precommit() {
    local module_root="${1:-.}"

    log_info "Skipping native git hook installation - use scripts/git_commit.sh and scripts/git_push.sh instead"
    return 0
}


# Setup child submodules recursively
setup_child_submodules() {
    local module_root="${1:-.}"

    # Convert to absolute path to avoid issues with relative path globs
    local abs_module_root
    abs_module_root=$(cd "$module_root" && pwd)

    # Array to store child modules with setup files
    local children_with_setup=()
    local child_count=0

    # Use find to list directories directly - store in a temporary file
    local temp_file=$(mktemp)
    find "$abs_module_root" -mindepth 1 -maxdepth 1 -type d -not -path "$abs_module_root" > "$temp_file"

    while IFS= read -r child_dir; do
        if [ -n "$child_dir" ] && [ -d "$child_dir" ]; then
            local child_name=$(basename "$child_dir")
            # Skip hidden directories
            if [[ "$child_name" != .* ]]; then
            # Check for Makefile
            if [ -f "$child_dir/Makefile" ]; then
                children_with_setup[$child_count]="$child_dir:Makefile"
                child_count=$((child_count + 1))
            fi
            fi
        fi
    done < "$temp_file"

    rm -f "$temp_file"

    if [ $child_count -eq 0 ]; then
        return 0
    fi

    log_info ""
    log_info "============================================================"
    log_info "Setting up $child_count child submodule(s)"
    log_info "============================================================"

    for ((i = 0; i < child_count; i++)); do
        # Split the entry by colon to get path and filename
        local child_entry="${children_with_setup[$i]}"
        local child_path="${child_entry%%:*}"
        local child_setup_type="${child_entry#*:}"
        local child_name=$(basename "$child_path")

        log_info ""
        log_info "Running setup for $child_name..."

        if [ "$child_setup_type" = "Makefile" ]; then
            if (cd "$child_path" && make setup); then
                log_info "✓ $child_name setup complete"
            else
                log_warning "Setup for $child_name failed with code $?"
                return 1
            fi
        else
            log_warning "Unknown setup type for $child_name: $child_setup_type"
        fi
    done
}

# Main setup function for modules
setup_module() {
    local module_root="${1:-.}"
    local project_name="${2:-$(basename "$module_root")}"
    local skip_submodules="${3:-false}"

    log_info "============================================================"
    log_info "Setting up ${project_name} Development Environment"
    log_info "Module root: $module_root"
    log_info "============================================================"

    if ! check_uv; then
        return 1
    fi

    ensure_uv_python "3.12"

    local pyproject="$module_root/pyproject.toml"
    if [ ! -f "$pyproject" ]; then
        log_error "pyproject.toml is required but missing at $pyproject"
        log_info "Every module must define dependencies via pyproject.toml for reproducibility."
        return 1
    fi

    # Run setup-shell.sh to ensure environment is properly configured
    log_info "Running scripts/setup-shell.sh..."
    if [ -f "scripts/setup-shell.sh" ]; then
        # Source the setup script to configure environment
        source "scripts/setup-shell.sh" || log_warning "setup-shell.sh had issues"
    else
        log_warning "scripts/setup-shell.sh not found"
    fi

    # Create virtual environment only if it doesn't already exist
    cd "$module_root"
    if [ -d ".venv" ]; then
        log_info "Virtual environment already exists, skipping creation..."
        # Still need to sync dependencies to ensure latest requirements are met
        log_info "Syncing dependencies with existing virtual environment..."
    else
        log_info "Creating virtual environment..."
        "$UV_CMD" venv --python 3.12 .venv
    fi

    # Sync dependencies from pyproject.toml
    if ! sync_dependencies "$module_root"; then
        return 1
    fi


    # Skip git hook installation - all commit/push validation now done by scripts/git_commit.sh and scripts/git_push.sh
    log_info "Git hooks skipped - all validation handled by scripts/git_commit.sh and scripts/git_push.sh"

    # Setup direct child submodules recursively (only if not skipping)
    if [ "$skip_submodules" = false ]; then
        if ! setup_child_submodules "$module_root"; then
            log_info "No child submodules to setup, or submodule setup completed."
        fi
    else
        log_info "Skipping submodule setup (--skip-submodules flag used)"
    fi

    log_info ""
    log_info "============================================================"
    log_info "${project_name} Development Environment Setup Complete!"
    log_info "Activate the venv:"
    log_info "  source $module_root/.venv/bin/activate"
    log_info "Run tests:"
    log_info "  uv run pytest -q"
    log_info "============================================================"

    return 0
}

# Run module setup for all submodules
run_submodule_setup() {
    log_info "Running module setup for all submodules..."

    # Find all modules with Makefile files
    local modules=()
    for dir in */; do
        if [[ -d "$dir" && -f "$dir/Makefile" ]]; then
            modules+=("$dir")
        fi
    done

    if [ ${#modules[@]} -eq 0 ]; then
        log_info "No submodules with Makefile found"
        return 0
    fi

    log_info "Found ${#modules[@]} submodules to set up: ${modules[*]}"

    for module in "${modules[@]}"; do
        local module_name="${module%/}"
        log_info "Setting up submodule: $module_name"
        if [ -f "$module_name/Makefile" ]; then
            # Use make to execute the module setup
            if (cd "$module_name" && make setup); then
                log_success "Submodule $module_name setup complete"
            else
                log_error "Submodule $module_name setup failed"
                return 1
            fi
        fi
    done

    log_success "All submodule setups completed"
    return 0
}