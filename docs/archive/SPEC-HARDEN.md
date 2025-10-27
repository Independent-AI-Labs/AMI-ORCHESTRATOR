> **ARCHIVED**: This specification described a 6-phase roadmap for hardening the launcher system. Implementation status as of October 2025:
> - **Phase 1 (Manifest Hygiene)**: ✅ COMPLETE - Full validator at `nodes/backend/launcher/validator.py` with comprehensive tests at `nodes/tests/test_launcher_validator.py`; CLI validates manifests before all lifecycle operations (nodes/scripts/launch_services.py:1077-1080)
> - **Phase 2 (Lifecycle Engine)**: ❌ NOT IMPLEMENTED - No worker pools, no restart policies with backoff/jitter, no dependency cascades
> - **Phase 3 (Health & Telemetry)**: ⚠️ PARTIAL - Metrics/counters exist in state snapshots and accessible via `launcher metrics` CLI; HTTP status endpoint and JSONL logging not implemented
> - **Phase 4 (Environment Safety)**: ❌ NOT IMPLEMENTED - No allow_env enforcement, no secrets broker integration
> - **Phase 5 (Observability)**: ⚠️ PARTIAL - CLI tools (`logs`, `env`, `state`, `metrics`) exist; MCP tools not implemented
> - **Phase 6 (Resilience Testing)**: ❌ NOT IMPLEMENTED
>
> The launcher operates with production-ready manifest validation and basic CLI observability but lacks advanced features like automatic restart policies, HTTP telemetry endpoints, and environment safety guards. See `nodes/SPEC-LAUNCHER.md` for current launcher architecture.

# Launcher Hardening Specification

## Purpose

Deliver an enterprise-grade launcher that can withstand misconfiguration, service failures, and operational churn without manual babysitting. The goals are to ensure deterministic orchestration across Docker, local processes, and MCP servers; surface actionable diagnostics; and block risky states before they reach production.

## Scope

- `nodes/backend/launcher/*` (config, supervisor, adapters, health, env).
- Launcher CLI (`nodes/scripts/launch_services.py`) and MCP bridge.
- Related guardrails in root scripts (`scripts/check_banned_words.py`) when they intersect with launcher behaviour.
- CI integration points that rely on launcher start/stop routines.

Modules outside the launcher (base/browser/files/etc.) only change when required for cross-module orchestration (for example, documenting new environment variables).

## Hardening Pillars & Tasks

1. **Manifest Hygiene**
   - Add a validator that rejects unknown service IDs, missing dependencies, duplicate compose references, conflicting execution modes, and env collisions before runtime.
   - Surface validator output via CLI (`launcher validate`), MCP tool, and CI job.
   - Provide quick-fix guidance in errors (file/line hints when possible).
   - Status: ✅ **COMPLETE** - The CLI validator (`nodes/backend/launcher/validator.py`) checks Docker Compose structure, service naming, dependency wiring, execution mode selection, and security tags; `nodes/tests/test_launcher_validator.py` provides comprehensive test coverage.
   - The launcher CLI (`nodes/scripts/launch_services.py`) validates manifests before executing `start`, `stop`, and `restart` commands (lines 1077-1080), blocking operations with exit code 1 if validation fails.

2. **Deterministic Lifecycle Management**
   - Status: ❌ **NOT IMPLEMENTED**
   - Move start/stop/health work into dedicated worker pools (thread/process) so the CLI never blocks and operations can be throttled.
   - Implement restart policies (`never`, `on-failure`, `always`) with exponential backoff, jitter, and max retry counters.
   - Cascade stop or mark dependents degraded when a required service fails repeatedly.

3. **Health & Telemetry**
   - Status: ⚠️ **PARTIALLY IMPLEMENTED**
   - ✅ State snapshots include restart counters, health metrics, and probe latency (nodes/backend/launcher/supervisor.py ServiceRuntime fields)
   - ✅ CLI `metrics` command exports telemetry as JSON (nodes/scripts/launch_services.py:1051-1060)
   - ❌ No HTTP status endpoint at `localhost:5055/launcher/status` for dashboards and CI probes
   - ❌ No structured JSONL logging with correlation IDs

4. **Environment & Secret Safety**
   - Status: ❌ **NOT IMPLEMENTED**
   - Enforce allow-lists for environment inheritance (explicit `allow_env` flag) to prevent leaking host secrets.
   - Fail fast when required env vars are missing (document the required keys per service in manifests).
   - Integrate secrets broker clients where applicable so tokens never live in plaintext manifests.

5. **Observability Hooks**
   - Status: ⚠️ **PARTIALLY IMPLEMENTED**
   - ✅ CLI subcommands exist: `logs` (nodes/scripts/launch_services.py:947-981), `env` (983-1022), `state` (1024-1049), `metrics` (1051-1060)
   - ❌ No MCP tools (`launcher_profiles`, `launcher_status`, `launcher_tail`) for automation integration

6. **Resilience Testing**
   - Status: ❌ **NOT IMPLEMENTED**
   - Add integration tests that simulate service failures (force stop containers, kill local processes) and assert restart logic works.
   - Include load tests for concurrent start/stop sequences to ensure no race conditions.
   - Wire a CI smoke profile (`launcher start --profile smoke`) that boots critical services and runs a basic health check suite.

## Phased Roadmap

| Phase | Focus | Deliverables |
| ----- | ----- | ------------ |
| 1 | Manifest hygiene | CLI validator, unit tests, documentation, CI hook |
| 2 | Lifecycle engine | Worker pool integration, restart policies, dependency error cascades |
| 3 | Telemetry | HTTP status endpoint, enhanced logging, state enrichment |
| 4 | Env safety | Env allow-lists, required var checks, secrets broker integration guidance |
| 5 | Observability | MCP tools, CLI log/metrics commands, documentation |
| 6 | Resilience testing | Failure simulations, load tests, smoke profile |

Each phase should land on `main` with passing module tests and updated documentation. Phases may overlap when workstreams are independent (for example, telemetry and env safety), but manifest hygiene must land first to keep future changes guardrailed.

## Success Criteria

- Launcher CLI refuses to start when manifests or env overrides are invalid, emitting precise guidance.
- Services restart according to policy with capped retries and report failures without deadlocking the supervisor.
- Monitoring systems can query JSON state and tail logs without scraping files manually.
- Environment propagation is explicit and auditable; secrets never live in plain text manifests.
- Integration tests cover the critical failure modes (dependency crash, hung health probe, command exit, docker kill) and pass repeatably in CI.

## Documentation & Training

- Update `nodes/SPEC-LAUNCHER.md` as phases complete.
- Add launcher hardening playbook entries to `docs/Next-Steps.md` and onboarding materials.
- Provide example manifest patterns (healthy vs. rejected) in `nodes/tests/fixtures/launcher_manifests/` for knowledge sharing.

## Open Questions

- How far should the validator go in parsing Docker Compose (full schema vs. selective checks)? – Validate the entire Compose document for structural integrity while deferring deep parsing to later stages that need specific sections.
- Do we need policy hooks (YAML lint) for service naming, tagging, and security classification? – Yes; bake lint hooks into the validator so submissions fail fast when policy is violated.
- Should restart policy configuration live per service or per profile override? – Both; define defaults on the service and allow profile overrides to tighten settings when environments demand it.

Captured decisions and answers belong in this spec to keep the roadmap aligned with reality.
