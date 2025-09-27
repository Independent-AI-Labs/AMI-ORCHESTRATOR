# Quality Policy (Cross-Module)

## Non-negotiables

- Centralised path/import control: only runner scripts (`run_*`, `scripts/run_tests.py`) may mutate `sys.path`, and they must do so via Base `PathFinder` helpers.
- Single toolchain: Python 3.12 via `uv` across every module. No mixed runtimes.
- Lint/type targets: `ruff` targets `py312` and `mypy` is pinned to `python_version = 3.12` (root and module-level configs already updated).
- Setup scripts rely on stdlib `logging` and defer third-party imports until after dependencies are installed.

## Configuration Hygiene

- Generate module-local `mypy.ini`, `ruff.toml`, and `.pre-commit-config.*.yaml` from Base templates to avoid drift.
- Hooks must use `python -m ...` executions for portability; avoid hard-coded binary paths.
- Keep `python.ver`, `requirements*.txt`, and `uv.lock` files in sync with the actual runtime.

## Documentation Integrity

- Root docs must mirror implemented features. Mark WIP items explicitly (e.g., compliance backend or UX NextAuth rollout).
- When removing legacy references, update `docs/Docs-Gaps.md` to record the follow-up rather than letting stale links persist.

## Security & SCM Expectations

- Use `git submodule update --init --recursive` (handled by `module_setup.py`) instead of manual pulls inside submodules.
- `.gitmodules` defaults to SSH; document HTTPS fallbacks for CI in module onboarding guides.
- Ensure `.gitignore` excludes PDFs and other compliance artefacts generated from source standards (already enforced globally).

## Open Items

- Update `ux/scripts/run_tests.py` to adopt Base `PathFinder` helpers.
- Add contract tests for the forthcoming compliance backend MCP server once implemented.
