# Secrets Broker Remediation Specification

## Summary
Unvetted changes landed a root-level `docker/` directory, bespoke Dockerfiles, rewritten compose stacks, and helper scripts that bypass the Nodes launcher (`nodes/scripts/setup_service.py`). These artifacts conflict with the repository's architecture, duplicate functionality that belongs inside the Base module, and violate guardrails that centralise process orchestration under `nodes/config/setup-service.yaml` with uv-native tooling.

## Goals
- Restore the Nodes launcher and its compose/process registry as the single orchestration authority.
- Rehome secrets-broker logic under the Base module (`base/backend/dataops/...`) with uv entry points instead of root-level scripts or Dockerfiles.
- Remove redundant Dockerfiles, scripts, docs, and dependency additions that were introduced solely to support the rogue stack.
- Provide a sanctioned path for running the secrets broker via the launcher, referencing approved images or uv commands.

## Scope
- All files introduced or modified outside module roots to support the rogue stack (`/docker`, `docker-compose*.yml`, `scripts/`, dependency manifests, docs, TODOs).
- Base module adjustments necessary to host the broker and its APIs.
- Nodes configuration updates required to register and manage the broker process.

## Constraints
- Must respect module guardrails (`base/` is allowed; other modules untouched unless coordinated) and the empty-`__init__.py` policy.
- Compose files must remain launcher-compatible; no ad-hoc Dockerfiles at repo root.
- Tooling should leverage uv commands instead of bespoke shell scripts where possible.

## Remediation Plan

### Phase 1 — Containment & Rollback
1. Delete `/docker/` and reset `docker-compose.yml`, `docker-compose.dev.yml`, and `docker-compose.services.yml` to `origin/main` equivalents.
2. Remove supporting scripts introduced at repo root (`scripts/run_secrets_broker.py`, `scripts/env/bitwarden-session-agent.sh`, `scripts/env/dev-stack.yaml`, `scripts/services.yaml`).
3. Drop FastAPI/Uvicorn additions from `pyproject.toml`, `uv.lock`, and revert `.pre-commit-config.yaml`/`AGENTS.md` tweaks tied solely to the rogue stack.
4. Remove documentation and backlog entries that describe the unsanctioned design (`docs/SPEC-SENSITIVE-FIELD-VAULT-HYDRATION.md`, additions in `docs/NextAuth-Integration.md`, `TODO-DOOMSCROLL.md`, etc.) unless they are reauthored for the sanctioned design.

### Phase 2 — Proper Secrets Broker Integration
1. Implement the broker entirely within Base:
   - Extend `base/backend/dataops/secrets/` with store, repository, and client logic.
   - Add a FastAPI/Starlette app under `base/services/secrets_broker/app.py` plus a uv-compatible launcher (e.g., `base/services/secrets_broker/run.py`).
   - Update DataOps decorators (`@sensitive_field`) and pipelines to use the broker via sanctioned client APIs.
2. Provide configuration via Base settings (e.g., `base/config/secrets_broker.py`) and document required env vars.
3. Publish/consume broker images through Base-managed Docker assets or invoke uv directly—no root Dockerfiles.
4. Update `docker-compose.services.yml` (or an equivalent launcher compose file) to reference the sanctioned image/command.
5. Ensure OpenBao is orchestrated alongside the broker through the launcher-managed compose stack. If a separate compose profile is required, add it under `docker-compose.services.yml` (or a dedicated `docker-compose.secrets.yml`) and wire it into the Nodes launcher so `nodes/scripts/setup_service.py` can start/stop the dependency.
6. Amend `nodes/config/setup-service.yaml` to register the broker under `processes` (type `docker-compose` or `command`) so `nodes/scripts/setup_service.py process start secrets-broker` manages lifecycle while guaranteeing OpenBao availability.

### Phase 3 — Validation & Documentation
1. Run `python nodes/scripts/setup_service.py verify --no-tests` to ensure launcher awareness, then `process start/stop secrets-broker` to validate control.
2. Add Base-level unit/integration tests for pointer storage, OpenBao interactions, and API endpoints. End-to-end coverage must hit a real OpenBao deployment (via the launcher compose stack) rather than the current in-memory stubs.
3. Update Base docs (e.g., `base/docs/SPEC-SECRETS-BROKER.md`) to explain architecture, configuration, and launcher usage. Trim root-level docs to reference the sanctioned implementation and emphasise launcher-first orchestration.
4. Record remediation outcomes in changelog/AGENTS guardrails, highlighting the ban on ad-hoc Dockerfiles at repo root and reaffirming uv-native workflows.

## Risks & Mitigations
- **Lingering references**: After cleanup, run `rg` to ensure no files point to removed paths (`scripts/run_secrets_broker.py`, etc.).
- **Dependency conflicts**: Removing FastAPI/Uvicorn from root may impact future work; note sanctioned reintroduction steps inside Base if required.
- **OpenBao integration gaps**: Align broker implementation with Base’s secrets broker client abstractions; escalate if additional module-level support is needed.

## Acceptance Criteria
- Root compose files are launcher-compatible and free of `dockerfile:` references to `/docker`.
- `/docker` directory and the rogue scripts/Docs are gone.
- Secrets broker logic resides in Base with uv-native entry points, and the Nodes launcher can manage the service.
- Documentation reflects the corrected design and reiterates launcher-first orchestration principles.
