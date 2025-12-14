# Quality Policy (Cross-Module)

## Non-negotiables

- **Centralised path/import control**: Scripts should avoid manual `sys.path` manipulation. Use the provided runner scripts (`ami-run`) which handle environment context.
- **Single toolchain**: Python 3.12 via `uv` across every module. No mixed runtimes.
- **Lint/type targets**: `ruff` targets `py312` and `mypy` is pinned to `python_version = 3.12` (root and module-level configs already updated).
- **Setup scripts**: Use standard `Makefile` targets (`setup`, `test`, `clean`) for all build orchestration.

## Configuration Hygiene

- Generate module-local `mypy.ini`, `ruff.toml`, and `.pre-commit-config.*.yaml` from Base templates to avoid drift.
- Hooks must use `python -m ...` executions for portability; avoid hard-coded binary paths.
- Keep `python.ver`, `requirements*.txt`, and `uv.lock` files in sync with the actual runtime.

## Documentation Integrity

- Root docs must mirror implemented features. Mark WIP items explicitly (e.g., compliance backend).
- When removing legacy references, update `docs/TODO-DOCS-GAPS.md` to record the follow-up rather than letting stale links persist.

## Security & SCM Expectations

- Use `make setup-all` (or `make setup-<module>`) to initialize submodules. Manual `git submodule update` calls inside scripts are discouraged.
- `.gitmodules` defaults to SSH; document HTTPS alternate commands for CI in module onboarding guides.
- Ensure `.gitignore` excludes PDFs and other compliance artefacts generated from source standards (already enforced globally).

## Open Items

- Migrate remaining `run_tests.py` scripts to use Base `scripts/env/paths.py` helpers instead of custom `_ensure_repo_on_path()` implementations:
  - `scripts/run_tests.py:16-23`
  - `ux/scripts/run_tests.py:15-21`
  - `browser/scripts/run_tests.py:10-16`
  - `domains/marketing/scripts/run_tests.py:10-16`
- Add contract tests for the forthcoming compliance backend MCP server once implemented.
