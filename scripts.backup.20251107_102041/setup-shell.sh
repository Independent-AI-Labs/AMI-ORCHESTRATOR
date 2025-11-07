#!/usr/bin/env bash
# AMI Orchestrator Production Shell Setup
# Source this file to configure your shell environment
# Usage: source scripts/setup-shell.sh  OR  . scripts/setup-shell.sh
#
# To install permanently in your shell:
#   scripts/setup-shell.sh --install
#   scripts/setup-shell.sh --install --no-backup  # skip backup
#
# To uninstall:
#   scripts/setup-shell.sh --uninstall

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

# Handle --install/--uninstall flags
if [[ "${1:-}" == "--install" ]]; then
    # Get AMI_ROOT early for install
    AMI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    export AMI_ROOT

    # Colors for output
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    YELLOW='\033[1;33m'
    NC='\033[0m'

    backup="true"
    [[ "${2:-}" == "--no-backup" ]] && backup="false"
    _install_to_bashrc "$backup"
    exit 0
elif [[ "${1:-}" == "--uninstall" ]]; then
    # Colors for output
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'

    _uninstall_from_bashrc
    exit 0
fi

# ============================================================================
# 1. ENVIRONMENT DETECTION & SETUP
# ============================================================================

# Get the root directory (parent of scripts/)
AMI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AMI_ROOT

# Colors for output
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Setting up AMI Orchestrator shell environment...${NC}"

# ============================================================================
# 2. PATH AND PYTHONPATH CONFIGURATION
# ============================================================================

# Add root .venv/bin to PATH (prepend so it takes precedence)
if [[ -d "$AMI_ROOT/.venv/bin" ]]; then
    export PATH="$AMI_ROOT/.venv/bin:$PATH"
    echo -e "${GREEN}✓${NC} Added root .venv/bin to PATH"
else
    echo -e "${YELLOW}⚠${NC} Warning: root .venv/bin not found."
fi

# Add base module .venv/bin to PATH
if [[ -d "$AMI_ROOT/base/.venv/bin" ]]; then
    export PATH="$AMI_ROOT/base/.venv/bin:$PATH"
    echo -e "${GREEN}✓${NC} Added base/.venv/bin to PATH"
    echo -e "  ${CYAN}→${NC} Access to: python, pytest, podman, claude, fastmcp, uvicorn, ruff, mypy, etc."
fi

# Set PYTHONPATH to include all modules
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
    # Returns path to module_setup.py or AMI_ROOT/module_setup.py as default
    local current="$PWD"

    while [[ "$current" != "/" ]]; do
        if [[ -f "$current/module_setup.py" ]]; then
            echo "$current/module_setup.py"
            return 0
        fi
        current="$(dirname "$current")"
    done

    # Default to root
    echo "$AMI_ROOT/module_setup.py"
}

# ============================================================================
# 4. CORE WRAPPERS (Root-only execution)
# ============================================================================

ami-run() {
    "$AMI_ROOT/scripts/ami-run.sh" "$@"
}

ami-uv() {
    "$AMI_ROOT/scripts/ami-uv" "$@"
}

ami-agent() {
    "$AMI_ROOT/scripts/ami-agent" "$@"
}

ami-repo() {
    "$AMI_ROOT/scripts/ami-repo" "$@"
}

# ============================================================================
# 5. SERVICE MANAGEMENT (Root-only execution)
# ============================================================================

ami-service() {
    ami-run nodes/scripts/setup_service.py "$@"
}

ami-start() {
    echo -e "${BLUE}Starting process/profile:${NC} $*"
    ami-service start "$@"
}

ami-stop() {
    echo -e "${YELLOW}Stopping process/profile:${NC} $*"
    ami-service stop "$@"
}

ami-restart() {
    echo -e "${YELLOW}Restarting process/profile:${NC} $*"
    ami-service restart "$@"
}

ami-profile() {
    echo -e "${BLUE}Managing profile:${NC} $*"
    ami-service profile "$@"
}

# ============================================================================
# 6. DYNAMIC DISCOVERY FUNCTIONS
# ============================================================================

ami-test() {
    # Takes optional module path as parameter
    # If not provided, auto-detects from PWD
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
        ami-run "$module_root/scripts/run_tests.py" "$@"
    fi
}

ami-install() {
    # Takes optional module path as parameter
    # If not provided, finds nearest module_setup.py
    if [[ $# -gt 0 && -f "$AMI_ROOT/$1/module_setup.py" ]]; then
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

ami-setup() {
    ami-install "$@"
}

# ============================================================================
# 7. CODE QUALITY TOOLS (Root-only execution)
# ============================================================================

ami-codecheck() {
    # Runs pre-commit hooks
    # No args: run all hooks
    # With args: run specific hooks by ID
    # Examples:
    #   ami-codecheck              → run all hooks
    #   ami-codecheck ruff         → run only ruff hook
    #   ami-codecheck mypy         → run only mypy hook
    #   ami-codecheck ruff mypy    → run ruff and mypy hooks

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

ami-check-storage() {
    echo -e "${BLUE}Checking storage backends...${NC}"
    ami-run base/scripts/check_storage.py "$@"
}

ami-propagate-tests() {
    echo -e "${BLUE}Propagating test runner to modules...${NC}"
    ami-run base/scripts/propagate_test_runner.py
}

# ============================================================================
# 9. NAVIGATION ALIASES
# ============================================================================

# Module navigation
alias ami-root="cd $AMI_ROOT"
alias ami-base="cd $AMI_ROOT/base"
alias ami-browser="cd $AMI_ROOT/browser"
alias ami-compliance="cd $AMI_ROOT/compliance"
alias ami-domains="cd $AMI_ROOT/domains"
alias ami-files="cd $AMI_ROOT/files"
alias ami-nodes="cd $AMI_ROOT/nodes"
alias ami-streams="cd $AMI_ROOT/streams"
alias ami-ux="cd $AMI_ROOT/ux"

# Directory navigation
alias ami-tests="cd $AMI_ROOT/base/tests"
alias ami-backend="cd $AMI_ROOT/base/backend"
alias ami-scripts="cd $AMI_ROOT/scripts"
alias ami-docs="cd $AMI_ROOT/docs"

# ============================================================================
# 10. GIT SHORTCUTS (Take module path as parameter)
# ============================================================================

ami-status() {
    # ami-status [module] [git-args]
    # If module provided, use it; otherwise auto-detect
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
}

ami-diff() {
    # ami-diff [module] [git-args]
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
}

ami-log() {
    # ami-log [module] [git-args]
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
}

# Multi-module operations
ami-status-all() {
    echo -e "${BLUE}Git status for all modules:${NC}"
    for module_dir in "$AMI_ROOT"/*; do
        if [[ -d "$module_dir/.git" ]]; then
            local module="$(basename "$module_dir")"
            echo -e "\n${YELLOW}=== $module ===${NC}"
            (cd "$module_dir" && git status -s)
        fi
    done

    # Also check root
    if [[ -d "$AMI_ROOT/.git" ]]; then
        echo -e "\n${YELLOW}=== orchestrator (root) ===${NC}"
        (cd "$AMI_ROOT" && git status -s)
    fi
}

ami-pull-all() {
    echo -e "${BLUE}Git pull for all modules:${NC}"
    for module_dir in "$AMI_ROOT"/*; do
        if [[ -d "$module_dir/.git" ]]; then
            local module="$(basename "$module_dir")"
            echo -e "\n${YELLOW}=== $module ===${NC}"
            (cd "$module_dir" && git pull)
        fi
    done

    # Also check root
    if [[ -d "$AMI_ROOT/.git" ]]; then
        echo -e "\n${YELLOW}=== orchestrator (root) ===${NC}"
        (cd "$AMI_ROOT" && git pull)
    fi
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

echo -e "\n${GREEN}✓${NC} Created production aliases:"
echo -e "\n${RED}🔴 Root-only (must run from $AMI_ROOT):${NC}"
echo -e "  ami-run, ami-uv, ami-agent, ami-repo"
echo -e "  ami-service, ami-codecheck"
echo -e "  ami-start, ami-stop, ami-restart, ami-profile"
echo -e "  ami-status-all, ami-pull-all"

echo -e "\n${PURPLE}🟣 Dynamic/Optional parameter:${NC}"
echo -e "  ami-test [module] [args]     → Run tests (auto-detects if no module)"
echo -e "  ami-install [module] [args]  → Run module_setup.py (auto-detects if no module)"
echo -e "  ami-setup [module] [args]    → Alias for ami-install"
echo -e "  ami-status [module] [args]   → Git status (auto-detects if no module)"
echo -e "  ami-diff [module] [args]     → Git diff (auto-detects if no module)"
echo -e "  ami-log [module] [args]      → Git log (auto-detects if no module)"

echo -e "\n${YELLOW}🟡 Navigation (work anywhere):${NC}"
echo -e "  ami-root, ami-base, ami-browser, ami-compliance, ami-domains"
echo -e "  ami-files, ami-nodes, ami-streams, ami-ux"
echo -e "  ami-tests, ami-backend, ami-scripts, ami-docs"

echo -e "\n${CYAN}🔵 Utilities:${NC}"
echo -e "  ami-check-storage, ami-propagate-tests, ami-info"

echo -e "\n${BLUE}💡 Available pre-commit hook IDs for ami-codecheck:${NC}"
echo -e "  ruff, ruff-format, mypy, validate-docs-links, check-yaml,"
echo -e "  check-added-large-files, check-merge-conflict, debug-statements"

echo -e "\n${GREEN}✨ Shell environment ready!${NC}"
echo -e "Type ${YELLOW}ami-info${NC} to see environment details"
echo -e "Type ${YELLOW}ami-codecheck${NC} to run all code quality checks"
echo -e "Type ${YELLOW}ami-start dev${NC} to start the development profile"
