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

## 2. Environment Provisioning

Each module must handle its own environment setup via a standard `Makefile`.

**Responsibilities:**
- Create a virtual environment (`.venv`) using Python 3.12.
- Install dependencies from `pyproject.toml` (or `package.json` for JS modules).
- Expose a `setup` target.

### Setup Mechanism (Makefile)

- Execute each module's setup via `make setup` (run from the module root).
- The Root Makefile orchestrates this via `make setup-all`.

**Required Makefile Targets:**
- `setup`: The primary entry point. Must ensure the environment is ready for development.
- `clean`: Should remove artifacts like `.venv` and `node_modules`.
- `test`: Should run the module's test suite.

Example `Makefile`:
```makefile
.PHONY: setup test clean

setup:
	uv python install 3.12
	uv sync --dev

test:
	uv run pytest -q

clean:
	rm -rf .venv
```

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
