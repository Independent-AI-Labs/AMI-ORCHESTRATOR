# Dependency Addition Process: Development Workflow

This document outlines the steps to safely add a dependency to the AMI Orchestrator system.

## Key Principle: No Cheating
You must properly add dependencies with correct versions. No taking shortcuts, bypassing quality checks, or skipping required steps.
- Always use concrete versions (package==x.y.z) for security and reproducibility
- Never bypass quality checks - Always resolve issues properly
- Verify dependencies are actively maintained and secure
- Address root causes, not symptoms

## Phase 1: Research & Identification

1. **Search for Latest Release**:
   - Search online for the latest pip / node / maven / etc. release for the required package
   - Ensure compatibility with existing dependencies and project requirements
   - Verify security and maintenance status of the package

2. **Determine Installation Target**:
   - Identify the appropriate project level: base, specific module, or root pyproject.toml
   - Consider scope: whether dependency is needed globally or for specific modules only

## Phase 2: Dependency Addition

1. **Update Configuration File**:
   - Add dependency to appropriate pyproject.toml file USING A CONCRETE VERSION
   - Use specific version numbers (e.g., package==1.2.3) rather than loose constraints
   - Verify version compatibility with existing dependencies

2. **Document Changes**:
   - Add comment explaining why the dependency is needed
   - Note any specific version requirements or compatibility concerns

## Phase 3: System Synchronization

1. **Execute Sync Process**:
   - CRITICAL: Each module has its own dependencies and virtual environment (venv)
   - Navigate to the appropriate directory:
     - For root dependencies: `cd /home/ami/Projects/AMI-ORCHESTRATOR`
     - For submodule-specific dependencies: `cd /path/to/submodule` (e.g., `cd learning`)
     - Each module maintains its own .venv directory and dependency set
   - Run synchronization script: `scripts/ami-uv sync`
   - CRITICAL NOTE for submodule execution: When calling from a submodule directory (e.g., from within a specific module folder), you can call the sync script using the relative path like: `../(as many directories up as needed)/scripts/ami-uv sync`
   - Verify the dependency has been properly installed and integrated

2. **Handle Installation Failures**:
   - If sync fails, check for version conflicts or compatibility issues
   - Adjust version specifications as needed while maintaining security requirements
   - Retry sync after resolving conflicts

## Quality Assurance Rules
1. Always use concrete versions (package==x.y.z) for security and reproducibility
2. Verify dependencies are actively maintained and secure
3. Check for compatibility with existing dependency ecosystem
4. Document the rationale for adding each dependency
5. Test thoroughly after adding any new dependencies
6. Remove unused dependencies to maintain minimal footprint
7. Follow existing versioning conventions in the project