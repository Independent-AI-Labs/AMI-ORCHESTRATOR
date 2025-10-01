# Agent Guidelines

NO FUCKING DETACHED HEADS — WE ARE WORKING ONLY IN MAIN ALWAYS UNLESS I SAY OTHERWISE!!!!!!

Scope: This file applies to the entire AMI-ORCHESTRATOR repository and all directories under it, including submodules referenced by this repo.

Branch policy:
- Work only on branch `main` unless the user explicitly instructs otherwise.
- Never work on a detached HEAD. If you find yourself detached, switch to a named branch immediately.
- Submodules should also be on their respective `main` branches unless explicitly instructed otherwise.

Module restrictions:
- Do not modify ANY module directories (base, browser, compliance, domains, files, nodes, streams, ux, etc.) unless the user explicitly instructs you to.

Enforcement:
- `agent.sh` only prints an error when a detached HEAD is detected in the root repo or any submodule. It does not exit, and it does not enforce being on `main`.

Commit discipline:
- Do not bypass hooks (no `--no-verify`).
- Commit only after linters, type checks, and tests pass.
- Land work module-by-module (skip `ux` until the user says otherwise) so CI can start verifying while you keep moving; push after each clean chunk.
- Read the file before editing it. Open and inspect first, then apply changes with the appropriate tool (no blind scripting).
- Never build or wire "fallback" behaviour unless the user explicitly requests it for the current task. If a storage option (like the local file config) exists, treat it as opt-in and surface its use clearly instead of silently enabling it.

Testing discipline:
- Run each module's test suite using the module's script in `scripts/` (for example, `python3 scripts/run_tests.py`).
- Do not expect the root environment to install per-module dependencies; rely on module-level runners before committing.

Dependency review workflow:
- Query real registries before bumping anything. Use `python3 - <<'PY'` with `urllib.request` to read `https://pypi.org/pypi/<package>/json` for PyPI packages, and `npm view <package> version` (or `npx pnpm@<version> view`) for Node/Pnpm packages. Never guess or copy numbers from memory.
- Pin every dependency to an exact version in manifests and lockfiles (no `^`, `~`, or unbounded ranges). Update Python pins via `uv lock --refresh` or `uv sync`, and Node/Pnpm pins via `npm install` or `npx pnpm@<version> install` so lock files stay in sync.
- After bumping, run the module's setup (`python3 module_setup.py`) and its documented test runner. If the newest release is incompatible, use the latest compatible release and call out the constraint in your summary.
- Skip `domains/predict` during installs/tests; that module is deprecated and remains out of scope for dependency updates.

Compute profiles:
- Heavy compute stacks are opt-in. Set `AMI_COMPUTE_PROFILE` to `cpu`, `nvidia`, `intel`, or `amd` before running setup/tests if you genuinely need those wheels.
- Each module may provide `requirements.env.<profile>.txt`; never hardcode GPU/XPU packages outside those files.

Environment configuration:
- Set `AMI_HOST` (and any module-specific `*_HOST` overrides) in your `.env` when you need to point services at a different machine; defaults fall back to `127.0.0.1`.
- Populate `SSH_DEFAULT_USER` and `SSH_DEFAULT_PASSWORD` in your `.env` so the SSH MCP tests can log into your local machine; they should reference a real system account.
- Copy the updated `default.env` files (base/browser/domains/ux) and fill the auth stack variables: `DATAOPS_AUTH_URL`, `NEXT_PUBLIC_DATAOPS_AUTH_URL`, `DATAOPS_INTERNAL_TOKEN`, `SECRETS_BROKER_URL`, the broker tokens, and the `OPENBAO_*` settings that match your secrets instance. These must be valid before running auth or secrets tests.

Process management:
- Run `npm run dev` for the UX app in the background (for example, `npm run dev &`) or in a separate terminal since it blocks the current shell.

Reference code:
- `ux/ui-concept` is prototype/reference code; do not spend cycles fixing lint or build failures there unless explicitly asked.

Docker access:
- Add yourself to the `docker` group (`printf '%s\n' "$SUDO_PASS" | sudo -S usermod -aG docker $(whoami)`), then start a new shell (`newgrp docker`) before running compose commands.
- Bring the data stack up with `docker-compose -f docker-compose.data.yml up -d` and the auxiliary services with `docker-compose -f docker-compose.services.yml up -d` when tests require them.

Nodes setup automation:
- Use `python nodes/scripts/setup_service.py preinstall` before provisioning to run the shared preinstall checks.
- `python nodes/scripts/setup_service.py verify --no-tests` runs module setup; drop `--no-tests` to include each module's tests.
- Managed processes (docker/python/npm) are declared in `nodes/config/setup-service.yaml`; start or stop them via the CLI or the `NodeSetupMCP` server.
