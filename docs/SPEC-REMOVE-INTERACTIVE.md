# SPEC: Remove Interactive Agent Behavior

## Overview

Remove all interactive behavior from AMI-Agent system. Convert from dual interactive/non-interactive to non-interactive only.

## Current Interactive Components to Remove

### 1. Mode Handler Function
- `mode_interactive()` in `scripts/agents/cli/mode_handlers.py`
- All Claude Code subprocess launching logic
- MCP config file creation/deletion
- Settings file creation/deletion

### 2. CLI Arguments
- `--interactive` flag
- `--continue` flag  
- `--resume` flag
- `--fork-session` flag

### 3. Default Behavior
- Current default: launch interactive when no args provided
- New default: show help or error when no args provided

### 4. Related Infrastructure
- Interactive-specific config in `automation.yaml`
- Interactive-related prompts
- MCP server integration for interactive mode

## Implementation Changes

### File: `scripts/agents/cli/main.py`
- Remove interactive argument parsing
- Remove default interactive fallback
- Update mode dispatch to exclude interactive path
- Update help text to reflect non-interactive only

### File: `scripts/agents/cli/mode_handlers.py`
- Delete entire `mode_interactive()` function
- Keep all other mode handlers unchanged (`mode_print`, `mode_hook`, `mode_audit`, `mode_tasks`, `mode_sync`, `mode_docs`)

### File: `scripts/config/automation.yaml`
- Remove interactive-specific config sections
- Update agent defaults to non-interactive presets

### File: `README.md`
- Remove interactive usage examples
- Update agent description to reflect non-interactive only

## Validation

After changes:
- `ami-agent` without args shows help/error
- `ami-agent --print ...` works unchanged
- `ami-agent --hook ...` works unchanged  
- `ami-agent --audit ...` works unchanged
- `ami-agent --tasks ...` works unchanged
- `ami-agent --sync ...` works unchanged
- `ami-agent --docs ...` works unchanged