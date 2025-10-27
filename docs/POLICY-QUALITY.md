# Quality Policy (Cross-Module)

## Non-negotiables

- **Centralised path/import control** (migration in progress): only runner scripts (`run_*`, `scripts/run_tests.py`) and `module_setup.py` may mutate `sys.path`. New scripts and updated scripts must use Base `scripts/env/paths.py` helpers (`setup_imports`, `find_orchestrator_root`, `find_module_root`) instead of custom path discovery logic.
- **Single toolchain**: Python 3.12 via `uv` across every module. No mixed runtimes.
- **Lint/type targets**: `ruff` targets `py312` and `mypy` is pinned to `python_version = 3.12` (root and module-level configs already updated).
- **Setup scripts**: rely on stdlib `logging` and defer third-party imports until after dependencies are installed.

## Configuration Hygiene

- Generate module-local `mypy.ini`, `ruff.toml`, and `.pre-commit-config.*.yaml` from Base templates to avoid drift.
- Hooks must use `python -m ...` executions for portability; avoid hard-coded binary paths.
- Keep `python.ver`, `requirements*.txt`, and `uv.lock` files in sync with the actual runtime.

## Documentation Integrity

- Root docs must mirror implemented features. Mark WIP items explicitly (e.g., compliance backend).
- When removing legacy references, update `docs/TODO-DOCS-GAPS.md` to record the follow-up rather than letting stale links persist.

## Security & SCM Expectations

- Use `git submodule update --init --recursive` (handled by `module_setup.py`) instead of manual pulls inside submodules.
- `.gitmodules` defaults to SSH; document HTTPS alternate commands for CI in module onboarding guides.
- Ensure `.gitignore` excludes PDFs and other compliance artefacts generated from source standards (already enforced globally).

## Open Items

- Migrate remaining `run_tests.py` scripts to use Base `scripts/env/paths.py` helpers instead of custom `_ensure_repo_on_path()` implementations:
  - `scripts/run_tests.py:16-23`
  - `ux/scripts/run_tests.py:15-21`
  - `browser/scripts/run_tests.py:10-16`
  - `domains/marketing/scripts/run_tests.py:10-16`
- Add contract tests for the forthcoming compliance backend MCP server once implemented.
