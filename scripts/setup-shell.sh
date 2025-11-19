#!/usr/bin/env bash
# AMI Orchestrator Shell Environment Setup
#
# This script configures the shell environment for the AMI Orchestrator system,
# a modular AI agent development platform. It provides convenient command-line
# access to development tools, testing frameworks, service management, and
# AI agent integrations across multiple modules.
#
# The AMI Orchestrator is structured as a multi-module system where each module
# (base, browser, compliance, domains, files, nodes, streams, ux) can have its
# own dependencies and setup while sharing common infrastructure.
#
# USAGE:
#   source scripts/setup-shell.sh        # Load environment temporarily
#   . scripts/setup-shell.sh            # Alternative to 'source' command
#
# PERMANENT INSTALLATION:
#   scripts/setup-shell.sh --install             # Install to ~/.bashrc
#   scripts/setup-shell.sh --install --no-backup # Install without backup
#
# UNINSTALL:
#   scripts/setup-shell.sh --uninstall          # Remove from ~/.bashrc
#
# FEATURES:
#   - Automatically configures PATH to include project virtual environments
#   - Sets PYTHONPATH to make all modules importable from any directory
#   - Provides unified command access via ami-* wrapper functions
#   - Offers navigation shortcuts for all modules
#   - Integrates multiple AI agents (Claude, Gemini, Qwen) with version control
#   - Enables service management and orchestration capabilities
#
# MODULAR ARCHITECTURE:
#   The system follows a hub-and-spoke design with a central 'base' module that:
#   - Defines shared dependencies and utilities
#   - Provides common testing and setup infrastructure
#   - Contains environment management tools and scripts
#   - Orchestrates child module setup and testing
#
#   Child modules include:
#   - browser/       - Web automation and browser-based agent interactions
#   - compliance/    - Security, compliance, and validation tools
#   - domains/       - Domain-specific business logic and services
#   - files/         - File handling, storage, and data processing
#   - nodes/         - Node management and orchestration services
#   - streams/       - Real-time data streaming and processing
#   - ux/            - User experience and interface components
#
# COMMAND CATEGORIES:
#   Core Wrappers:    ami-run, ami-uv, ami-agent, ami-repo
#   Service Mgmt:     ami-services, ami-start, ami-stop, ami-restart, ami-profile
#   Testing:          ami-test with auto-discovery of modules
#   Setup/Install:    ami-install, ami-setup for modules
#   Code Quality:     ami-codecheck for pre-commit hooks
#   Git Operations:   ami-status, ami-diff, ami-log with module auto-detection
#   Navigation:       ami-base, ami-browser, etc. for quick directory access
#   Utilities:        ami-check-storage, ami-gcloud, ami-info

# ============================================================================
# 0. AUTO-INSTALL TO BASHRC (if requested)
# ============================================================================

_install_to_bashrc() {
    local backup="${1:-true}"
    local bashrc="$HOME/.bashrc"
    local setup_script="$AMI_ROOT/scripts/setup-shell.sh"
    local marker="# AMI Orchestrator Shell Setup"
    local source_line="[ -f \"$setup_script\" ] && . \"$setup_script\""

    # Check if already installed
    if grep -qF "$marker" "$bashrc" 2>/dev/null; then
        echo -e "${YELLOW}⚠${NC} AMI shell setup already installed in $bashrc"
        return 0
    fi

    # Backup .bashrc if requested
    if [[ "$backup" == "true" ]]; then
        cp "$bashrc" "$bashrc.backup-$(date +%Y%m%d-%H%M%S)"
        echo -e "${GREEN}✓${NC} Backed up $bashrc"
    fi

    # Remove old AMI aliases (lines containing ami-run, ami-uv from old install methods)
    if grep -q "# AMI Orchestrator - auto-registered" "$bashrc" 2>/dev/null; then
        echo -e "${BLUE}→${NC} Removing old AMI aliases from $bashrc"
        sed -i '/# AMI Orchestrator - auto-registered/d' "$bashrc"
        sed -i '/# AMI Orchestrator - auto-installed/d' "$bashrc"
        sed -i '/alias ami-run=/d' "$bashrc"
        sed -i '/alias ami-uv=/d' "$bashrc"
        echo -e "${GREEN}✓${NC} Cleaned up old aliases"
    fi

    # Add source line
    echo "" >> "$bashrc"
    echo "$marker" >> "$bashrc"
    echo "$source_line" >> "$bashrc"

    echo -e "${GREEN}✓${NC} Installed AMI shell setup to $bashrc"
    echo -e "${YELLOW}→${NC} Run 'source ~/.bashrc' or restart your shell to activate"
}

_uninstall_from_bashrc() {
    local bashrc="$HOME/.bashrc"
    local marker="# AMI Orchestrator Shell Setup"

    if ! grep -qF "$marker" "$bashrc" 2>/dev/null; then
        echo -e "${YELLOW}⚠${NC} AMI shell setup not found in $bashrc"
        return 0
    fi

    # Backup first
    cp "$bashrc" "$bashrc.backup-$(date +%Y%m%d-%H%M%S)"
    echo -e "${GREEN}✓${NC} Backed up $bashrc"

    # Remove the marker and the following line
    sed -i '/# AMI Orchestrator Shell Setup/,+1d' "$bashrc"

    echo -e "${GREEN}✓${NC} Removed AMI shell setup from $bashrc"
    echo -e "${YELLOW}→${NC} Run 'source ~/.bashrc' or restart your shell to apply"
}

# Handle --install/--uninstall/--quiet flags
if [[ "${1:-}" == "--install" ]]; then
    # Get AMI_ROOT early for install
    AMI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    export AMI_ROOT

    # Source color definitions and banner functions
    source "$AMI_ROOT/scripts/ami-banner.sh"

    backup="true"
    [[ "${2:-}" == "--no-backup" ]] && backup="false"
    _install_to_bashrc "$backup"
    exit 0
elif [[ "${1:-}" == "--uninstall" ]]; then
    # Source color definitions and banner functions
    AMI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    export AMI_ROOT
    source "$AMI_ROOT/scripts/ami-banner.sh"

    _uninstall_from_bashrc
    exit 0
elif [[ "${1:-}" == "--quiet" ]] || [[ "${1:-}" == "-q" ]]; then
    # Quiet mode - set quiet flag and continue with setup
    AMI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    export AMI_ROOT
    export AMI_QUIET_MODE=1
    # Source color definitions and banner functions for quiet mode
    source "$AMI_ROOT/scripts/ami-banner.sh"
else
    # Get the root directory (parent of scripts/)
    AMI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    export AMI_ROOT
    # Source color definitions and banner functions
    source "$AMI_ROOT/scripts/ami-banner.sh"
fi

# ============================================================================
# 1. ENVIRONMENT DETECTION & SETUP
# ============================================================================

# Source color definitions and banner functions
source "$AMI_ROOT/scripts/ami-banner.sh"

# Default AMI_QUIET_MODE to 0 if not set
AMI_QUIET_MODE=${AMI_QUIET_MODE:-0}

# Show initial banner based on quiet mode
if [[ "$AMI_QUIET_MODE" != "1" ]]; then
    _ami_echo "${BLUE}🚀 Setting up AMI Orchestrator shell environment...${NC}"
fi

# ============================================================================
# 2. PATH AND PYTHONPATH CONFIGURATION
# ============================================================================

# Add .boot-linux/bin to PATH to make bootstrapped tools available (takes precedence)
# This includes node, npm, npx and other bootstrapped binaries
if [[ -d "$AMI_ROOT/.boot-linux/bin" ]]; then
    export PATH="$AMI_ROOT/.boot-linux/bin:$PATH"
    echo -e "${GREEN}✓${NC} Added .boot-linux/bin to PATH (takes precedence)"
    echo -e "  ${CYAN}→${NC} Access to: node, npm, npx, and other bootstrapped tools"
fi

# Add root .venv/bin to PATH (lower precedence than bootstrapped tools)
# The root virtual environment contains the core Python interpreter and global tools
# used across all modules in the orchestrator system
if [[ -d "$AMI_ROOT/.venv/bin" ]]; then
    export PATH="$AMI_ROOT/.venv/bin:$PATH"
    if [[ $? -ne 0 ]]; then
        echo -e "${YELLOW}⚠${NC} Warning: root .venv/bin not found. Run 'module_setup.py' to create venv."
        echo -e "  ${CYAN}→${NC} Expected location: $AMI_ROOT/.venv/bin"
    else
        echo -e "${GREEN}✓${NC} Added root .venv/bin to PATH"
        echo -e "  ${CYAN}→${NC} Access to: python, pytest, podman, claude, fastmcp, uvicorn, ruff, mypy, etc."
    fi
else
    echo -e "${YELLOW}⚠${NC} Warning: root .venv/bin not found. Run 'module_setup.py' to create venv."
    echo -e "  ${CYAN}→${NC} Expected location: $AMI_ROOT/.venv/bin"
fi

# Set PYTHONPATH to include all modules for cross-module imports
export PYTHONPATH="$AMI_ROOT:$AMI_ROOT/base:$AMI_ROOT/browser:$AMI_ROOT/compliance:$AMI_ROOT/domains:$AMI_ROOT/files:$AMI_ROOT/nodes:$AMI_ROOT/streams:${PYTHONPATH:-}"
echo -e "${GREEN}✓${NC} Set PYTHONPATH to include all modules"

# ============================================================================
# 3. HELPER FUNCTIONS (Internal use)
# ============================================================================

_detect_current_module() {
    # Detect which module PWD is in by walking up
    # Returns module name (base, browser, etc.) or "." for root
    local current="$PWD"

    while [[ "$current" != "/" && "$current" != "$AMI_ROOT" ]]; do
        # Check if this is a module root (has backend/ or is a known module)
        local rel_path="${current#$AMI_ROOT/}"

        # If we're at a first-level directory under AMI_ROOT, that's likely the module
        if [[ "$rel_path" != "$current" && "$rel_path" != */* ]]; then
            echo "$rel_path"
            return 0
        fi

        current="$(dirname "$current")"
    done

    # Default to root
    echo "."
}

_find_module_root() {
    # Find module root by walking up looking for backend/ + requirements.txt
    # Returns path to module root or AMI_ROOT/base as default
    local current="$PWD"

    while [[ "$current" != "/" ]]; do
        # Module root has both backend/ and requirements.txt
        if [[ -d "$current/backend" && -f "$current/requirements.txt" ]]; then
            echo "$current"
            return 0
        fi
        # Also check for .venv as a module indicator
        if [[ -d "$current/.venv" && -d "$current/backend" ]]; then
            echo "$current"
            return 0
        fi
        current="$(dirname "$current")"
    done

    # Default to base
    echo "$AMI_ROOT/base"
}

_find_nearest_module_setup() {
    # Walk up from PWD looking for module_setup.py
    # Returns path to module_setup.py or AMI_ROOT/base/module_setup.py as default
    local current="$PWD"

    while [[ "$current" != "/" ]]; do
        if [[ -f "$current/module_setup.py" ]]; then
            echo "$current/module_setup.py"
            return 0
        fi
        current="$(dirname "$current")"
    done

    # Default to base module setup
    echo "$AMI_ROOT/base/module_setup.py"
}

# ============================================================================
# 4. CORE WRAPPERS (Root-only execution)
# ============================================================================

# Core execution wrapper functions that provide unified access to key system tools
# These functions delegate to corresponding scripts in the /scripts directory

ami-run() {
    # Universal Python execution wrapper for AMI Orchestrator
    # Finds nearest .venv up the directory hierarchy from PWD
    # Supports: ami-run install/setup commands, running tests, executing scripts
    "$AMI_ROOT/scripts/ami-run" "$@"
}

ami-uv() {
    # Universal UV execution wrapper for AMI Orchestrator
    # Always uses root .venv uv, auto-targets nearest .venv with --python flag
    # Handles package management across the modular system
    "$AMI_ROOT/scripts/ami-uv" "$@"
}

ami-agent() {
    # Wrapper for AI agent orchestration and automation
    # Uses root venv and handles agent-specific CLI tools, authentication, and version management
    # Includes Claude, Gemini, and Qwen agent integrations
    # Available modes: interactive, continue, resume, print, hook, audit, tasks, sync, docs
    "$AMI_ROOT/scripts/ami-agent" "$@"
}

ami-repo() {
    # Git repository server management CLI
    # Wrapper for scripts/ami_repo.py which manages git operations across modules
    # Available commands: init, create, list, url, clone, delete, info, add-key, list-keys, remove-key, setup-ssh, generate-key, bootstrap-ssh, service
    "$AMI_ROOT/scripts/ami-repo" "$@"
}

ami-podman() {
    # Direct access to podman from the bootstrapped environment
    # DEPRECATED: Use ami-run podman [args...] instead
    # This function is maintained for backward compatibility
    ami-run podman "$@"
}

# ============================================================================
# 4.5. CLI TOOL WRAPPERS
# ============================================================================

# Tool wrappers that ensure consistent environment usage
# These maintain backward compatibility while forwarding to the unified ami-run command

ami-node() {
    # Node.js execution wrapper for consistent environment usage
    # DEPRECATED: Use ami-run node [args...] instead
    # This function is maintained for backward compatibility
    ami-run node "$@"
}

ami-npm() {
    # NPM execution wrapper for consistent environment usage
    # DEPRECATED: Use ami-run npm [args...] instead
    # This function is maintained for backward compatibility
    ami-run npm "$@"
}

ami-npx() {
    # NPX execution wrapper for consistent environment usage
    # DEPRECATED: Use ami-run npx [args...] instead
    # This function is maintained for backward compatibility
    ami-run npx "$@"
}

# AI agent CLI wrappers that ensure version control and prevent unwanted auto-updates
# These use version-controlled binaries from the project's .venv/node_modules directory

ami-claude() {
    # Claude Code AI assistant CLI wrapper
    # Uses version-controlled binary to ensure consistent behavior across environments
    # Prevents auto-updates that could affect agent behavior in development
    "$AMI_ROOT/.venv/node_modules/.bin/claude" "$@"
}

ami-gemini() {
    # Gemini CLI AI assistant wrapper
    # Uses version-controlled binary to ensure consistent behavior across environments
    # Handles authentication setup and version management automatically
    "$AMI_ROOT/.venv/node_modules/.bin/gemini" "$@"
}

ami-qwen() {
    # Qwen Code AI assistant CLI wrapper
    # Uses version-controlled binary to ensure consistent behavior across environments
    # Part of the multi-agent integration in the AMI Orchestrator system
    "$AMI_ROOT/.venv/node_modules/.bin/qwen" "$@"
}

# ============================================================================
# 5. SERVICE MANAGEMENT (Root-only execution)
# ============================================================================

# Service orchestration functions that manage processes and profiles for the system
# These commands control the nodes module's process management system

ami-services() {
    # Service orchestration with multiple subcommands
    # Handles process management, profiles, and multi-module operations
    if [[ $# -eq 0 ]]; then
        echo -e "${RED}Error: No command provided${NC}"
        echo -e "Usage: ami-services [command] [args...]"
        echo -e "Available commands:"
        echo -e "  start <profile>        - Start processes/profiles with visual feedback"
        echo -e "  stop <profile>         - Stop processes/profiles with visual feedback"
        echo -e "  restart <profile>      - Restart processes/profiles with visual feedback"
        echo -e "  profile [args...]      - Manage coordinated service profiles"
        echo -e "  status                 - List status of all managed processes"
        return 1
    fi

    local cmd="$1"
    shift

    case "$cmd" in
        start)
            echo -e "${BLUE}Starting process/profile:${NC} $*"
            # Determine if the argument is a profile or a process
            if [[ $# -gt 0 ]]; then
                local target="$1"
                # Test if it's a valid profile by trying to list profiles
                if ami-run nodes/scripts/setup_service.py profile info "$target" >/dev/null 2>&1; then
                    # It's a profile
                    ami-run nodes/scripts/setup_service.py profile start "$@"
                else
                    # Assume it's a process
                    ami-run nodes/scripts/setup_service.py process start "$@"
                fi
            else
                echo -e "${RED}Error: No profile or process name provided${NC}"
                return 1
            fi
            ;;
        stop)
            echo -e "${YELLOW}Stopping process/profile:${NC} $*"
            # Determine if the argument is a profile or a process
            if [[ $# -gt 0 ]]; then
                local target="$1"
                # Test if it's a valid profile by trying to list profiles
                if ami-run nodes/scripts/setup_service.py profile info "$target" >/dev/null 2>&1; then
                    # It's a profile
                    ami-run nodes/scripts/setup_service.py profile stop "$@"
                else
                    # Assume it's a process
                    ami-run nodes/scripts/setup_service.py process stop "$@"
                fi
            else
                echo -e "${RED}Error: No profile or process name provided${NC}"
                return 1
            fi
            ;;
        restart)
            echo -e "${YELLOW}Restarting process/profile:${NC} $*"
            # Determine if the argument is a profile or a process
            if [[ $# -gt 0 ]]; then
                local target="$1"
                # Test if it's a valid profile by trying to list profiles
                if ami-run nodes/scripts/setup_service.py profile info "$target" >/dev/null 2>&1; then
                    # It's a profile - stop then start
                    ami-run nodes/scripts/setup_service.py profile stop "$@"
                    sleep 2
                    ami-run nodes/scripts/setup_service.py profile start "$@"
                else
                    # Assume it's a process - stop then start
                    ami-run nodes/scripts/setup_service.py process stop "$@"
                    sleep 2
                    ami-run nodes/scripts/setup_service.py process start "$@"
                fi
            else
                echo -e "${RED}Error: No profile or process name provided${NC}"
                return 1
            fi
            ;;
        profile)
            echo -e "${BLUE}Managing profile:${NC} $*"
            # Check if it's a list command to use human output
            if [[ "$1" == "list" ]]; then
                AMI_SERVICES_HUMAN_OUTPUT=1 ami-run nodes/scripts/setup_service.py profile "$@"
            else
                ami-run nodes/scripts/setup_service.py profile "$@"
            fi
            ;;
        status)
            echo -e "${BLUE}Listing all managed processes status:${NC}"
            AMI_SERVICES_HUMAN_OUTPUT=1 ami-run nodes/scripts/setup_service.py process list
            ;;
        *)
            echo -e "${RED}Error: Unknown command '$cmd'${NC}"
            echo -e "Usage: ami-services [command] [args...]"
            echo -e "Available commands:"
            echo -e "  start <profile>        - Start processes/profiles with visual feedback"
            echo -e "  stop <profile>         - Stop processes/profiles with visual feedback"
            echo -e "  restart <profile>      - Restart processes/profiles with visual feedback"
            echo -e "  profile [args...]      - Manage coordinated service profiles"
            echo -e "  status                 - List status of all managed processes"
            return 1
            ;;
    esac
}

# ============================================================================
# 6. DYNAMIC DISCOVERY FUNCTIONS
# ============================================================================

# Functions that automatically detect which module to operate on
# These functions include smart module detection and path resolution

ami-test() {
    # Run tests for a module with automatic module detection
    # Takes optional module path as parameter: ami-test [module] [pytest-args]
    # If no module specified, auto-detects from current working directory
    # Uses the smart run_tests.py which can run tests across the modular system
    if [[ $# -gt 0 && "$1" != -* ]]; then
        # Module specified as first arg
        local module="$1"
        shift
        echo -e "${BLUE}Running tests for module:${NC} $module"
        ami-run "$module/scripts/run_tests.py" "$@"
    else
        # Auto-detect current module
        local module_root="$(_find_module_root)"
        local module_name="${module_root#$AMI_ROOT/}"
        [[ "$module_name" == "$module_root" ]] && module_name="base"

        echo -e "${BLUE}Running tests for detected module:${NC} $module_name"
        ami-run "$AMI_ROOT/$module_name/scripts/run_tests.py" "$@"
    fi
}

ami-setup() {
    # Run module setup for a module with automatic module detection
    # Takes optional module path as parameter: ami-setup [module] [setup-args]
    # If no module specified, finds nearest module_setup.py in directory hierarchy
    # Handles dependencies, virtual environment setup, and git hook installation
    if [[ $# -gt 0 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
        echo -e "${BLUE}AMI Module Setup${NC}"
        echo -e "Usage: ami-setup [module] [args...]"
        echo -e "  module    Optional module name (auto-detected if not specified)"
        echo -e "  args...   Arguments passed to module_setup.py"
        echo -e ""
        echo -e "Runs module setup (module_setup.py) for a specific module with auto-detection."
        echo -e "If no module is specified, finds the nearest module_setup.py in directory hierarchy."
    elif [[ $# -gt 0 && -f "$AMI_ROOT/$1/module_setup.py" ]]; then
        # Module specified
        local module="$1"
        shift
        echo -e "${BLUE}Running module_setup.py for:${NC} $module"
        ami-run "$module/module_setup.py" "$@"
    else
        # Find nearest module_setup.py
        local setup_path="$(_find_nearest_module_setup)"
        local module_dir="$(dirname "$setup_path")"
        local module_name="${module_dir#$AMI_ROOT/}"

        if [[ "$module_name" == "$module_dir" || "$module_name" == "." ]]; then
            echo -e "${BLUE}Running orchestrator setup${NC}"
        else
            echo -e "${BLUE}Running module_setup.py for:${NC} $module_name"
        fi

        ami-run "$setup_path" "$@"
    fi
}

ami-install() {
    # Call the actual install script which performs comprehensive system installation
    # This includes: git submodule initialization, environment bootstrapping,
    # node agent installation, testing, and recursive module setup
    # Passes all arguments directly to the install script
    if [[ $# -gt 0 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
        echo -e "${BLUE}AMI System Installation${NC}"
        echo -e "Usage: ami-install [options]"
        echo -e "Options:"
        echo -e "  --recreate    Delete .venv and recreate environment using .boot-linux, then proceed with install"
        echo -e "  --help, -h    Show this help message"
        echo -e ""
        echo -e "Runs the comprehensive system installation via the install script."
        echo -e "This includes: git submodule initialization, environment bootstrapping,"
        echo -e "node agent installation, testing, and recursive module setup."
        "$AMI_ROOT/install" --help 2>/dev/null || true
    else
        echo -e "${BLUE}Running comprehensive system installation via install script${NC}"
        "$AMI_ROOT/install" "$@"
    fi
}

# ============================================================================
# 7. CODE QUALITY TOOLS (Root-only execution)
# ============================================================================

# Code quality and linting functions that run pre-commit hooks across the system

ami-codecheck() {
    # Run pre-commit hooks for code quality assurance
    # This ensures consistent code style and quality across all modules
    # No args: run all hooks
    # With args: run specific hooks by ID
    # Examples:
    #   ami-codecheck              → run all hooks
    #   ami-codecheck ruff         → run only ruff hook for formatting
    #   ami-codecheck mypy         → run only mypy hook for type checking
    #   ami-codecheck ruff mypy    → run ruff and mypy hooks
    #
    # Available hooks: ruff, ruff-format, mypy, validate-docs-links, check-yaml,
    #                  check-added-large-files, check-merge-conflict, debug-statements

    cd "$AMI_ROOT" || return 1

    if [[ $# -eq 0 ]]; then
        echo -e "${BLUE}Running all pre-commit hooks...${NC}"
        pre-commit run --all-files
    else
        echo -e "${BLUE}Running pre-commit hooks:${NC} $*"
        for hook_id in "$@"; do
            echo -e "${CYAN}→${NC} Running hook: $hook_id"
            pre-commit run "$hook_id" --all-files
        done
    fi
}

# ============================================================================
# 8. UTILITY WRAPPERS
# ============================================================================

# General utility functions that provide access to specialized tools and services

ami-check-storage() {
    # Validate DataOps storage backends defined in storage-config.yaml
    # Checks that all configured storage backends are accessible and properly configured
    # Part of the data operations infrastructure in the base module
    echo -e "${BLUE}Checking storage backends...${NC}"
    ami-run base/scripts/check_storage.py "$@"
}

ami-backup() {
    # Backup to Google Drive with impersonation auth
    # Usage: ami-backup
    ami-run scripts/backup/backup_to_gdrive.py --auth-mode impersonation
}

ami-gcloud() {
    # Google Cloud SDK wrapper with local installation preference
    # Uses local .gcloud installation if available, otherwise falls back to system gcloud
    # This ensures consistent gcloud version across environments
    # Usage: ami-gcloud [gcloud-args]
    local gcloud_path

    # Check for local installation first
    if [[ -f "$AMI_ROOT/.gcloud/google-cloud-sdk/bin/gcloud" ]]; then
        gcloud_path="$AMI_ROOT/.gcloud/google-cloud-sdk/bin/gcloud"
    else
        # Fall back to system gcloud
        gcloud_path=$(which gcloud 2>/dev/null || echo "")
        if [[ -z "$gcloud_path" ]]; then
            echo -e "${RED}Error: gcloud not found${NC}"
            echo -e "Install with: ami-run scripts/install_gcloud.sh"
            return 1
        fi
    fi

    echo -e "${BLUE}Running gcloud via:${NC} $gcloud_path"
    "$gcloud_path" "$@"
}


# ============================================================================
# 10. GIT SHORTCUTS (Take module path as parameter)
# ============================================================================


# Function to perform git operations across all modules
_run_git_operation_for_all() {
    local git_cmd="$1"
    local description="$2"
    local root_cmd="$3"

    echo -e "${BLUE}$description:${NC}"
    for module_dir in "$AMI_ROOT"/*; do
        if [[ -d "$module_dir/.git" ]]; then
            local module="$(basename "$module_dir")"
            echo -e "\n${YELLOW}=== $module ===${NC}"
            (cd "$module_dir" && git $git_cmd)
        fi
    done

    # Also check root
    if [[ -d "$AMI_ROOT/.git" ]]; then
        echo -e "\n${YELLOW}=== orchestrator (root) ===${NC}"
        (cd "$AMI_ROOT" && git $root_cmd)
    fi
}


# Unified git operations tool
ami-git() {
    # Unified git operations tool with multiple subcommands
    # Usage: ami-git [subcommand] [args...]
    # Subcommands: status, diff, log, commit, push, pull-all, tag-all, delete-tag-all
    if [[ $# -eq 0 ]]; then
        echo -e "${RED}Error: No subcommand provided${NC}"
        echo -e "Usage: ami-git [subcommand] [args...]"
        echo -e "Available subcommands:"
        echo -e "  status [module] [args...]      - Show git status with module auto-detection"
        echo -e "  diff [module] [args...]        - Show git diff with module auto-detection"
        echo -e "  log [module] [args...]         - Show git log with module auto-detection"
        echo -e "  commit [options] [module] [msg] - Safe commit with quality checks"
        echo -e "                                  Options: --fix, --dry-run, --amend"
        echo -e "  push [options] [module] [remote] [branch] - Safe push with tests"
        echo -e "                                  Options: --only-ready"
        echo -e "  pull-all                       - Multi-module git pull operations"
        echo -e "  tag-all <version> [message]    - Tag all modules with same version"
        echo -e "  delete-tag-all <version>       - Delete tag from all modules"
        return 1
    fi

    local cmd="$1"
    shift

    case "$cmd" in
        status)
            # Show git status for a module with automatic module detection
            local module

            if [[ $# -gt 0 && -d "$AMI_ROOT/$1" ]]; then
                module="$1"
                shift
            else
                module="$(_detect_current_module)"
            fi

            if [[ "$module" == "." ]]; then
                echo -e "${BLUE}Git status for:${NC} orchestrator root"
                (cd "$AMI_ROOT" && git status "$@")
            else
                echo -e "${BLUE}Git status for:${NC} $module"
                (cd "$AMI_ROOT/$module" && git status "$@")
            fi
            ;;
        diff)
            # Show git diff for a module with automatic module detection
            local module

            if [[ $# -gt 0 && -d "$AMI_ROOT/$1" ]]; then
                module="$1"
                shift
            else
                module="$(_detect_current_module)"
            fi

            if [[ "$module" == "." ]]; then
                (cd "$AMI_ROOT" && git diff "$@")
            else
                (cd "$AMI_ROOT/$module" && git diff "$@")
            fi
            ;;
        log)
            # Show git log for a module with automatic module detection
            local module

            if [[ $# -gt 0 && -d "$AMI_ROOT/$1" ]]; then
                module="$1"
                shift
            else
                module="$(_detect_current_module)"
            fi

            if [[ "$module" == "." ]]; then
                (cd "$AMI_ROOT" && git log --oneline -10 "$@")
            else
                (cd "$AMI_ROOT/$module" && git log --oneline -10 "$@")
            fi
            ;;
        commit)
            # Safe git commit wrapper that stages all changes and runs quality checks before committing
            # Uses scripts/git_commit.sh with built-in safety checks and auto-fixes
            "$AMI_ROOT/scripts/git_commit.sh" "$@"
            ;;
        push)
            # Safe git push wrapper that runs tests before pushing
            # Uses scripts/git_push.sh with built-in testing and safety checks
            "$AMI_ROOT/scripts/git_push.sh" "$@"
            ;;
        pull-all)
            # Multi-module git pull operations across all modules
            _run_git_operation_for_all "pull" "Git pull for all modules" "pull"
            ;;
        tag-all)
            # Tag all submodules and root with the same version tag
            "$AMI_ROOT/scripts/git_tag_all.sh" "$@"
            ;;
        delete-tag-all)
            # Delete a tag from all submodules and root (both local and remote)
            "$AMI_ROOT/scripts/git_delete_tag_all.sh" "$@"
            ;;
        *)
            echo -e "${RED}Error: Unknown subcommand '$cmd'${NC}"
            echo -e "Usage: ami-git [subcommand] [args...]"
            echo -e "Available subcommands:"
            echo -e "  status [module] [args...]      - Show git status with module auto-detection"
            echo -e "  diff [module] [args...]        - Show git diff with module auto-detection"
            echo -e "  log [module] [args...]         - Show git log with module auto-detection"
            echo -e "  commit [options] [module] [msg] - Safe commit with quality checks"
            echo -e "                                  Options: --fix, --dry-run, --amend"
            echo -e "  push [options] [module] [remote] [branch] - Safe push with tests"
            echo -e "                                  Options: --only-ready"
            echo -e "  pull-all                       - Multi-module git pull operations"
            echo -e "  tag-all <version> [message]    - Tag all modules with same version"
            echo -e "  delete-tag-all <version>       - Delete tag from all modules"
            return 1
            ;;
    esac
}

# ============================================================================
# 11. ENVIRONMENT INFO
# ============================================================================

ami-info() {
    echo -e "${BLUE}AMI Orchestrator Environment${NC}"
    echo -e "${CYAN}Root:${NC} $AMI_ROOT"
    echo -e "${CYAN}Python:${NC} $(which python)"
    echo -e "${CYAN}Podman:${NC} $(which podman 2>/dev/null || echo 'not found')"
    echo -e "${CYAN}UV:${NC} $(which uv 2>/dev/null || echo 'not found')"
    echo -e "${CYAN}Current Module:${NC} $(_detect_current_module)"
    echo -e "${CYAN}PATH:${NC} $PATH"
}

# ============================================================================
# 12. SUMMARY OUTPUT
# ============================================================================

# Display the banner if not in quiet mode
if [[ "$AMI_QUIET_MODE" != "1" ]]; then
    display_banner
fi
