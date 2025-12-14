#!/usr/bin/env bash

# Common utility functions for AMI Orchestrator setup

# Logging functions
log_info() {
    echo "$1" >&2
}

log_error() {
    echo "ERROR: $1" >&2
}

log_warning() {
    echo "WARNING: $1" >&2
}

log_success() {
    echo "✓ $1" >&2
}

# Check if uv is installed (from bootstrapped environment)
check_uv() {
    # Prefer UV_CMD from environment if available
    if [ -n "${UV_CMD:-}" ] && [ -x "$UV_CMD" ]; then
        return 0
    # Look for uv in .boot-linux only - no system alternative allowed
    elif [ -x "$PWD/.boot-linux/bin/uv" ]; then
        UV_CMD="$PWD/.boot-linux/bin/uv"
        export UV_CMD
        return 0
    else
        log_error "uv is not installed in the bootstrapped environment."
        log_info "Run bootstrap script first: ./scripts/setup/bootstrap.sh"
        return 1
    fi
}

# Ensure Python version is installed via uv (using bootstrapped binary)
ensure_uv_python() {
    local version="${1:-3.12}"
    if ! "$UV_CMD" python find "$version" >/dev/null 2>&1; then
        log_info "Installing Python $version toolchain via uv..."
        "$UV_CMD" python install "$version" || {
            log_error "Failed to install Python $version via uv"
            return 1
        }
    fi
}

# Convert SSH GitHub URL to HTTPS if applicable
_to_https() {
    local url="$1"
    if [[ "$url" =~ ^git@github\.com: ]]; then
        echo "https://github.com/${url#git@github.com:}"
    else
        echo "$url"
    fi
}

# Check for uncommitted changes in submodules
check_submodule_changes() {
    local git_cmd="$1"
    log_info "Checking for uncommitted changes in submodules..."

    # Get list of all submodules
    local submodules
    submodules=$("$git_cmd" submodule foreach --quiet 'echo $path' 2>/dev/null) || true

    local has_changes=0
    for submodule in $submodules; do
        if [ -d "$submodule/.git" ]; then
            # Check for uncommitted changes in submodule
            if ! "$git_cmd" -C "$submodule" diff-index --quiet HEAD --; then
                log_warning "⚠️  Submodule $submodule has uncommitted changes!"
                has_changes=1
            fi

            # Check for untracked files in submodule
            local untracked
            untracked=$("$git_cmd" -C "$submodule" ls-files --others --exclude-standard)
            if [ -n "$untracked" ]; then
                log_warning "⚠️  Submodule $submodule has untracked files:"
                echo "$untracked" | head -5 | while read -r file; do
                    if [ -n "$file" ]; then
                        log_warning "   - $submodule/$file"
                    fi
                done
                if [ "$(echo "$untracked" | wc -l)" -gt 5 ]; then
                    log_warning "   ... and more"
                fi
                has_changes=1
            fi
        fi
    done

    if [ $has_changes -eq 1 ]; then
        log_warning "⚠️  WARNING: Uncommitted changes detected in submodules!"
        log_info "This operation may overwrite uncommitted changes."
        log_info "Continue anyway? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "Operation cancelled by user."
            return 1
        fi
    fi

    return 0
}

# Initialize and update git submodules with HTTPS alternative (using bootstrapped binary)
ensure_git_submodules() {
    # Set up git command from bootstrapped environment
    local git_cmd
    if [ -n "${GIT_CMD:-}" ] && [ -x "$GIT_CMD" ]; then
        git_cmd="$GIT_CMD"
    elif [ -x "$PWD/.boot-linux/bin/git" ]; then
        git_cmd="$PWD/.boot-linux/bin/git"
    else
        git_cmd="git"
    fi

    if [ ! -d ".git" ]; then
        log_warning "No .git directory found; skipping submodule init."
        return 0
    fi

    # Check for uncommitted changes in submodules before updating
    if ! check_submodule_changes "$git_cmd"; then
        return 1
    fi

    log_info "Initializing git submodules (recursive)..."
    if "$git_cmd" submodule update --init --recursive; then
        log_info "✓ Submodules initialized"
        return 0
    fi

    local stderr_output
    stderr_output=$("$git_cmd" submodule update --init --recursive 2>&1) || {
        if [[ "$stderr_output" == *"Permission denied (publickey)"* ]] || [[ "$stderr_output" == *"fatal: Could not read from remote repository"* ]]; then
            log_warning "SSH auth failed for submodules; attempting HTTPS alternative..."

            # Parse .gitmodules to get paths and URLs
            if [ -f ".gitmodules" ]; then
                local line path url https_url
                while IFS= read -r line; do
                    if [[ $line =~ ^[[:space:]]*path[[:space:]]*=[[:space:]]*(.+)$ ]]; then
                        path="${BASH_REMATCH[1]}"
                    elif [[ $line =~ ^[[:space:]]*url[[:space:]]*=[[:space:]]*(.+)$ ]]; then
                        url="${BASH_REMATCH[1]}"
                        https_url=$(_to_https "$url")
                        if [ "$https_url" != "$url" ]; then
                            "$git_cmd" submodule set-url "$path" "$https_url" 2>/dev/null || log_warning "Could not set HTTPS URL for $path"
                        fi
                        path=""
                        url=""
                    fi
                done < ".gitmodules"

                "$git_cmd" submodule sync --recursive 2>/dev/null || true
            fi

            # Retry update with HTTPS URLs
            if "$git_cmd" submodule update --init --recursive; then
                log_info "✓ Submodules initialized via HTTPS"
                return 0
            else
                log_error "Submodule init failed with HTTPS alternative"
                return 1
            fi
        else
            log_error "Submodule init failed: $stderr_output"
            return 1
        fi
    }

    return 0
}

# Find shell config files
_find_shell_configs() {
    if [ -f "$HOME/.bashrc" ]; then
        echo "bashrc:$HOME/.bashrc"
    fi
    if [ -f "$HOME/.zshrc" ]; then
        echo "zshrc:$HOME/.zshrc"
    fi
}

# Register shell setup by sourcing setup-shell.sh
_register_aliases_in_shell() {
    local shell_rc="$1"
    local content
    content=$(cat "$shell_rc" 2>/dev/null || echo "")

    if [[ "$content" == *"setup-shell.sh"* ]]; then
        return 0  # Already present
    fi

    local ami_root
    ami_root=$(pwd)
    local marker="# AMI Orchestrator Shell Setup"
    local source_line='[ -f "'$ami_root'/scripts/setup-shell.sh" ] && . "'$ami_root'/scripts/setup-shell.sh"'

    {
        echo
        echo "$marker"
        echo "$source_line"
    } >> "$shell_rc"

    return 0
}

register_shell_aliases() {
    local setup_script="scripts/setup-shell.sh"
    if [ ! -f "$setup_script" ]; then
        log_warning "setup-shell.sh not found at $setup_script"
        return 0
    fi

    local shell_configs
    shell_configs=$(_find_shell_configs)
    if [ -z "$shell_configs" ]; then
        log_warning "No .bashrc or .zshrc found in home directory"
        return 0
    fi

    local installed_count=0
    local config
    while IFS= read -r config; do
        if [ -n "$config" ]; then
            local name="${config%%:*}"
            local shell_rc="${config#*:}"
            if _register_aliases_in_shell "$shell_rc"; then
                log_info "✓ Installed AMI shell setup in ~/.${name}"
                ((installed_count++))
            else
                log_info "✓ AMI shell setup already present in ~/.${name}"
            fi
        fi
    done <<< "$shell_configs"

    if [ $installed_count -gt 0 ]; then
        log_info ""
        log_info "To activate immediately:"
        log_info "  source ~/.bashrc  # or: source ~/.zshrc"
        log_info "Or restart your shell."
    fi

    return 0
}