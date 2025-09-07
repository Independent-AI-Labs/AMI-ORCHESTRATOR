# Setup Contract (Orchestrator ⇄ Modules)

Intent: Define a single, tight, and robust setup contract that keeps import/path handling centralized and avoids ad-hoc patterns.

Principles
- Runner-only import/path setup: Only `run_*` and `run_tests` scripts adjust `sys.path`.
- Module-local venvs: Each module owns `.venv` created with `uv venv --python 3.12`.
- Centralized environment utilities: Use `base.backend.utils.{path_finder, environment_setup, path_utils}` as the single source of truth.
- Deferred third-party imports in setup scripts: Use stdlib `logging` until after venv exists and deps are installed.

Orchestrator responsibilities
- Initialize/sync submodules (no unsafe `git pull` inside them; use submodule update).
- Ensure toolchain only (uv + Python 3.12 available to `uv`).
- Execute each module’s `module_setup.py` via `uv run --python 3.12`.
- Do not create a root venv and do not import module code.

Module responsibilities
- Provide `python.ver` with the required minor version (e.g., `3.12`).
- Provide `requirements.txt` and optional `requirements-test.txt`.
- Provide `module_setup.py` that delegates to Base’s `AMIModuleSetup`:
  - Create `.venv` (via `EnvironmentSetup.ensure_venv_exists` or equivalent).
  - Install base + module requirements before importing any third-party packages.
  - Install pre-commit hooks if configured.
- Entrypoints (`run_*`, `run_tests`) perform all `sys.path` setup using centralized PathFinder helpers; application packages must not modify `sys.path`.

Base module (source of truth)
- `PathFinder`: discover module root, orchestrator root, base path.
- `EnvironmentSetup`: create/manage venvs, install requirements, copy pre-commit config, generate mypy config.
- `path_utils`: compatibility and convenience layer; re-exports the standardized utilities.

Quality gates
- Python 3.12 target across lint/type configs.
- Pre-commit hooks must be installable and platform-aware (Windows/macOS/Linux).
- No imports of local packages that depend on third-party libraries before venv is provisioned and dependencies installed.
