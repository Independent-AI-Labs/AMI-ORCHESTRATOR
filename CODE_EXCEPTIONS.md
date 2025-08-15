# CODE EXCEPTIONS - ROOT ORCHESTRATOR MODULE

This file documents legitimate code patterns and architectural decisions for the root orchestrator.

## 1. Submodule Architecture

### Submodule Integration
**Modules:**
- `base` - Core worker pool and MCP infrastructure
- `browser` - Web automation and browser management
- `files` - File system operations and git integration
- `ux` - User interface components
- `compliance` - Compliance tracking (placeholder)
- `domains` - Domain-specific logic (placeholder)
- `streams` - Streaming capabilities (placeholder)

**Justification:**
Each submodule is independently versioned and tested, allowing for modular development and deployment. The orchestrator coordinates these modules without duplicating their functionality.

## 2. Test Architecture

### No Root-Level Tests
**Location:** `scripts/run_tests.py`

**Justification:**
All functionality is implemented in submodules which have comprehensive test suites. The root orchestrator merely coordinates these modules. Testing is performed at the submodule level where the actual logic resides.

## 3. Module Status

### Active Modules (Updated):
- ✅ **BASE** - All exceptions fixed, CODE_EXCEPTIONS.md created, 22 tests passing
- ✅ **BROWSER** - User agents extracted to config, CODE_EXCEPTIONS.md created, 38 unit tests passing
- ✅ **FILES** - All broad exceptions fixed, CODE_EXCEPTIONS.md created, 62 tests passing
- ✅ **UX** - Polling fixed with events, CODE_EXCEPTIONS.md created, build successful

### Placeholder Modules:
- **compliance** - Requirements defined, implementation pending
- **domains** - Requirements defined, implementation pending
- **streams** - Requirements defined, implementation pending

## Summary

The root orchestrator follows a clean architecture pattern where:
1. Each submodule is self-contained with its own tests and documentation
2. The orchestrator provides coordination without duplicating logic
3. All critical issues have been resolved in active modules
4. CODE_EXCEPTIONS.md files document legitimate patterns in each module