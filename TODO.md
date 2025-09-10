# TODO (Prioritized)

P0 — Blockers / Immediate
- Browser: module_setup.py fails with TypeError on `Path | None` (annotations evaluated). Fix by adding `from __future__ import annotations` at top and rerun setup.
- Compliance, Domains: pre-commit hooks not installed. Ensure dev tools installed in their venvs by providing `requirements-test.txt` (pre-commit, ruff, pytest, mypy) and re-run module setup to install hooks.
- Verify all modules use Python 3.12 via `python.ver` (done). Keep audit to catch regressions.
- Mypy scope collisions: running mypy per-module reveals duplicate module names when `mypy_path` includes `..` (e.g., `files` sees `backend.*` from root). Decide on cross-module import strategy and adjust templates to avoid duplicate discovery (options: avoid `..` in `mypy_path`, make `base` a proper package dependency, or use namespace packages with distinct top-levels).
- Root mypy import resolution: root `backend/*` imports `base.backend.*` but mypy cannot resolve without including submodule on path. Pick one: add `mypy_path = base` for root-only checks or avoid cross-module imports in root until packaging is in place.

P1 — Setup Robustness / Consistency
- Root setup: remove legacy “No module named pip” noise by switching to pyproject + `uv sync` or ensure `uv pip` installs minimum tooling before hook install.
- Integrate config drift audit into routine: `python module_setup.py --audit-configs` in CI to report differences without writes. Apply with explicit flag when approved.
- Ensure each module has `requirements-test.txt` to consistently install dev tooling (pre-commit, ruff, pytest, mypy) even in legacy (non-pyproject) flow.
 - Validate matrix: tune `scripts/validate_all.py` to handle the above mypy pathing decisions; keep ruff+mypy fast and isolated per module without cross-talk.

P2 — Validation Matrix / CI
- Add a script to recreate all venvs and verify: deps resolved, hooks present, sentinel imports work, mypy/ruff run per module.
- Add per-module smoke `uv run pre-commit run -a` in CI (non-destructive) to catch bad configs early.
- Consider root-level pyproject.toml for consistent uv-native workflow at root.

P3 — Documentation
- Document the config replication/audit behavior in README or docs/Setup-Contract.md, including flags and non-destructive defaults.
