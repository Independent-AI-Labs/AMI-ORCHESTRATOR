# Architecture Violation Analysis & Corrective Actions

## Issues Identified

### 1. Base Module Contains Infrastructure Services (VIOLATION OF HIERARCHY PRINCIPLES)

The base module is intended to be a core data operations library with common utilities.
However, it's currently housing infrastructure services that break architectural boundaries:

#### A. SSH Infrastructure in Base (Should be in Launcher)
- `/base/backend/mcp/ssh/ssh_server.py` - SSH MCP server
- `/base/scripts/run_ssh_fastmcp.py` - SSH server runner  
- `/base/backend/mcp/ssh/tools/` - SSH operation tools (ssh_execute, ssh_transfer, etc.)
- SSH test server infrastructure in `/base/tests/conftest.py`

#### B. Git Infrastructure in Base (Should be in Launcher)  
- `/base/backend/workers/git_command.py` - Git command execution worker
- Git-related subprocess management logic

#### C. Service Orchestration in Base (Should be in Launcher)
- `/base/scripts/run_mcp.py` - Unified MCP server dispatcher
- Infrastructure service run scripts

### 2. Violation of Isolation Principles

The current architecture violates the intended hierarchy:
- `base/` → Core data operations, models, utilities (should have NO infrastructure dependencies)
- `launcher/` → Service orchestration, process management, infrastructure services
- `browser/`, `files/`, etc. → Domain-specific modules using base + launcher services

Instead, base has infrastructure concerns baked in.

### 3. The "Stupid" Directory Structure
- `/launcher/backend/launcher/` creates redundant nesting
- Should be `/launcher/backend/services/` or similar

## Suggested Corrective Actions

### Phase 1: Directory Restructure
1. **Rename nested launcher structure**
   - Move `/launcher/backend/launcher/*` → `/launcher/backend/services/*`
   - Update all imports accordingly

### Phase 2: Extract Infrastructure from Base
1. **Move SSH infrastructure from base → launcher**
   - Move `/base/backend/mcp/ssh/` → `/launcher/backend/mcp/ssh/`
   - Move `/base/scripts/run_ssh_fastmcp.py` → `/launcher/scripts/run_ssh_fastmcp.py`
   - Update imports and references

2. **Move Git infrastructure from base → launcher**  
   - Move `/base/backend/workers/git_command.py` → `/launcher/backend/workers/git_command.py`
   - Update imports and references

3. **Move service orchestration from base → launcher**
   - Move `/base/scripts/run_mcp.py` → Create a new orchestration system in launcher
   - Update the dispatcher to work with launcher infrastructure

### Phase 3: Clean Base Module
1. **Remove all infrastructure concerns from base**
   - Base should only contain: data operations, models, storage, core utilities
   - No SSH, Git, or service orchestration code
   - No server/demon infrastructure

2. **Update dependencies**
   - Base should have no launcher dependencies
   - Launcher can depend on base for data operations

### Phase 4: Update Integration Points
1. **Update test infrastructure**
   - Move SSH test server logic to launcher tests or create separate infrastructure tests
   - Ensure tests still work after refactoring

2. **Update configuration**
   - Update docker-compose files and setup configurations to use new paths
   - Update MCP client integration tests to use relocated services

## Benefits of This Structure

1. **Clear separation of concerns**: Base focuses on data ops, launcher handles infrastructure
2. **Better maintainability**: Infrastructure services centralized in launcher
3. **Proper dependency flow**: Base has no infrastructure dependencies
4. **Easier testing**: Infrastructure tests separated from core logic
5. **Scalability**: Can add more infrastructure services to launcher without polluting base

## Migration Strategy

1. **Create copies first**: Copy files to new locations while keeping old ones temporarily
2. **Update imports**: Fix all import paths to use new locations
3. **Test thoroughly**: Ensure all functionality still works
4. **Remove old files**: Clean up after verification
5. **Update documentation**: Reflect new architecture in docs

## Priority Actions

1. **Immediate**: Fix the nested directory structure in launcher
2. **High**: Move SSH infrastructure out of base
3. **Medium**: Move Git infrastructure out of base  
4. **Low**: Gradually refactor the unified MCP runner