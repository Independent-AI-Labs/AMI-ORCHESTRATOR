# AMI-ORCHESTRATOR Architecture Restructure Plan

## Current Issues Identified

### 1. Stupid Directory Structure: `/launcher/backend/launcher/`

The current nested structure is redundant and confusing:
- `/launcher/` (was originally "nodes")
- `/launcher/backend/`
- `/launcher/backend/launcher/` ← This is redundant!

This creates paths like: `/launcher/backend/launcher/adapters/base.py` which is confusing.

### 2. Leaked Service Management Logic

The following service/deploymnet management logic exists outside the launcher where it should be centralized:

- `scripts/ami-service-discovery` - Should be part of launcher service discovery
- `scripts/` contains execution utilities (`ami-run`) that should be integrated with launcher
- Some service run scripts in `base/scripts/` that should be managed by launcher

## Proposed Restructure

### New Directory Structure:

```
ami-orchestrator/                 # Root project directory
├── launcher/                     # Service orchestration module (was "nodes")
│   ├── backend/
│   │   ├── adapters/            # Service adapters (python, node, docker-compose, etc.)
│   │   │   ├── base.py
│   │   │   ├── python.py
│   │   │   ├── node.py
│   │   │   ├── docker_compose.py
│   │   │   └── docker_run.py
│   │   ├── supervisor.py        # Core orchestration supervisor
│   │   ├── health.py            # Health monitoring
│   │   ├── state.py             # State management
│   │   └── config.py            # Configuration models
│   ├── mcp/                     # MCP server interface
│   ├── scripts/                 # Launcher CLI tools
│   │   └── launch_services.py   # Main launcher CLI
│   └── production/              # Production deployment tools
├── scripts/                     # General orchestration scripts (moved from launcher)
│   ├── ami-run
│   ├── ami-service-discovery
│   └── other utility scripts
└── base/                        # Core infrastructure (unchanged)
    └── backend/
        └── workers/             # Worker pools (used by launcher)
```

### Renaming Plan:

1. **Rename the project**: The "nodes" project was renamed to "launcher" but this wasn't fully completed
   - Update all documentation references from "nodes" to "launcher"
   - Update README.md to reflect current purpose

2. **Eliminate the nested structure**: 
   - Move `/launcher/backend/launcher/*` to `/launcher/backend/*`
   - Update imports and references accordingly

3. **Consolidate service logic**:
   - Move `scripts/ami-service-discovery` functionality into launcher module
   - Keep `scripts/ami-run` as the general execution wrapper
   - Integrate launcher commands with ami-run for unified execution

### Implementation Steps:

#### Phase 1: Directory Restructure
1. Rename `/launcher/backend/launcher/` → `/launcher/backend/services/` (or similar appropriate name)
2. Update all import paths in Python code
3. Update documentation references
4. Update configuration files that reference paths

#### Phase 2: Logic Consolidation
1. Move service discovery logic into launcher module
2. Enhance launcher to handle ami-service-discovery functionality
3. Update Makefiles and build scripts

#### Phase 3: Integration
1. Ensure `ami-run` can properly invoke launcher services
2. Update all references in docker-compose files
3. Test all functionality after restructure

## Benefits of the New Structure:

1. **Clearer Architecture**: No more confusing nested launcher directories
2. **Better Organization**: Service logic centralized in launcher module
3. **Maintainability**: Easier to understand and modify service orchestration
4. **Consistency**: Follows same patterns as other modules (base, files, browser, etc.)

## Migration Considerations:

- Update all CI/CD pipelines that reference the old paths
- Update documentation across the codebase
- Update any external tools or scripts that depend on the old structure
- Plan for backward compatibility during transition