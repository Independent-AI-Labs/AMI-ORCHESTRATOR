# Specification: Hierarchical Shell Tools System

## Overview

This specification describes an enhanced hierarchical shell setup system for the AMI Orchestrator that improves the existing `scripts/setup-shell.sh` by implementing a recursive discovery and sourcing mechanism for submodule setup scripts.

## Current Architecture

The current system has a single root `scripts/setup-shell.sh` that:
- Sets up environment variables (PATH, PYTHONPATH)
- Provides core wrapper functions (ami-run, ami-uv, ami-agent, etc.)
- Implements dynamic discovery functions
- Sources banner and color functions
- Provides the OpenAMI header and system information

## Proposed Enhancement: Hierarchical Shell Architecture

### 1. Centralized Common Components in Base

All common printing, documentation, alias and CLI-general logic from the root shell script should be moved to the `base/` module:

#### Components to Move to Base:
- Color definitions and banner functions (`scripts/ami-banner.sh`)
- Common utility functions
- Standard error/success formatting
- Base setup helper functions
- Common aliases and printing utilities
- Module detection functions
- Environment validation utilities

#### Base Module Components:
- `base/scripts/setup_common.sh` - Common shell functions and utilities
- `base/scripts/ami-banner.sh` - Standardized banner and color definitions
- `base/scripts/setup_helpers.sh` - Common helper functions for all setup scripts

### 2. Module-Specific Setup Scripts

Each module will have its own `setup-shell.sh` script that:
- Sources common components from base module
- Defines module-specific aliases and functions
- Documents only its own capabilities in minimal form
- Exposes only its own MCP servers and key functionality

#### Module Setup Scripts Structure:
- `base/scripts/setup-shell.sh` - Core infrastructure and utilities
- `browser/scripts/setup-shell.sh` - Web automation and browser-based agent interactions
- `compliance/scripts/setup-shell.sh` - Security, compliance, and validation tools
- `domains/scripts/setup-shell.sh` - Domain-specific business logic and services hub
- `files/scripts/setup-shell.sh` - File handling, storage, and data processing
- `nodes/scripts/setup-shell.sh` - Node management and orchestration services
- `streams/scripts/setup-shell.sh` - Real-time data streaming and processing
- `ux/scripts/setup-shell.sh` - User experience and interface components

#### Nested Submodule Setup Scripts:
- `domains/marketing/scripts/setup-shell.sh` - Marketing-specific domain logic
- `ux/cms/scripts/setup-shell.sh` - Content management system UI components

#### Recursive Discovery Support:
The system supports nested modules at any depth. For example, if `domains/marketing` contained further submodules, they would also be discovered and loaded following the same pattern. The system will recursively search for `*/scripts/setup-shell.sh` files in all subdirectories.

### Module Identification Criteria

The system identifies modules based on the presence of the following indicators in a directory:
- `Makefile` - Standard build and setup instructions
- `backend/` directory - Contains backend code structure
- `requirements.txt` - Python dependency specifications
- `pyproject.toml` - Python project configuration

#### Complete Module Inventory

The system currently contains the following modules that require `setup-shell.sh` scripts:

**Primary Modules (Root Level):**
- `base` - Core infrastructure and utilities
- `browser` - Web automation and browser-based agent interactions
- `compliance` - Security, compliance, and validation tools
- `domains` - Domain-specific business logic and services hub
- `files` - File handling, storage, and data processing
- `nodes` - Node management and orchestration services
- `streams` - Real-time data streaming and processing
- `ux` - User experience and interface components

**Nested Submodules:**
- `domains/marketing` - Marketing-specific domain logic
- `ux/cms` - Content management system UI components

**Module Identification Command:**
```bash
# To identify all modules and submodules in the project
find /path/to/project -mindepth 1 -maxdepth 3 -type d \( -name "Makefile" -o -path "*/backend" -o -name "requirements.txt" -o -name "pyproject.toml" \) -exec dirname {} \; | sort -u
```

This command finds all directories that contain module indicators and can be adapted to discover new modules added to the system.

### 3. Enhanced Root Orchestrator Setup

The root `scripts/setup-shell.sh` will be redesigned to:

#### Responsibilities:
1. Handle only root-level initialization and header display
2. Recursively discover and source submodule setup scripts
3. Maintain its own MCP server exposure
4. Provide unified interface to all modules

#### Recursive Discovery Algorithm:
```bash
discover_and_source_submodules() {
    local root_dir="${1:-$AMI_ROOT}"
    local search_pattern="${2:-"*/scripts/setup-shell.sh"}"
    local modules_processed=0

    # Find and source all setup-shell.sh scripts at any depth
    while IFS= read -r -d '' setup_script; do
        if [[ -f "$setup_script" && -r "$setup_script" ]]; then
            # Get directory containing the script to determine module name
            local module_dir=$(dirname "$(dirname "$setup_script")")
            local module_name="${module_dir#$AMI_ROOT/}"

            if [[ "$AMI_QUIET_MODE" != "1" ]]; then
                echo -e "${CYAN}→${NC} Loading $module_name..."
            fi
            source "$setup_script"
            ((modules_processed++))
        fi
    done < <(find "$root_dir" -name "setup-shell.sh" -path "*/scripts/setup-shell.sh" -print0)

    if [[ "$AMI_QUIET_MODE" != "1" ]]; then
        echo -e "${GREEN}✓${NC} Loaded $modules_processed submodule environments"
    fi
}
```

### 4. Header and Output Constraints

#### Root Script Responsibilities Only:
- Display OpenAMI header and system information
- Show main orchestrator banner
- Provide overall system status
- Handle installation/uninstallation logic

#### Submodule Scripts Constraints:
- NO headers or banners (only minimal output)
- NO system-wide information display
- Only module-specific aliases and functions
- Minimal documentation in standardized format

## Detailed Implementation

### Base Module Components

#### `base/scripts/setup_common.sh`
```bash
# Common functions used by all setup scripts

# Standardized logging functions
base_log_info() { echo -e "${BLUE}INFO${NC}: $1"; }
base_log_success() { echo -e "${GREEN}✓${NC} $1"; }
base_log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
base_log_error() { echo -e "${RED}✗${NC} $1"; }

# Common path resolution functions
base_resolve_root() {
    echo "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
}

# Module detection and validation
base_detect_current_module() {
    local current="$PWD"
    local root="$1"
    
    while [[ "$current" != "/" && "$current" != "$root" ]]; do
        local rel_path="${current#$root/}"
        if [[ "$rel_path" != "$current" && "$rel_path" != */* ]]; then
            echo "$rel_path"
            return 0
        fi
        current="$(dirname "$current")"
    done
    echo "."
}
```

#### `base/scripts/ami-banner.sh` (Enhanced)
```bash
# Enhanced banner system with standardized colors and functions

# Color definitions
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[0;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export NC='\033[0m' # No Color

# Standardized banner functions
display_header() {
    if [[ "${AMI_QUIET_MODE:-0}" != "1" ]]; then
        _ami_echo "${BLUE}🚀 OpenAMI Orchestrator${NC}"
        _ami_echo "${CYAN}Modular AI Agent Development Platform${NC}"
    fi
}

display_module_capabilities() {
    local module_name="$1"
    local capabilities="$2"
    if [[ "${AMI_QUIET_MODE:-0}" != "1" ]]; then
        echo -e "${CYAN}$module_name Capabilities:${NC} $capabilities"
    fi
}
```

### Root Orchestrator Script Enhancement

#### Enhanced `scripts/setup-shell.sh`
```bash
#!/usr/bin/env bash
# Enhanced AMI Orchestrator Shell Environment Setup
# This script now serves as the central orchestrator that recursively
# sources all submodule setup scripts while maintaining the header display.

# [Initial setup and flag handling remains similar but streamlined]

# ============================================================================
# 1. LOAD BASE COMPONENTS AND SETUP ROOT ENVIRONMENT
# ============================================================================

# Source base common components
source "$AMI_ROOT/base/scripts/setup_common.sh"
source "$AMI_ROOT/base/scripts/ami-banner.sh"

# Setup root-specific environment
# [PATH, PYTHONPATH configuration remains]

# ============================================================================
# 2. DISPLAY HEADER AND SYSTEM INFORMATION (ROOT ONLY)
# ============================================================================

# Display unified header (only at root level)
if [[ "$AMI_QUIET_MODE" != "1" ]]; then
    display_header
    _ami_echo "${BLUE}🚀 Setting up AMI Orchestrator shell environment...${NC}"
fi

# ============================================================================
# 3. RECURSIVE SUBMODULE DISCOVERY AND SOURCING
# ============================================================================

discover_and_source_submodules() {
    local root_dir="${1:-$AMI_ROOT}"
    local modules_processed=0
    
    if [[ "$AMI_QUIET_MODE" != "1" ]]; then
        echo -e "${BLUE}Loading submodule environments:${NC}"
    fi
    
    # Process each submodule directory
    for module_dir in "$root_dir"/*/; do
        if [[ -d "$module_dir" ]]; then
            local module_name="$(basename "$module_dir")"
            local setup_script="$module_dir/scripts/setup-shell.sh"
            
            # Check if this is a valid module with setup script
            if [[ -f "$setup_script" && -r "$setup_script" ]]; then
                if [[ "$AMI_QUIET_MODE" != "1" ]]; then
                    echo -e "${CYAN}→${NC} Loading $module_name..."
                fi
                source "$setup_script"
                ((modules_processed++))
            fi
        fi
    done
    
    if [[ "$AMI_QUIET_MODE" != "1" ]]; then
        echo -e "${GREEN}✓${NC} Loaded $modules_processed submodule environments"
    fi
}

# Execute recursive loading
discover_and_source_submodules "$AMI_ROOT"

# ============================================================================
# 4. ROOT-ONLY CAPABILITIES
# ============================================================================

# Define root-specific functions that coordinate across modules
ami-status() {
    echo -e "${BLUE}AMI Orchestrator Status:${NC}"
    echo "- Core Wrappers: ami-run, ami-uv, ami-agent, ami-repo"
    echo "- Service Management: ami-services, ami-start, etc."
    echo "- Testing: ami-test with auto-discovery"
    echo "- Setup: ami-install, ami-setup with auto-detection" 
    echo "- Code Quality: ami-codecheck for pre-commit hooks"
    echo "- Git Operations: ami-git with multi-module support"
    echo "- Utilities: ami-check-storage, ami-gcloud, ami-info"
}

# [Rest of root-specific functions remain]
```

### Submodule Setup Script Template

#### Template for `module/scripts/setup-shell.sh`
```bash
#!/usr/bin/env bash
# Module-specific shell environment setup
# This script should ONLY define module-specific aliases and functions
# NO headers, banners, or system information (handled by root script)

# ============================================================================
# PREREQUISITES
# ============================================================================

# Ensure base components are available
if [[ -z "${AMI_ROOT:-}" ]]; then
    echo "Error: This script should be sourced from the root setup-shell.sh"
    return 1
fi

# Source base common components
source "$AMI_ROOT/base/scripts/setup_common.sh"

# ============================================================================
# MODULE-SPECIFIC SETUP
# ============================================================================

# Set module-specific variables
MODULE_NAME="$(basename "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)")"
MODULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Module-specific PATH additions (if needed)
if [[ -d "$MODULE_ROOT/.venv/bin" ]]; then
    export PATH="$MODULE_ROOT/.venv/bin:$PATH"
fi

# ============================================================================
# MODULE-SPECIFIC ALIASES AND FUNCTIONS
# ============================================================================

# Provide access to module-specific MCP server
ami-module-mcp() {
    # Launch module-specific MCP server
    "$AMI_ROOT/scripts/ami-run" "$MODULE_ROOT/scripts/run_mcp_server.py" "$@"
}

# Module-specific convenience functions
# (Only functions that make sense at shell level, not internal utilities)

# ============================================================================
# CAPABILITY DOCUMENTATION
# ============================================================================

# Register module capabilities for root script visibility
if [[ -n "${AMI_ROOT:-}" ]]; then
    display_module_capabilities "$MODULE_NAME" "$(get_module_capabilities)"
fi

get_module_capabilities() {
    # Return a concise string describing the main capabilities
    # This should come from a consistent source like a config file
    case "$MODULE_NAME" in
        "files")
            echo "filesystem tools, git workflows, document processing, Python runner"
            ;;
        "browser") 
            echo "web automation, browser control, navigation tools"
            ;;
        "compliance")
            echo "security checks, compliance validation, audit tools"
            ;;
        *)
            echo "custom module capabilities"
            ;;
    esac
}

# [Module-specific aliases like ami-module-name, etc.]
```

## Implementation Plan

### Phase 1: Base Component Extraction
1. Move common functions to `base/scripts/setup_common.sh`
2. Enhance `base/scripts/ami-banner.sh`
3. Create standardized utility functions

### Phase 2: Submodule Script Development
1. Create setup script template
2. Implement for each existing module
3. Ensure minimal output requirements

### Phase 3: Root Script Enhancement
1. Implement recursive discovery function
2. Refactor root script to delegate to submodules
3. Maintain backward compatibility

### Phase 4: Testing
1. Verify all functionality still works
2. Test nested module discovery
3. Validate quiet mode operation
4. Ensure installation/uninstallation still works

## Benefits

1. **Modularity**: Each module manages its own shell interface
2. **Scalability**: Easy to add new modules with their own capabilities
3. **Maintainability**: Common functionality centralized in base module
4. **Consistency**: Standardized approach across all modules
5. **Performance**: Only load what's needed per module

## Backward Compatibility

- All existing aliases and functions will continue to work
- The root script maintains the same interface
- Installation/uninstallation processes remain the same
- No changes to existing workflows or CI/CD pipelines