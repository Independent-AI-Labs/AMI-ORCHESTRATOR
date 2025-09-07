TODO — UV Migration and Setup Contract

Goals
- Make each module self-contained with uv-managed venvs.
- Eliminate ad-hoc path hacks and third‑party imports during setup.
- Move to pyproject/uv.lock per module with clear console scripts.
- Keep orchestrator as the toolchain entrypoint only.

Principles
- Python 3.12 standard across repo; managed via uv.
- No third‑party imports at setup time; stdlib only for module_setup.py.
- Centralize path/import setup in runner-only spots; no hidden sys.path edits.
- Prefer `uv run -m package.entry` over invoking scripts directly.

Milestones
1) Toolchain ready (uv + Python 3.12)
- [x] Bootstrap script: scripts/bootstrap_uv_python.py
- [x] Orchestrator ensures uv + 3.12 toolchain

2) Module setup contract hygiene
- [x] Add module_setup.py delegators for modules missing them (compliance, domains)
- [x] Add contract checker: scripts/check_setup_contract.py
- [x] Add pyproject template for modules: docs/uv/pyproject-template.toml
- [ ] Wire checker into CI (optional pre-commit and pipeline step)

3) UV-native modules (phased)
- [x] Base: add pyproject.toml, define console scripts, generate uv.lock
- [x] Browser: add pyproject.toml, console scripts, uv.lock
- [x] Files: add pyproject.toml, console scripts (uv.lock optional)
- [x] Node: add pyproject.toml, console scripts, uv.lock
- [x] Streams: add pyproject.toml (uv.lock present)
- [x] UX: add pyproject.toml (scripts optional)
- [ ] Compliance: add pyproject.toml, console scripts, uv.lock
- [ ] Domains: add pyproject.toml, console scripts, uv.lock

4) Orchestrator support for uv-native
- [x] Detect per-module pyproject.toml and run `uv sync` (pre-CI)
- [x] Replace requirements*.txt flows with uv lock flows where available
- [x] Document fallback when pyproject is absent (current behavior)

5) CI and developer workflow
- [ ] Cache uv and Python toolchains
- [ ] Use `uv run` for ruff, mypy, pytest
- [ ] Add frozen lock validation: `uv sync --frozen`
- [ ] Contract checks: no top-level third‑party imports in module_setup.py

Sprint 1 — Immediate Tasks
- [x] Create TODO-UV.md with plan and checklists
- [x] Add module_setup.py delegators for compliance and domains
- [x] Add pyproject template under docs/uv
- [x] Add setup contract checker script
- [x] Propose pre-commit hook to run the checker in orchestrator context

How to use the checker
- Run: `python scripts/check_setup_contract.py`
- Exit code is non-zero if violations are found.
- Intended to be added to CI and/or pre-commit for orchestrator-only checks.

Notes
- Do not introduce pyproject.toml piecemeal into deeply-coupled modules without verifying entrypoints and local imports. Start with Base to set patterns, then propagate.
- `uv run` can execute modules even before full migration; use it to keep runtimes consistent.
