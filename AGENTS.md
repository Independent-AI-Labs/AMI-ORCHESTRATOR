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

Testing discipline:
- Run each module's test suite using the module's script in `scripts/` (for example, `python3 scripts/run_tests.py`).
- Do not expect the root environment to install per-module dependencies; rely on module-level runners before committing.

Compute profiles:
- Heavy compute stacks are opt-in. Set `AMI_COMPUTE_PROFILE` to `cpu`, `nvidia`, `intel`, or `amd` before running setup/tests if you genuinely need those wheels.
- Each module may provide `requirements.env.<profile>.txt`; never hardcode GPU/XPU packages outside those files.

Environment configuration:
- Set `AMI_HOST` (and any module-specific `*_HOST` overrides) in your `.env` when you need to point services at a different machine; defaults fall back to `127.0.0.1`.
- Populate `SSH_DEFAULT_USER` and `SSH_DEFAULT_PASSWORD` in your `.env` so the SSH MCP tests can log into your local machine; they should reference a real system account.

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
