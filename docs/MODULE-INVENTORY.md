# Modules and Nested Submodules for Hierarchical Shell Architecture

## Root Level Modules
The following directories are root-level modules that contain the necessary module indicators (Makefile, backend/, requirements.txt, or pyproject.toml):

1. `base`
2. `browser`
3. `compliance` 
4. `domains`
5. `files`
6. `nodes`
7. `streams`
8. `ux`

## Nested Submodules
The following nested submodules have been identified that also contain module indicators:

### domains/ submodules:
- `domains/marketing`

### ux/ submodules:
- `ux/cms`

## Complete Module List for setup-shell.sh Creation

### Primary modules (root level):
- `base` - Core infrastructure and utilities
- `browser` - Web automation and browser-based agent interactions
- `compliance` - Security, compliance, and validation tools
- `domains` - Domain-specific business logic and services hub
- `files` - File handling, storage, and data processing
- `nodes` - Node management and orchestration services
- `streams` - Real-time data streaming and processing
- `ux` - User experience and interface components

### Nested submodules:
- `domains/marketing` - Marketing-specific domain logic
- `ux/cms` - Content management system UI components

## Directory Structure Summary

```
AMI-ORCHESTRATOR/
├── base/
├── browser/
├── compliance/
├── domains/
│   ├── marketing/     ← Nested submodule
│   ├── keyring/
│   ├── risk/
│   └── sda/
├── files/
├── nodes/
├── streams/
└── ux/
    ├── cms/          ← Nested submodule
    ├── auth/
    └── research/
```

## Requirements for Each Module's setup-shell.sh

Each module (both primary and nested) needs to have a `setup-shell.sh` script in its `scripts/` subdirectory that:

1. Sources common utilities from base module
2. Defines only module-specific aliases and functions
3. Documents only its own MCP server and key functionality
4. Provides no headers or system information (handled by root only)
5. Follows the standardized format for module capabilities display
6. Sets up any module-specific environment variables or paths
7. Exposes module-specific tools and services

## MCP Server Access Patterns

### Root-level MCP servers (accessed via root script):
- Base MCP server
- Browser MCP server  
- Other root-level module MCP servers

### Module-specific MCP server access (via module scripts):
- `domains/marketing` - Domain-specific services
- `ux/cms` - CMS-related services and tools