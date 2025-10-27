# SPEC – Authentication Platform

> **Implementation Status**: Phase 1 (CRUD Foundation) is **complete**. Phases 2-4 (HTTP Surface, Adapter Integration, Advanced Features) are **planned but not yet implemented**. The UX layer currently operates in **dev/local mode** with file-based credential stores until the HTTP surface is ready.

## Scope
This specification defines the target architecture for authentication across AMI Orchestrator. It replaces the ad-hoc checklist in `TODO-AUTH.md` with a cohesive blueprint that covers the storage mix (Postgres, Dgraph, OpenBao), service boundaries in the `base` backend, and the integration contract consumed by `ux` surfaces (NextAuth adapter, CMS account manager, extensions, CLI tooling).

The scope includes:
- How user and provider records are modelled and persisted.
- Secrets-handling responsibilities between the DataOps layer and the secrets broker.
- Session issuance/validation for Next.js surfaces via a custom NextAuth adapter.
- Required APIs (HTTP + MCP) and environment variables.
- Timeline considerations for hardening the production-grade stack now that the in-memory helper has been retired.

## System Overview
```
+-------------------+        HTTPS        +--------------------------------+
| UX Surfaces       | <----------------> | Auth Gateway (NextAuth Adapter) |
| (CMS, extensions) |                    |  - Next.js route handlers        |
+-------------------+                    |  - Custom DataOps adapter       |
          |                              +--------------------------------+
          | REST/GraphQL (planned)                  |
          v                                         |
+----------------------+   gRPC/HTTP (internal)   +-----------------------------+
| DataOps Auth Service | <----------------------> | Secrets Broker (OpenBao)    |
|  - AuthService API   |                         |  - OpenBao DAO              |
|  - UnifiedCRUD layer |                         |  - Token material storage   |
+----------------------+                         +-----------------------------+
          |                                                     |
          | UnifiedCRUD                                         |
          v                                                     v
+------------------+   +------------------+     +------------------------------+
| Postgres (primary|   | Dgraph (metadata)|     | OpenBao (secret material)    |
| user/provider    |   | identity graph)  |     | via Vault-compatible API     |
+------------------+   +------------------+     +------------------------------+
```

### Key Components
- **NextAuth Adapter (`ux/auth`)** – *Current:* Dev mode with local JSON credential stores (`ux/auth/src/dataops-client.ts`). *Target:* Translate Auth.js lifecycle events into DataOps CRUD calls via HTTP.
- **DataOps Auth Service (`base/backend/opsec/auth`)** – *Implemented:* Business logic for user/provider lifecycle, token refresh, revocation via `AuthService` class and `repository.py`. *Missing:* HTTP endpoints and MCP tools (Phase 2).
- **UnifiedCRUD Layer (`base/backend/dataops/services/unified_crud.py`)** – Persists models across the configured storage mix without leaking DAO specifics to callers. Follows [SPEC – DataOps Data Access Pattern](./SPEC-DATAOPS-DATA-ACCESS.md).
- **Secrets Broker (`base/backend/services/secrets_broker/app.py`)** – ✅ **Implemented** FastAPI app with `/v1/secrets/{ensure,retrieve,delete}` endpoints. Proxies to OpenBao via Vault DAO.
- **Storage Registry (`base/config/storage-config.yaml`)** – Central definition for `postgres`, `dgraph`, and `openbao` configurations. See [SPEC – Storage Configuration Management](./SPEC-STORAGE.md) for validation tooling.

## Storage Mix
| Concern | Backend | Rationale |
| --- | --- | --- |
| Canonical user/provider records, sessions, tenant membership | **Postgres (`postgres`)** | Transactional store, primary key/foreign key enforcement, reliable durability. |
| Relationship metadata, traversal (user ↔ provider ↔ tenant), audit trails | **Dgraph (`dgraph`)** | Graph-first queries for relationship lookups and lineage. |
| Provider secrets (OAuth client secret, refresh tokens, API keys) | **OpenBao (`openbao`)** | Dedicated secrets engine with access policies and rotation support via Vault-compatible API. |
| Ephemeral caches (auth flows, rate limits) | **In-memory / runtime cache** | Provided via `AuthService` in-process caches; no Redis tier is required. |

`AuthProvider` models declare `Meta.storage_configs = ["postgres", "dgraph", "openbao"]` in that order (`base/backend/dataops/models/user.py:97-100`) so vault-backed fields never touch disk. `User` models rely on `["postgres", "dgraph"]` and avoid OpenBao altogether. There is no implicit disk persistence: opting into any additional storage (for example a JSON file for offline demos) requires defining a custom `StorageConfig` and wiring it deliberately per deployment.

## Storage Failure Handling
- UnifiedCRUD surfaces storage failures immediately. Operators must restore the affected backing service rather than relying on hidden degradations.
- Optional storage backends can be added explicitly for lab environments, but they must be documented and toggled via configuration rather than assumed in code.

## Data Flows

> **Note**: Flows below describe the **target architecture**. Currently, only the backend CRUD layer is implemented. UX surfaces use local dev mode until Phase 2 HTTP endpoints are ready.

### Provider Catalogue & CRUD
1. **Target:** UX surfaces request `/auth/providers/catalog` from the DataOps auth service.
2. **Target:** Service composes static templates (`base/backend/opsec/oauth/oauth_config.py`) with tenant-specific overrides stored in Postgres.
3. **Implemented:** `AuthService.create_auth_provider` validates the payload, persists non-secret fields via UnifiedCRUD (`base/backend/opsec/auth/repository.py`), and hands secret fields to the secrets broker.
4. **Implemented:** Dgraph receives the same provider node via UnifiedCRUD multi-storage sync.

### Sign-In Flow
1. **Current:** NextAuth runs in dev mode (`ux/auth/src/server.ts:createDevAuth`) with hardcoded guest sessions. **Target:** Custom adapter calls DataOps HTTP endpoints.
2. **Implemented:** `AuthService.authenticate_user` (`auth_service.py:34-84`) ensures `User` exists, fetches/refreshes provider tokens, persists via repository.
3. **Planned:** Session documents in Postgres/Dgraph. **Current:** Sessions live in NextAuth JWT/cookies only.
4. **Planned:** Route guards fetch session via `/auth/session`. **Current:** Dev mode returns static guest session.

### Secrets Handling
- ✅ **Implemented:** Auth service never stores raw secrets on the model. Fields typed as `SecretStr` (e.g., `AuthProvider.api_key` in `user.py:60`) delegate to the Vault DAO.
- ✅ **Implemented:** Secrets broker exposes `POST /v1/secrets/ensure`, `POST /v1/secrets/retrieve`, `DELETE /v1/secrets/{vault_reference}` (`secrets_broker/app.py:86-131`) and proxies to OpenBao. Tokens/mounts from `SECRETS_BROKER_*` env vars.
- ✅ **Implemented:** Callers hold only vault references (e.g., `vault://providers/<id>/client_secret`) after persistence via `VaultFieldPointer`.

### Session Enforcement & Security Context
- Every UnifiedCRUD call receives a `SecurityContext` derived either from NextAuth (end-user flows) or system credentials (administrative flows).
- CMS route handlers use `withSession` to populate the context before invoking DataOps APIs; CLI tools and automation bots use `DATAOPS_INTERNAL_TOKEN` to hit the auth service directly.

## API Surface

### HTTP (FastAPI, planned path `/auth`)

> **Status**: ❌ **Not Implemented** – No FastAPI router exists for auth endpoints. Backend logic is ready via `AuthService` class.

| Method | Path | Description | Status |
| --- | --- | --- | --- |
| `GET` | `/auth/providers/catalog` | List available provider types + field schema, including tenant overrides. | ❌ Planned |
| `POST` | `/auth/providers` | Create or update a provider configuration for a user/tenant. Secrets resolved via Vault. | ❌ Planned |
| `DELETE` | `/auth/providers/{provider_id}` | Revoke a provider and delete secret references. | ❌ Planned |
| `POST` | `/auth/providers/{provider_id}/refresh` | Force token refresh using adapter registry. | ⚠️ Backend method exists but returns `False` (TODO at `auth_service.py:203`) |
| `GET` | `/auth/users/{uid}` | Fetch user profile + linked providers. | ❌ Planned |
| `POST` | `/auth/sessions` | Exchange credentials/OAuth result for a session (used by NextAuth adapter). | ❌ Planned |
| `GET` | `/auth/sessions/{session_id}` | Resolve session for guard middleware. | ❌ Planned |
| `POST` | `/auth/sessions/{session_id}/revoke` | Terminate active session (logout). | ❌ Planned |

All endpoints require bearer authentication (`DATAOPS_INTERNAL_TOKEN`) when called by trusted services; end-user flows use signed NextAuth cookies and call adapter helpers that forward to the DataOps gateway.

### MCP Tools (DataOps Server)

> **Status**: ❌ **Not Implemented** – No MCP tools defined for auth operations yet.

| Tool | Purpose | Status |
| --- | --- | --- |
| `auth/providers.list` | Inspect provider catalogue (no secrets). | ❌ Planned |
| `auth/providers.validate` | Validate a provider payload before committing changes. | ❌ Planned |
| `auth/storage.validate` | Run storage validator scoped to auth-related configs (delegates to [SPEC-STORAGE](./SPEC-STORAGE.md)). | ❌ Planned |
| `auth/sessions.list` | Operational metadata for admins (active sessions per tenant). | ❌ Planned |

## Environment Variables
| Variable | Description | Default |
| --- | --- | --- |
| `DATAOPS_AUTH_URL` | Base URL for the DataOps auth service. UX adapter uses this when available. | `http://127.0.0.1:9001/auth` (recommended) |
| `DATAOPS_INTERNAL_TOKEN` | Shared bearer token for trusted service-to-service calls (NextAuth adapter, CLI runners). | _none_ (must be generated per environment) |
| `NEXT_PUBLIC_DATAOPS_AUTH_URL` | Public URL exposed to browser clients (mirrors `DATAOPS_AUTH_URL`). | Derived from `DATAOPS_AUTH_URL` |
| `SECRETS_BROKER_URL` | Endpoint for the secrets broker REST API. | `http://127.0.0.1:8700` |
| `SECRETS_BROKER_INTERNAL_TOKEN` / `SECRETS_BROKER_TOKEN` | Shared bearer token for secrets broker access (defaults to `DATAOPS_INTERNAL_TOKEN`). | _none_ |
| `SECRETS_BROKER_OPENBAO_ADDR` | OpenBao base URL (`scheme://host:port`). | `http://127.0.0.1:8200` |
| `SECRETS_BROKER_OPENBAO_TOKEN` | Token presented by the broker to OpenBao. | `openbao-root` in dev mode |
| `SECRETS_BROKER_OPENBAO_MOUNT` | Secrets engine mount path. | `secret` |
| `SECRETS_BROKER_OPENBAO_NAMESPACE` | Optional namespace for multi-tenant OpenBao setups. | unset |

Providers that need third-party credentials also require provider-specific env vars (e.g., `GOOGLE_CLIENT_ID`, `GITHUB_CLIENT_SECRET`). Keep those in the module `.env.local` files and never commit them.

## Operational Guarantees
- UnifiedCRUD iterates storages in declaration order and stops on the first success. Errors bubble to callers so infrastructure issues are discovered immediately.
- Local filesystem persistence is no longer bundled by default. Teams that want an offline or demo mode must create a dedicated `StorageConfig` and document its operational impact.
- Auth persistence runs exclusively through `base/backend/opsec/auth/repository.py`; callers must use UnifiedCRUD so invariants stay consistent across storages.

## Implementation Phases

### Phase 1: CRUD Foundation ✅ **COMPLETE**
- ✅ `AuthService` persists via `base/backend/opsec/auth/repository.py`, backed by UnifiedCRUD
- ✅ `User` / `AuthProvider` models declare correct storage configs (`["postgres", "dgraph"]` and `["postgres", "dgraph", "openbao"]` respectively)
- ✅ UnifiedCRUD automatically populates `SecurityContext` metadata
- ✅ Secrets broker implemented with `/v1/secrets/*` endpoints
- ⚠️ **Outstanding:** Token refresh returns stub (`auth_service.py:203`)

**Files:**
- `base/backend/opsec/auth/auth_service.py` (AuthService class)
- `base/backend/opsec/auth/repository.py` (CRUD helpers)
- `base/backend/dataops/models/user.py` (User, AuthProvider models)
- `base/backend/services/secrets_broker/app.py` (Secrets broker FastAPI app)

### Phase 2: Auth Service HTTP Surface ❌ **NOT STARTED**
- ❌ Create FastAPI router for `/auth` endpoints
- ❌ Implement bearer-auth middleware using `DATAOPS_INTERNAL_TOKEN`
- ❌ Wire `AuthService` methods to HTTP handlers
- ❌ Add storage validation to module setup

**Blockers:** None – backend logic ready, just needs HTTP wrapper

### Phase 3: NextAuth Adapter Integration ❌ **NOT STARTED**
- ❌ Replace dev auth mode in `ux/auth/src/server.ts`
- ❌ Update `DataOpsClient` to call Phase 2 HTTP endpoints instead of local files
- ❌ Propagate DataOps validation errors to CMS hint system

**Blockers:** Requires Phase 2 completion

### Phase 4: Advanced Providers & Compliance ❌ **NOT STARTED**
- ❌ Provider schema API for tenant-defined OAuth configs
- ❌ Provider auditing hooks (security audit trail)
- ❌ MFA flows
- ❌ CLI integration for auth operations

## Open Questions & Risks
- **Tenant bootstrap** – Determine how the first admin account is provisioned (manual secret vs. CLI). Consider seeding via `DATAOPS_ADMIN_EMAIL` + `DATAOPS_BOOTSTRAP_TOKEN` env vars.
- **Session storage** – Decide whether to persist sessions in Postgres exclusively or allow stateless JWT sessions for public surfaces.
- **Secrets rotation** – Define rotation playbooks (triggered via MCP `auth/providers.rotate` tool?) to re-encrypt provider secrets without downtime.
- **Compliance mapping** – Align audit logs with ISMS requirements (GDPR data export, right-to-be-forgotten) once CRUD persistence lands.

## Current Dev Mode Behavior

Until Phase 2 HTTP endpoints are implemented, the system runs in **dev/local mode**:

- **UX Layer** (`ux/auth/src/server.ts`): Returns hardcoded guest sessions via `createDevAuth()` when `AMI_AUTH_FORCE_DEV=1` or outside Next.js runtime
- **Credential Storage** (`ux/auth/src/dataops-client.ts`): Falls back to local JSON files when `DATAOPS_AUTH_URL` is unset
- **Provider Catalog**: Loaded from local file via `LocalProviderCatalogStore` if `DATAOPS_AUTH_URL` is unavailable
- **Backend CRUD**: Fully operational for programmatic use (e.g., CLI tools, automation scripts) via `AuthService` class

This mode allows frontend development to proceed while Phase 2 HTTP surface is built.

## References
- [SPEC – DataOps Data Access Pattern](./SPEC-DATAOPS-DATA-ACCESS.md)
- [SPEC – Storage Configuration Management](./SPEC-STORAGE.md)
- **Backend Implementation:**
  - `base/backend/opsec/auth/auth_service.py` (Core business logic)
  - `base/backend/opsec/auth/repository.py` (UnifiedCRUD persistence)
  - `base/backend/dataops/models/user.py` (User, AuthProvider models)
  - `base/backend/services/secrets_broker/app.py` (Secrets broker FastAPI)
  - `base/backend/opsec/oauth/oauth_config.py` (Provider templates)
- **Frontend Implementation:**
  - `ux/auth/src/server.ts` (NextAuth wrapper, dev mode)
  - `ux/auth/src/dataops-client.ts` (DataOps client with local fallback)
  - `ux/auth/src/config.ts` (Environment configuration)
