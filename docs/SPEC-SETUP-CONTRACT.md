# Setup Contract (Orchestrator ⇄ Modules)

Intent: Define a single, tight, and robust setup contract that keeps import/path handling centralized and avoids ad-hoc patterns.

## Principles

- **Runner-only import/path setup**: Only `run_*` and `run_tests` scripts adjust `sys.path`.
- **Module-local venvs**: Each module owns `.venv` created with `uv venv --python 3.12`.
- **Centralized environment utilities**: Use `base.scripts.env.{paths, venv}` as the single source of truth.
- **Deferred third-party imports in setup scripts**: Use stdlib `logging` until after venv exists and deps are installed.

## Orchestrator Responsibilities

- Initialize/sync submodules (no unsafe `git pull` inside them; use submodule update).
- Ensure toolchain only (uv + Python 3.12 available to `uv`).
- Execute each module's `module_setup.py` via Python (modules handle their own venv setup internally).
- Do not create a root venv and do not import module code.

## Module Responsibilities

- Provide `python.ver` with the required minor version (e.g., `3.12`).
- Provide `pyproject.toml` with dependencies under `[project.dependencies]` and `[tool.uv.dev-dependencies]`.
- Optional: Maintain parallel `requirements.txt` for backward compatibility (not used by module_setup.py).
- Provide `module_setup.py` that uses Base's consolidated environment utilities:
  - Import from `base.scripts.env.paths` (for `setup_imports`, path discovery functions).
  - Import from `base.scripts.env.venv` (for `ensure_venv`, `get_venv_python`).
  - Create `.venv` via `ensure_venv(module_root, python_version="3.12")`.
  - Sync dependencies via `uv sync --dev` (reads pyproject.toml).
  - Install native git hooks from `/base/scripts/hooks/` to module's `.git/hooks/`.
  - Recursively setup direct child submodules.
- Entrypoints (`run_*`, `run_tests`) perform all `sys.path` setup using centralized path helpers; application packages must not modify `sys.path`.

## Base Module (Source of Truth)

Located in `base/scripts/env/`:

- **`paths.py`**: Path discovery and sys.path management
  - `find_git_root()`: Locate nearest .git directory
  - `find_module_root()`: Find module root (has backend/ and requirements.txt or .venv)
  - `find_orchestrator_root()`: Find main orchestrator root (has base/ and .git)
  - `find_base_module()`: Locate base module path
  - `setup_imports()`: Add orchestrator and module roots to sys.path

- **`venv.py`**: Virtual environment operations
  - `ensure_venv(module_root, python_version)`: Create venv if doesn't exist
  - `get_venv_python(module_root)`: Get Python executable path for venv

- **`requirements.py`**: Legacy dependency installation (requirements.txt fallback)
  - Used by `runner_bootstrap.py` for backward compatibility
  - Not used by `module_setup.py` (which uses `uv sync` instead)
  - Provides `install_module_requirements()`, `requirements_installed()`, `mark_requirements_installed()`

## Module Setup Pattern

All modules follow this standardized `module_setup.py` pattern (see base/module_setup.py:16-17):

```python
# Bootstrap sys.path - MUST come before base imports
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))

# Import consolidated environment utilities from base
from base.scripts.env.paths import setup_imports
from base.scripts.env.venv import ensure_venv

def setup(module_root: Path, project_name: str | None) -> int:
    # Use consolidated env utilities
    setup_imports(module_root)
    ensure_venv(module_root, python_version="3.12")

    # Sync dependencies from pyproject.toml
    subprocess.run(["uv", "sync", "--dev"], cwd=module_root, check=True)

    # Install hooks, setup children
    # ...
```

## Runner Script Pattern

All `run_*` and `run_tests` scripts follow this pattern (see base/scripts/run_tests.py:14-22):

```python
# Bootstrap sys.path - MUST come before base imports
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))

# Now import from base
from base.scripts.env.paths import setup_imports

# Setup paths
ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()
```

## Dependency Management

- **Standard**: All modules use `pyproject.toml` for dependency management (PEP 621 standard).
- **Installation**: Module setup runs `uv sync --dev` to install from pyproject.toml.
- **Legacy files**: Some modules (base, browser, files, nodes) maintain parallel `requirements.txt` files for backward compatibility with tools that haven't migrated to pyproject.toml yet.
- **Active source**: `module_setup.py` exclusively uses pyproject.toml via `uv sync`; requirements.txt files are not consulted during setup.

## Quality Gates

- Python 3.12 target across lint/type configs.
- Native git hooks must be installable and platform-aware (Windows/macOS/Linux).
- No imports of local packages that depend on third-party libraries before venv is provisioned and dependencies installed.
