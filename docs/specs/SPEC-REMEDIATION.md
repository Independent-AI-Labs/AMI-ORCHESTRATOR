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

### Phase 1 — Containment & Rollback [COMPLETED]
1. ✅ Deleted `/docker/` directory
2. ✅ Removed root-level scripts: `scripts/run_secrets_broker.py`, `scripts/env/bitwarden-session-agent.sh`, `scripts/env/dev-stack.yaml`
3. ✅ Removed `docker-compose.dev.yml`
4. ✅ FastAPI/Uvicorn moved to `base/pyproject.toml` (sanctioned location)
5. ✅ Removed unsanctioned documentation: `docs/SPEC-SENSITIVE-FIELD-VAULT-HYDRATION.md`, `docs/NextAuth-Integration.md`

**Note:** `scripts/services.yaml` is the **sanctioned launcher manifest** and must be retained. It is the canonical service registry referenced by `nodes/backend/launcher/loader.py:18` and `nodes/backend/mcp/launcher/launcher_server.py:61`.

### Phase 2 — Proper Secrets Broker Integration [COMPLETED]
1. ✅ Implemented broker in Base module:
   - `base/backend/dataops/secrets/` contains pointer.py, adapter.py, repository.py, client.py
   - `base/backend/services/secrets_broker/` contains app.py, config.py, openbao_client.py, store.py
   - `base/scripts/run_secrets_broker.py` provides uv-compatible launcher
   - DataOps decorators (`@sensitive_field`) integrated in base/backend/dataops/models/
2. ✅ Configuration via `base/backend/services/secrets_broker/config.py`
3. ✅ No root Dockerfiles; broker runs via `uv run base/scripts/run_secrets_broker.py`
4. ✅ OpenBao orchestrated via `docker-compose.secrets.yml` with profile support
5. ✅ Services registered in `nodes/config/setup-service.yaml`:
   - `openbao` process (lines 54-60): docker-compose type, references docker-compose.secrets.yml
   - `secrets-broker` process (lines 61-72): command type, runs via uv
6. ✅ Launcher manifest `scripts/services.yaml` contains proper service definitions for both compose and local execution modes

### Phase 3 — Validation & Documentation [PARTIAL]
1. ✅ Launcher integration validated - services registered in `nodes/config/setup-service.yaml` and `scripts/services.yaml`
2. ✅ Base-level tests implemented:
   - `base/tests/test_secrets_broker_service.py`
   - `base/tests/test_secrets_broker_openbao_integration.py`
   - `base/tests/test_secrets_client_http_backend.py`
3. ⚠️ **PENDING**: Create `base/docs/SPEC-SECRETS-BROKER.md` documenting architecture, configuration, and launcher usage
4. ✅ Audit documentation exists at `base/docs/audit/20.10.2025/` covering implementation review

## Risks & Mitigations
- **Lingering references**: After cleanup, run `rg` to ensure no files point to removed paths (`scripts/run_secrets_broker.py`, etc.).
- **Dependency conflicts**: Removing FastAPI/Uvicorn from root may impact future work; note sanctioned reintroduction steps inside Base if required.
- **OpenBao integration gaps**: Align broker implementation with Base’s secrets broker client abstractions; escalate if additional module-level support is needed.

## Acceptance Criteria
- ✅ Root compose files are launcher-compatible and free of `dockerfile:` references to `/docker`
- ✅ `/docker` directory removed
- ✅ Rogue root-level scripts removed (`scripts/run_secrets_broker.py`, `scripts/env/bitwarden-session-agent.sh`, `scripts/env/dev-stack.yaml`)
- ✅ Secrets broker logic resides in Base (`base/backend/services/secrets_broker/`, `base/backend/dataops/secrets/`)
- ✅ Launcher can manage services via `nodes/config/setup-service.yaml` and `scripts/services.yaml`
- ⚠️ **PENDING**: Base module documentation (`base/docs/SPEC-SECRETS-BROKER.md`)

## Current Status: SUBSTANTIALLY COMPLETE

The remediation is 95% complete. All Phase 1 and Phase 2 objectives have been met:
- Rogue artifacts removed
- Secrets broker properly integrated into Base module
- Services registered with launcher infrastructure
- Tests implemented and passing
- Sanctioned service manifest (`scripts/services.yaml`) correctly retained as launcher registry

**Remaining work:** Create comprehensive documentation in `base/docs/SPEC-SECRETS-BROKER.md` explaining the secrets broker architecture, configuration, and integration with the launcher.
