# SPEC: Environment Setup Consolidation

## Problem Statement

Environment setup code is scattered across **FIVE** locations with massive duplication:

### 1. EnvironmentSetup CLASS (base/backend/utils/environment_setup.py) - 453 lines
- All `@staticmethod`, ZERO state (should be functions)
- Generates configs during test runs (lines 160-168)
- Mixes venv ops with config generation

### 2. Root module_setup.py - 485 lines
- `replicate_configs_from_base()` - generates mypy.ini and .pre-commit-config.yaml
- `check_uv()` - uv installation
- `ensure_git_submodules()` - git submodule init
- Delegates to base/module_setup.py but ALSO has its own setup logic

### 3. Each module's module_setup.py (base/, browser/, nodes/, etc.)
- Each module has its own setup script
- Some delegate to EnvironmentSetup
- Some have custom logic
- NO consistency

### 4. propagate_configs.py - 455 lines
- Config template generation from base/configs/
- Hook installation
- **ALREADY THE RIGHT DESIGN** but not used consistently

### 5. PathFinder CLASS, ModuleSetup CLASS, standard_imports
- Multiple "classes" with only static methods
- Path discovery duplicated across PathFinder and setup_imports()

## Design Goals

1. **NO wrapper functions** - call primitives directly
2. **NO legacy flags** - separate functions, not boolean parameters
3. **Flat hierarchy** - functions not classes (unless state needed)
4. **ONE source of truth for config generation** - propagate_configs.py ONLY
5. **Clear boundaries** - venv ops | path discovery | dependency install | NOTHING ELSE

## Proposed Structure

```
base/scripts/env/
├── __init__.py                      # Empty
├── paths.py                         # Path discovery & sys.path (merge PathFinder + setup_imports)
├── venv.py                          # Venv creation ONLY
├── requirements.py                  # Dependency installation ONLY
└── compute_profiles.py              # Compute profile detection ONLY

base/scripts/quality/                # Quality enforcement
├── __init__.py
├── banned_words.py                  # check_banned_words.py → here
├── lint_suppressions.py             # list_noqas.py → here
├── empty_inits.py                   # ensure_empty_inits.py → here
├── coauthored_commits.py            # detect_coauthored_commits.py → here
└── serial_hooks.py                  # validate_serial_hooks.py → here

base/scripts/meta/                   # Meta operations
├── __init__.py
├── ami_enforce.py                   # STAYS (CLI orchestrator)
├── propagate.py                     # propagate_configs.py → here (SINGLE SOURCE OF TRUTH)
├── cleanup.py                       # cleanup_configs.py → here
└── bootstrap_toolchain.py           # bootstrap_uv_python.py → here

base/scripts/lib/                    # Shared utilities
├── __init__.py
├── cli.py                           # STAYS
├── git.py                           # STAYS
└── modules.py                       # STAYS
```

## Core Functions (NO WRAPPERS, NO LEGACY FLAGS)

### base/scripts/env/paths.py
```python
"""Path discovery and sys.path management - SINGLE SOURCE OF TRUTH"""

def find_git_root(start_path: Path | None = None) -> Path | None:
    """Find .git directory."""

def find_module_root(start_path: Path | None = None) -> Path:
    """Find module root (has backend/ and requirements.txt)."""

def find_orchestrator_root(start_path: Path | None = None) -> Path | None:
    """Find AMI-ORCHESTRATOR root (has base/ and .git)."""

def find_base_module(start_path: Path | None = None) -> Path:
    """Find base module path."""

def setup_imports(start_path: Path | None = None) -> tuple[Path, Path]:
    """Discover paths and add to sys.path. Returns (orchestrator_root, module_root)."""
```

### base/scripts/env/venv.py
```python
"""Virtual environment operations ONLY"""

def get_venv_python(module_root: Path) -> Path:
    """Get platform-specific venv python path."""

def ensure_venv(module_root: Path, python_version: str | None = None) -> Path:
    """Create venv if doesn't exist. Returns venv python path."""
```

### base/scripts/env/requirements.py
```python
"""Dependency installation ONLY"""

def install_requirements_file(venv_python: Path, requirements_file: Path) -> None:
    """Install single requirements file with uv."""

def install_module_requirements(module_root: Path, venv_python: Path, include_test: bool = False) -> None:
    """Install base + module requirements in correct order."""

def requirements_installed(module_root: Path) -> bool:
    """Check .requirements_installed marker."""

def mark_requirements_installed(module_root: Path) -> None:
    """Create .requirements_installed marker."""
```

### base/scripts/env/compute_profiles.py
```python
"""Compute profile detection and overlays ONLY"""

def detect_compute_profile() -> str | None:
    """Detect from AMI_COMPUTE_PROFILE env var."""

def apply_compute_profile(module_root: Path, venv_python: Path) -> None:
    """Install requirements.env.{profile}.txt if detected. Idempotent."""
```

## Usage Patterns (Call Primitives Directly)

### For Test Runners (runner_bootstrap.py)
```python
from base.scripts.env.paths import find_module_root, setup_imports
from base.scripts.env.venv import get_venv_python, ensure_venv
from base.scripts.env.requirements import install_module_requirements, requirements_installed, mark_requirements_installed
from base.scripts.env.compute_profiles import apply_compute_profile

def ensure_module_venv(script_path: Path) -> None:
    """Ensure running in module venv, re-exec if needed."""
    module_root = find_module_root(script_path)
    setup_imports(module_root)

    venv_python = get_venv_python(module_root)

    # Create venv if missing
    if not venv_python.exists():
        venv_python = ensure_venv(module_root)
        install_module_requirements(module_root, venv_python, include_test=True)
        apply_compute_profile(module_root, venv_python)
        mark_requirements_installed(module_root)

    # Re-exec if not in venv
    if Path(sys.executable) != venv_python:
        os.execv(str(venv_python), [str(venv_python), str(script_path)] + sys.argv[1:])
```

### For Module Setup Scripts (module_setup.py)
```python
from base.scripts.env.paths import find_module_root, setup_imports
from base.scripts.env.venv import ensure_venv
from base.scripts.env.requirements import install_module_requirements
from base.scripts.env.compute_profiles import apply_compute_profile

def main() -> int:
    module_root = find_module_root()
    orchestrator_root, _ = setup_imports(module_root)

    venv_python = ensure_venv(module_root)
    install_module_requirements(module_root, venv_python, include_test=True)
    apply_compute_profile(module_root, venv_python)

    # Config generation: call propagate_configs.py directly
    subprocess.run([
        str(venv_python),
        str(orchestrator_root / "base" / "scripts" / "propagate_configs.py"),
        "--module", module_root.name
    ])

    return 0
```

### Phase 3: Delete Redundant Code

#### DELETE these files:
- `base/backend/utils/environment_setup.py` (287 lines) - split into env/*.py
- `base/backend/utils/module_orchestration.py` (85 lines) - replaced by env/bootstrap.py
- `base/backend/utils/path_finder.py` (104 lines) - moved to env/paths.py

#### DEPRECATE these:
- `base/backend/utils/standard_imports.py` - keep with deprecation notice

### Phase 4: Update Scripts

#### Move and rename:
```bash
# Quality checks
base/scripts/check_banned_words.py → base/scripts/quality/banned_words.py
base/scripts/list_noqas.py → base/scripts/quality/lint_suppressions.py
base/scripts/ensure_empty_inits.py → base/scripts/quality/empty_inits.py
base/scripts/detect_coauthored_commits.py → base/scripts/quality/coauthored_commits.py
base/scripts/validate_serial_hooks.py → base/scripts/quality/serial_hooks.py

# Meta operations
base/scripts/propagate_configs.py → base/scripts/meta/propagate.py
base/scripts/cleanup_configs.py → base/scripts/meta/cleanup.py
base/scripts/bootstrap_uv_python.py → base/scripts/meta/bootstrap_toolchain.py

# ami_enforce.py STAYS at base/scripts/ (top-level CLI)
```

## Function Mapping

### OLD → NEW

| Old Location | Old Function | New Location | New Function |
|--------------|-------------|--------------|-------------|
| environment_setup.py | EnvironmentSetup.get_venv_python() | env/venv.py | get_venv_python() |
| environment_setup.py | EnvironmentSetup.get_module_venv_python() | env/venv.py | get_venv_python(find_module_root()) |
| environment_setup.py | EnvironmentSetup.ensure_venv_exists() | env/bootstrap.py | bootstrap_module() |
| environment_setup.py | EnvironmentSetup._detect_compute_profile() | env/compute_profiles.py | detect_compute_profile() |
| environment_setup.py | EnvironmentSetup._resolve_env_requirements() | env/compute_profiles.py | find_profile_requirements() |
| environment_setup.py | EnvironmentSetup._install_requirement_path() | env/requirements.py | install_requirements_file() |
| environment_setup.py | EnvironmentSetup._apply_compute_profile_requirements() | env/compute_profiles.py | apply_compute_profile() |
| environment_setup.py | EnvironmentSetup.install_requirements() | env/requirements.py | install_module_requirements() |
| environment_setup.py | EnvironmentSetup.setup_python_paths() | env/paths.py | setup_imports() |
| standard_imports.py | setup_imports() | env/paths.py | setup_imports() |
| path_finder.py | PathFinder.find_git_root() | env/paths.py | find_git_root() |
| path_finder.py | PathFinder.find_module_root() | env/paths.py | find_module_root() |
| path_finder.py | PathFinder.find_orchestrator_root() | env/paths.py | find_orchestrator_root() |
| path_finder.py | PathFinder.find_base_module() | env/paths.py | find_base_module() |
| module_orchestration.py | ModuleSetup.setup_module_environment() | env/bootstrap.py | bootstrap_module() |
| module_orchestration.py | ModuleSetup.setup_for_script() | env/paths.py | setup_imports() |

### DELETED (redundant with propagate_configs.py):
- EnvironmentSetup.copy_platform_precommit_config()
- EnvironmentSetup.generate_mypy_config()
- EnvironmentSetup.install_precommit_hooks()

These should ONLY be called by:
- `propagate_configs.py` (explicit config propagation)
- `module_setup.py` (initial module setup)
- **NEVER by test runners or runtime code**

## Implementation Order

1. ✅ Remove lines 160-168 from environment_setup.py (DONE - prevents test-time regeneration)
2. Create base/scripts/env/ directory structure
3. Implement env/paths.py (merge path_finder + setup_imports)
4. Implement env/venv.py (extract from EnvironmentSetup)
5. Implement env/requirements.py (extract from EnvironmentSetup)
6. Implement env/compute_profiles.py (extract from EnvironmentSetup)
7. Implement env/bootstrap.py (replace ModuleSetup + ensure_venv_exists logic)
8. Update runner_bootstrap.py to use new functions
9. Update module_setup.py scripts across all modules
10. Move scripts to quality/ and meta/ directories
11. Update ami_enforce.py to use new locations
12. Delete old files (environment_setup.py, module_orchestration.py, path_finder.py)
13. Add deprecation notice to standard_imports.py

## Testing Strategy

1. Test each new function in isolation
2. Test bootstrap flow end-to-end
3. Verify test runners still work (no config regeneration)
4. Verify module_setup.py still works
5. Verify ami_enforce still works
6. Run full test suite across all modules

## Success Criteria

- ✅ No classes with only static methods
- ✅ ONE function for each task (no duplication)
- ✅ Clear separation: venv ops | paths | requirements | configs | quality
- ✅ Test runners do NOT regenerate configs
- ✅ Config generation is EXPLICIT opt-in only
- ✅ All tests pass
- ✅ Git push succeeds without "files modified by hook" error

## Non-Goals

- NOT touching run_*.py scripts (test/server runners)
- NOT touching check_storage.py (DataOps-specific)
- NOT changing public APIs until after migration complete
