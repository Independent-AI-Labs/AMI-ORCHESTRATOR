Purpose
- Hand off the current state and guardrails so the next agent can continue safely and efficiently on the main branch.

Repository State (at handoff)
- Branch: `main` is ahead of `origin/main` by 3 commits.
- Merges: `origin/feat/initial-framework` has been merged into `main` (unrelated histories allowed).
- Submodules present: `base`, `browser`, `files`, `node`, `streams`, `ux`, plus `compliance` and `domains`.
- New top-level files/dirs since merge: `docker-compose.yml`, `requirements.txt`, `src/**`, `tests/**`, multiple docs under `docs/`, and `agent.sh`.
- Note: `__pycache__` artifacts were accidentally committed within `src/**` and `tests/**` by the merged branch and should be removed.

Guardrails (do not deviate)
- Do not create new branches unless explicitly instructed.
- Do not push with `--no-verify`. Let hooks run.
- Only push after all tests and checks pass locally.
- Treat submodules carefully: avoid rewriting their history; only update pointers in the superproject unless explicitly asked to change inside a submodule.

Environment & Tooling
- Python: prefer `uv` for environment management and invocation.
  - Bootstrap: `uv run python scripts/bootstrap_uv_python.py`
  - Run tests: `uv run python scripts/run_tests.py`
- Pre-commit hooks: `.pre-commit-config.yaml` exists. Install and run locally:
  - `uv run pre-commit install --install-hooks`
  - `uv run pre-commit run -a`
- Docker (for Dgraph tests): `docker-compose.yml` is provided. Bring up services when running integration tests that require Dgraph:
  - `docker compose up -d`
- Guardrail launcher: `./agent.sh` starts Codex with the agreed guardrails and a 20-minute timeout.

Immediate Tasks (high-priority)
1) Clean VCS noise from merged branch
   - Remove committed `__pycache__` files and ensure they’re ignored:
     - `git rm --cached -r src/**/__pycache__ tests/**/__pycache__ || true`
     - Confirm `.gitignore` already contains `__pycache__/` (it does).
     - Commit with message: `chore: remove committed __pycache__ artifacts`

2) Verify submodules are synchronized
   - `git submodule update --init --recursive`
   - If there are pending changes inside any submodule that must be preserved, commit inside the submodule, then update the superproject pointer.

3) Make tests pass locally (no network installs during hooks)
   - `uv run python scripts/run_tests.py`
   - If Dgraph-dependent tests fail and Dgraph is not running, either:
     - Start services: `docker compose up -d`, then re-run tests; or
     - Temporarily skip those specific tests via `-k "not dgraph"` if skipping is acceptable for local pre-push; do not change test code without approval.

4) Lint and type-check
   - Ruff: `uv run ruff check . && uv run ruff format .`
   - Mypy: `uv run mypy --config-file mypy.ini .`
   - Address only errors related to your changes or obvious fallout from the merge; avoid broad refactors.

5) Push policy
   - When all tests/linters pass: `git push` (no `--no-verify`).
   - Do not create or push additional branches unless instructed.

Contextual Notes
- Test layout (superproject):
  - New tests under `tests/` validate the initial framework (agents, dgraph store, orchestrator).
  - Submodules have their own test suites (`*/scripts/run_tests.py`, or `pytest.ini`). Run them only if you are asked to touch those submodules.
- Configuration:
  - `requirements.txt` and `requirements-test.txt` are present; prefer `uv` to resolve and isolate Python deps.
  - The superproject’s `.gitignore` already ignores `__pycache__/`, `.venv/`, and common build artifacts.
- Security/Secrets:
  - Do not commit credentials. Example files like `node/test_creds.txt` are test fixtures; do not populate them with real secrets.

Checks Before Any Push
- [ ] `uv run python scripts/run_tests.py` passes (or expected/integration tests are gated appropriately and documented in the commit message).
- [ ] `uv run ruff check .` passes and formatting applied.
- [ ] `uv run mypy --config-file mypy.ini .` passes (or any ignores are justified and minimal).
- [ ] No `__pycache__` or `.pytest_cache` tracked files remain: `git ls-files | rg "__pycache__|\.pytest_cache"` returns empty.
- [ ] Submodule pointers are consistent: `git submodule status` shows exact commits (no `+` prefix).

Suggested Commit Messages
- Merge cleanup: `chore: remove committed __pycache__ artifacts`
- Submodule sync: `chore(submodules): update pointers after local changes`
- Tests: `test: stabilize dgraph tests; document docker compose usage`

Contact Points in the Tree
- Orchestration framework: `src/orchestration/orchestrator.py`
- Dgraph integration: `src/dgraph/dgraph_store.py`, `src/dgraph/schema.dql`
- Agent base: `src/agents/base.py`
- Test suite: `tests/`
- Tooling scripts: `scripts/`
- Submodules: `base/`, `browser/`, `files/`, `node/`, `streams/`, `ux/`, plus `compliance/`, `domains/`

If You Need to Deviate
- If a deviation from guardrails is necessary (e.g., hotfix branch), request explicit instruction first. Document why, how, and the rollback plan.

