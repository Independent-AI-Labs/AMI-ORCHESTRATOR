# SPEC – Storage Configuration Management

**Status**: ✅ Implemented (Oct 2025)
**Location**: `base/backend/dataops/storage/`

## Goals
- Provide a single source of truth for storage backends (Postgres, Dgraph, OpenBao, Redis, etc.) used by DataOps models and services.
- Define validation and health-check tooling that guarantees configurations are correct before UnifiedCRUD and downstream services rely on them.
- Expose configuration inspection and validation endpoints via the DataOps MCP server for real-time diagnostics.

## Foundations

### Configuration Files
- `base/config/storage-config.yaml` holds environment-agnostic defaults for all named storage backends (`postgres`, `pgvector`, `dgraph`, `redis`, `openbao`, `mongodb`, `prometheus`).
- Values support `${ENV_VAR:-default}` substitution; module setup scripts populate required env vars via `.env`.
- `model_defaults.default_storages` defines the order UnifiedCRUD will try when a model omits `storage_configs` (currently: `[dgraph]` as ground truth).

### Runtime Objects
- **`StorageConfigFactory.from_yaml(name)`** (`base/backend/dataops/models/storage_config_factory.py`) resolves a named entry from YAML and returns a typed `StorageConfig` instance.
- **`StorageModel.Meta.storage_configs`** (list or dict of `StorageConfig`) dictates the backend mix for that model. Ordering matters: the first config is primary in UnifiedCRUD's `PRIMARY_FIRST` strategy.
- **`UnifiedCRUD`** (`base/backend/dataops/services/unified_crud.py`) and **`DAOFactory`** cache constructed DAOs per `(model, storage_name)` tuple and call `dao.connect()` lazily.

## Implementation

### 1. Configuration Registry API ✅
**Location**: `base/backend/dataops/storage/registry.py`

- **`StorageRegistry`** class provides:
  - `list_configs()` – returns all storage configs from YAML (cached)
  - `get_config(name)` – retrieves a single config by name
  - `list_config_summaries()` – returns sanitized summaries (credentials redacted)
  - `get_model_usage()` – returns which models use which storages
  - `get_config_usage_index()` – reverse index: storage name → list of models
- Auto-discovers all models via `ModelRegistry.auto_register_common_models()` and walks `StorageModel` subclasses.
- Sanitizes sensitive fields (`password`, `secret`, `token`, `key`, `credential`) in output.

### 2. Validation & Health Checks ✅
**Location**: `base/backend/dataops/storage/validator.py`

- **`StorageValidator`** class provides:
  - `validate_all(names)` – validates specified or all storage backends
  - `validate_for_model(model_name)` – validates only storages used by a specific model
  - Returns `StorageValidationResult` with `{name, storage_type, status, details, missing_fields, models}`
- Validates required fields per storage type before attempting connections.
- Uses `dao.connect()` and `dao.test_connection()` to verify backend connectivity.
- **CLI tool**: `base/scripts/check_storage.py`
  - Usage: `./scripts/ami-run.sh base/scripts/check_storage.py [--storage NAME] [--model NAME] [--json]`
  - Returns exit code 0 (all OK) or 1 (failures detected)
  - Integrated into CI/testing workflows

### 3. FastMCP Server Integration ✅
**Location**: `base/backend/mcp/dataops/tools/dataops_storage_tools.py`

Three MCP tools registered in `DataOpsFastMCPServer`:
- **`dataops_storage_list`** – lists all storage configs (sanitized, no credentials)
- **`dataops_storage_validate`** – validates connectivity (accepts `storage_names` or `model` parameter)
- **`dataops_storage_models`** – shows which models depend on each storage backend

Access via MCP client or through `base/scripts/run_dataops_fastmcp.py`.

### 4. Observability & Telemetry 🔄
**Status**: Partial

- Structured logging via `loguru` when validation fails
- UnifiedCRUD logs storage operation results
- **TODO**: Prometheus metrics integration (`storage_connection_ok{name="..."}`)
- **TODO**: Telemetry on fallback scenarios (primary → secondary storage)

### 5. Developer Workflow ✅

**CLI Commands:**
```bash
# Validate all storages
./scripts/ami-run.sh base/scripts/check_storage.py

# Validate specific storage(s)
./scripts/ami-run.sh base/scripts/check_storage.py --storage postgres --storage redis

# Validate storages for a specific model
./scripts/ami-run.sh base/scripts/check_storage.py --model User

# JSON output
./scripts/ami-run.sh base/scripts/check_storage.py --json
```

**Via MCP:**
MCP clients can call `dataops_storage_validate` tool directly. The MCP server runs via:
```bash
./scripts/ami-run.sh base/scripts/run_dataops_fastmcp.py --transport stdio
```

**Adding a New Storage Backend:**
1. Add entry to `base/config/storage-config.yaml` with type, host, port, credentials
2. Implement DAO in `base/backend/dataops/implementations/<type>/` extending `BaseDAO`
3. Register DAO in `DAOFactory.create()` (`base/backend/dataops/core/dao.py`)
4. Add required fields to `_STORAGE_REQUIRED_FIELDS` in `validator.py` if needed
5. Run `check_storage.py` to verify connectivity

## Current Status & Next Steps

### Completed ✅
- ✅ Configuration registry with YAML loading and caching
- ✅ Storage validator with field and connectivity checks
- ✅ CLI tool for health checks (`check_storage.py`)
- ✅ MCP server integration with three storage tools
- ✅ Model-to-storage usage tracking and reverse indexing
- ✅ Credential sanitization in API responses

### Remaining Work 🔄
- 🔄 **Prometheus metrics** – add gauges for storage health (`storage_connection_ok{name="..."}`)
- 🔄 **Telemetry** – emit metrics when UnifiedCRUD falls back to secondary storage
- 🔄 **Caching** – optional validation result caching to avoid hammering backends during dev
- 🔄 **Per-environment configs** – mechanism for staging/production YAML overrides

### Open Design Questions
- **Secret rotation**: Should validation auto-trigger on Vault/DB credential rotation, or require manual `check_storage.py` invocation?
- **Validation caching**: Cache successful checks with TTL, or always run fresh? (Performance vs accuracy trade-off)
- **Environment overrides**: Bake into registry, or expect orchestrators to swap YAML files?

## Recent Updates (Oct 2025)

### Storage Backend Improvements
- **Metadata-aware schemata** – Dgraph DAO feeds full `ModelMetadata` into schema creation; index declarations in `Meta.indexes` are honored automatically.
- **PgVector integration** – Vector-backed models persist through PostgreSQL DAO with dedicated `vector` field. Embedding dimensions are derived from payload; HNSW indexes created dynamically after data insertion.
- **Redis cache-only** – Redis DAO enforces non-zero TTLs. All entries must have explicit expiration, preventing accidental use as durable storage.
- **OpenBao enumeration** – Vault/OpenBao storage enumerates secrets via native API rather than maintaining an `__index__` document, eliminating race conditions.
- **FILE storage unimplemented** – `StorageType.FILE` enum exists but is marked unimplemented in `dao.py:283`; no FileDAO implementation or YAML configuration. Implemented backends: Postgres (relational), PgVector (vector), Dgraph (graph), Redis (in-memory cache), OpenBao (secrets), REST (API-based storage). Unimplemented types: FILE, MongoDB (document), Prometheus (timeseries).

### Storage Management Features
- **Configuration registry** – Centralized YAML-based config with environment variable substitution
- **Validation framework** – Automated health checks with missing field detection and connectivity tests
- **MCP integration** – Storage inspection and validation tools exposed via DataOps MCP server
- **CLI tooling** – `check_storage.py` for CI/CD and local development validation

### Type Safety & Quality
- All storage types defined in `StorageType` enum (no magic strings)
- Required fields validated per storage type before connection attempts
- Credential sanitization in all API responses
- Structured validation results with actionable error messages
