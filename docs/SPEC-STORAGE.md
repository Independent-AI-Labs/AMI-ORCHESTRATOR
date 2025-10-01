# SPEC – Storage Configuration Management

## Goals
- Provide a single source of truth for storage backends (Postgres, Dgraph, Vault, etc.) used by DataOps models and services.
- Define validation and health-check tooling that guarantees configurations are correct before UnifiedCRUD and downstream services rely on them.
- Expose configuration inspection and validation endpoints via the DataOps MCP server for real-time diagnostics.

## Foundations

### Configuration Files
- `base/config/storage-config.yaml` holds environment-agnostic defaults for all named storage backends (`postgres`, `dgraph`, `vault`, …).
- Values support `${ENV_VAR:-default}` substitution; module setup scripts must populate required env vars via `.env` before validation.
- `model_defaults.default_storages` defines the order UnifiedCRUD will try when a model omits `storage_configs`. Every entry must be safe for production traffic; no hidden degradations are permitted.

### Runtime Objects
- `StorageConfigFactory.from_yaml(name)` resolves a named entry, merges it with overrides, and returns a `StorageConfig` instance.
- `StorageModel.Meta.storage_configs` (list or dict of `StorageConfig`) dictates the backend mix for that model. Ordering matters: the first config is treated as primary by UnifiedCRUD’s `PRIMARY_FIRST` strategy.
- `UnifiedCRUD` and `DAOFactory` cache constructed DAOs per `(model, storage_name)` tuple and call `dao.connect()` lazily; this is where connection validation occurs today.

## Design Requirements

### 1. Configuration Registry API
- Implement a registry component (e.g., `base/backend/dataops/storage/registry.py`) that:
  - Loads all configs from YAML and caches them.
  - Provides typed accessors (`get_config(name)`, `list_configs()`).
  - Tracks which models use which configs for observability.

### 2. Validation & Health Checks
- Add a `StorageValidator` utility responsible for:
  - Attempting a connection to each configured backend (per storage type) using DAO `test_connection()` hooks.
  - Verifying required fields (host, port, credentials) are present before attempting connection.
  - Producing a structured report `{name, storage_type, status, details}` for all configured backends.
- Integrate the validator into:
  - Module setup scripts (e.g., invoke `python base/scripts/check_storage.py` during CI) so failures surface early.
  - `agent.sh` (optional but recommended) to warn developers when required services are down.

### 3. FastMCP Server Integration
- Extend the DataOps MCP server (FastMCP) with new tools so clients can:
  - call `storage_list` to enumerate available storage configs (sanitised: no credentials in the payload).
  - call `storage_validate` to trigger validation and return the report from `StorageValidator`.
  - call `storage_models` to inspect which models rely on each storage backend (impact analysis).
- Guard these tools behind the existing MCP auth controls to prevent leaking infrastructure metadata.

### 4. Observability & Telemetry
- Emit structured logs and metrics when storage validation fails or when UnifiedCRUD falls back to secondary storage due to a primary failure.
- Optionally wire Prometheus gauges (e.g., `storage_connection_ok{name="postgres"}`) so Ops dashboards highlight downtime.

### 5. Developer Workflow
- Document required environment variables and test commands:
  - `python base/scripts/check_storage.py` (new) – runs validator for all known storages.
  - `python base/scripts/check_storage.py --model user` – restrict validation to storages used by a specific model.
  - `ami mcp storage validate` – CLI entry point hitting the MCP tool.
- Add guidance to `AGENTS.md` covering:
  - How to add a new storage backend (YAML entry + DAO registration + validation hook).
  - How to run health checks locally before committing.

## Open Questions
- Should we cache successful validation results to avoid repeatedly hammering backends during local development, or always run a fresh check?
- Do we need per-environment overrides (e.g., staging vs production) baked into the registry, or should orchestrators supply different YAML files?
- How should we handle secret rotation for Vault/Database credentials—trigger validation automatically, or expect the operator to run the CLI command post-rotation?

## Next Steps
1. Implement the `StorageValidator` and CLI script; wire into base CI.
2. Add MCP endpoints with appropriate authentication/authorisation guards.
3. Update developer docs (`AGENTS.md`, module READMEs) with the new workflow and troubleshooting steps.

## 2025-10 Updates

- **Metadata-aware schemata** – the Dgraph DAO now feeds full `ModelMetadata` into schema creation so index declarations in `Meta.indexes` are honoured automatically.
- **PgVector integration rewritten** – vector-backed models persist through the PostgreSQL DAO, storing structured columns plus a dedicated `vector` field. Embedding dimensions are derived from the stored payload and hnsw indexes are created only after the column receives real data.
- **Redis as cache-only** – the Redis DAO refuses zero/negative TTLs. All entries must provide an explicit expiration, guaranteeing we never treat Redis as durable storage.
- **OpenBao listing** – Vault/OpenBao storage enumerates secrets via the native API rather than maintaining an in-repo `__index__` document, eliminating race conditions.
- **Local JSON storage profile removed** – the file-backed DAO and `StorageType.FILE` profile have been deleted; UnifiedCRUD now stops at Postgres (primary), Dgraph (metadata), and Vault (secrets).
