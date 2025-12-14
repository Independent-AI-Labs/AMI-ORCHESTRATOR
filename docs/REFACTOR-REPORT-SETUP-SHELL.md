# Audit Report: scripts/setup-shell.sh Refactoring

## Overview
The current `scripts/setup-shell.sh` is a monolithic script that handles all shell environment setup for the AMI Orchestrator. This script needs to be refactored to implement a hierarchical shell architecture where the root script orchestrates submodule setup while only displaying headers and system information.

## Current Issues

### 1. Monolithic Structure
- The script contains all functionality in a single file
- Common components are mixed with root-specific logic
- No clear separation between base utilities and specific implementations

### 2. Violation of Single Responsibility Principle
- Handles installation/uninstallation logic
- Sets up environment variables and paths
- Provides core wrapper functions
- Implements dynamic discovery functions
- Sources banner and color functions
- Provides the OpenAMI header and system information
- Contains module-specific logic that should be in submodule scripts

### 3. Redundant Code Structure
- Multiple functions repeat similar patterns
- Color codes and banner functions are defined at root level
- Helper functions could be shared across modules

## Refactoring Plan

### Phase 1: Extract Common Components to Base Module

#### 1.1 Move Color and Banner Functions
**Current location:** `scripts/ami-banner.sh` (sourced by setup-shell.sh)
**Move to:** `base/scripts/ami-banner.sh`
```bash
# Color definitions to be standardized in base
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[0;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export NC='\033[0m'  # No Color

# Banner functions already exist, standardize them
_ami_echo() { echo -e "$@"; }
display_banner() { # ... existing banner logic }
```

#### 1.2 Create Common Setup Utilities
**Create:** `base/scripts/setup_common.sh`
```bash
# Common functions used by all setup scripts
base_log_info() { echo -e "${BLUE}INFO${NC}: $1"; }
base_log_success() { echo -e "${GREEN}✓${NC} $1"; }
base_log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
base_log_error() { echo -e "${RED}✗${NC} $1"; }

# Common path resolution functions
base_resolve_root() {
    echo "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
}

# Module detection and validation (current _detect_current_module logic)
base_detect_current_module() { # ... implementation }

# Common validation utilities
base_validate_path() { # ... path validation logic }
```

#### 1.3 Extract Helper Functions
**Current helper functions to move to base:**
- `_detect_current_module`
- `_find_module_root`
- `_find_nearest_setup_file`

### Phase 2: Restructure Root Script

#### 2.1 Minimal Root Responsibilities
The refactored root script should only handle:
- Installation/uninstallation logic
- Root environment setup (PATH, PYTHONPATH)
- Header display (once, at root level)
- Recursive submodule discovery and sourcing
- Root-specific functionality

#### 2.2 Recursive Submodule Discovery
**Add to root script:**
```bash
# Function to discover and source submodule setup scripts
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
```

### Phase 3: Create Module-Specific Setup Scripts

#### 3.1 Template Structure for Module Scripts
**Each module needs:** `module/scripts/setup-shell.sh`

```bash
#!/usr/bin/env bash
# Module-specific shell environment setup
# This script should ONLY define module-specific aliases and functions
# NO headers, banners, or system information (handled by root script)

# Source base common components
source "$AMI_ROOT/base/scripts/setup_common.sh"
source "$AMI_ROOT/base/scripts/ami-banner.sh"

# Module-specific environment setup
MODULE_NAME="$(basename "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)")"
MODULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Module-specific PATH additions (if needed)
if [[ -d "$MODULE_ROOT/.venv/bin" ]]; then
    export PATH="$MODULE_ROOT/.venv/bin:$PATH"
fi

# Module-specific aliases and functions (only MCP server access and key tools)
ami-module-mcp() { # ... module-specific MCP server access }
ami-module-specific-tool() { # ... module-specific function }

# Minimal module capability documentation
display_module_capabilities "$MODULE_NAME" "mcp server, key tools"
```

### Phase 4: Specific Refactoring Tasks

#### 4.1 Cleanup Root Script Functions
**Remove from root script:**
- Any module-specific MCP server access functions
- Module-specific tool functions
- All header/banner displays except root-level

**Keep in root script:**
- Installation/uninstallation logic
- Root environment setup (PATH, PYTHONPATH)
- Root-specific wrappers (ami-run, ami-uv, ami-agent, ami-repo)
- Service management functions (ami-services)
- Testing and setup functions (ami-test, ami-setup, ami-install)
- Code quality functions (ami-codecheck)
- Core utility functions (ami-check-storage, ami-gcloud)

#### 4.2 Organize Root Script Functions by Category
**Current categories identified in the script:**
1. Auto-install/uninstall functions (keep in root)
2. Environment detection and setup (keep in root)
3. Helper functions (move to base)
4. Core wrappers (keep in root)
5. CLI tool wrappers (keep in root)
6. Service management (keep in root)
7. Dynamic discovery functions (keep in root)
8. Code quality tools (keep in root)
9. Utility wrappers (keep in root)
10. Git shortcuts (keep in root)
11. Production orchestration (keep in root)

#### 4.3 Add Recursive Loading Logic
**Add after environment setup and before final aliases:**
1. Discover all module directories with setup-shell.sh
2. Source each module's setup script
3. Validate that all modules loaded successfully

## Implementation Steps

### Step 1: Create Base Components
- Create `base/scripts/setup_common.sh`
- Move helper functions to base
- Standardize banner system in base

### Step 2: Create Module Scripts
- Create template setup scripts for each module
- Move module-specific functionality to respective modules
- Ensure modules source base components

### Step 3: Refactor Root Script
- Remove module-specific logic
- Add recursive discovery and loading logic
- Keep only root-specific functionality

### Step 4: Testing
- Verify all aliases still work
- Test recursive loading
- Validate quiet mode operation
- Ensure installation/uninstallation still works

## Benefits of Refactoring

1. **Modularity**: Each module manages its own shell interface
2. **Maintainability**: Common functionality centralized in base
3. **Scalability**: Easy to add new modules
4. **Separation of Concerns**: Clear boundaries between root and module responsibilities
5. **Consistency**: Standardized approach across all modules

## Timeline
- Phase 1: 1 day (Extract common components)
- Phase 2: 2 days (Restructure root script)
- Phase 3: 3 days (Create module scripts)
- Phase 4: 1 day (Testing and validation)

Total: 7 days to complete the refactoring while maintaining backward compatibility.

## Risk Mitigation
- Maintain all existing function names and interfaces
- Keep installation/uninstallation logic unchanged
- Preserve all current environment setup behavior
- Test thoroughly in a staging environment before production deployment