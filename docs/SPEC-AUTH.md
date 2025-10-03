# SPEC – Authentication Platform

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
- **NextAuth Adapter (`ux/auth`)** – Translates Auth.js lifecycle events (`createUser`, `getSession`, provider linkages) into DataOps CRUD calls and proxies session validation to the backend.
- **DataOps Auth Service (`base/backend/opsec/auth`)** – Owns business logic for user/provider lifecycle, token refresh, revocation, and security context propagation. Provides HTTP endpoints and MCP tools.
- **UnifiedCRUD Layer (`base/backend/dataops/services/unified_crud.py`)** – Persists models across the configured storage mix without leaking DAO specifics to callers. Follows [SPEC – DataOps Data Access Pattern](./SPEC-DATAOPS-DATA-ACCESS.md).
- **Secrets Broker (`base/backend/services/secrets_broker`)** – REST surface that marshals secrets to OpenBao via the Vault DAO. Auth service uses the broker whenever secret-bearing fields are created/updated.
- **Storage Registry (`base/config/storage-config.yaml`)** – Central definition for `postgres`, `dgraph`, and `vault` configurations. See [SPEC – Storage Configuration Management](./SPEC-STORAGE.md) for validation tooling.

## Storage Mix
| Concern | Backend | Rationale |
| --- | --- | --- |
| Canonical user/provider records, sessions, tenant membership | **Postgres (`postgres`)** | Transactional store, primary key/foreign key enforcement, reliable durability. |
| Relationship metadata, traversal (user ↔ provider ↔ tenant), audit trails | **Dgraph (`dgraph`)** | Graph-first queries for relationship lookups and lineage. |
| Provider secrets (OAuth client secret, refresh tokens, API keys) | **OpenBao via Vault DAO (`vault`)** | Dedicated secrets engine with access policies and rotation support. |
| Ephemeral caches (auth flows, rate limits) | **In-memory / runtime cache** | Provided via `AuthService` in-process caches; no Redis tier is required. |

`AuthProvider` models declare `Meta.storage_configs = ["postgres", "dgraph", "vault"]` in that order so vault-backed fields never touch disk. `User` models rely on `["postgres", "dgraph"]` and avoid OpenBao altogether. There is no implicit disk persistence: opting into any additional storage (for example a JSON file for offline demos) requires defining a custom `StorageConfig` and wiring it deliberately per deployment.

## Storage Failure Handling
- UnifiedCRUD surfaces storage failures immediately. Operators must restore the affected backing service rather than relying on hidden degradations.
- Optional storage backends can be added explicitly for lab environments, but they must be documented and toggled via configuration rather than assumed in code.

## Data Flows
### Provider Catalogue & CRUD
1. UX surfaces request `/auth/providers/catalog` from the DataOps auth service.
2. Service composes static templates (`oauth_config.py`) with tenant-specific overrides stored in Postgres.
3. When creating/updating providers, `AuthService` validates the payload, persists non-secret fields via UnifiedCRUD, and hands secret fields (`client_secret`, `api_key`, etc.) to the secrets broker (Vault DAO).
4. Dgraph receives the same provider node to keep graph queries (e.g., “list providers for tenant X”) fast.

### Sign-In Flow
1. NextAuth credential/OAuth flow hits the custom adapter.
2. Adapter calls `AuthService.authenticate_user`, which ensures the `User` record exists, fetches/refreshes provider tokens, and persists the latest state.
3. Session documents are created in Postgres (`Session` model) and mirrored to Dgraph for audit. Session secrets (if JWT mode) live entirely in NextAuth; no server-side storage required.
4. Adapter returns the session payload to NextAuth, which issues cookies/JWTs. Route guards fetch the session via `/auth/session` (served from DataOps).

### Secrets Handling
- Auth service never stores raw secrets on the model. Fields typed as `SecretStr` (e.g., `AuthProvider.api_key`) delegate to the Vault DAO.
- Secrets broker exposes `POST /v1/secrets/write`, `GET /v1/secrets/read`, `DELETE /v1/secrets/remove` and proxies everything to OpenBao. Tokens and mounts come from `SECRETS_BROKER_*` env vars.
- Callers hold only the secret reference (e.g., `vault://providers/<id>/client_secret`) after persistence.

### Session Enforcement & Security Context
- Every UnifiedCRUD call receives a `SecurityContext` derived either from NextAuth (end-user flows) or system credentials (administrative flows).
- CMS route handlers use `withSession` to populate the context before invoking DataOps APIs; CLI tools and automation bots use `DATAOPS_INTERNAL_TOKEN` to hit the auth service directly.

## API Surface
### HTTP (FastAPI, planned path `/auth`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/auth/providers/catalog` | List available provider types + field schema, including tenant overrides. |
| `POST` | `/auth/providers` | Create or update a provider configuration for a user/tenant. Secrets resolved via Vault. |
| `DELETE` | `/auth/providers/{provider_id}` | Revoke a provider and delete secret references. |
| `POST` | `/auth/providers/{provider_id}/refresh` | Force token refresh using adapter registry. |
| `GET` | `/auth/users/{uid}` | Fetch user profile + linked providers. |
| `POST` | `/auth/sessions` | Exchange credentials/OAuth result for a session (used by NextAuth adapter). |
| `GET` | `/auth/sessions/{session_id}` | Resolve session for guard middleware. |
| `POST` | `/auth/sessions/{session_id}/revoke` | Terminate active session (logout). |

All endpoints require bearer authentication (`DATAOPS_INTERNAL_TOKEN`) when called by trusted services; end-user flows use signed NextAuth cookies and call adapter helpers that forward to the DataOps gateway.

### MCP Tools (DataOps Server)
| Tool | Purpose |
| --- | --- |
| `auth/providers.list` | Inspect provider catalogue (no secrets). |
| `auth/providers.validate` | Validate a provider payload before committing changes. |
| `auth/storage.validate` | Run storage validator scoped to auth-related configs (delegates to [SPEC-STORAGE](./SPEC-STORAGE.md)). |
| `auth/sessions.list` | Operational metadata for admins (active sessions per tenant). |

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
1. **CRUD Foundation** *(completed)*
   - AuthService now persists via `opsec/auth/repository.py`, backed by UnifiedCRUD.
   - Ensure `User` / `AuthProvider` models declare the correct storage configs and auto-populate `SecurityContext` metadata.
   - Add Vault DAO integration tests and wire secrets broker calls into CRUD operations.
2. **Auth Service HTTP Surface**
   - Expose FastAPI router under `/auth` with endpoints listed above.
   - Implement bearer-auth middleware using `DATAOPS_INTERNAL_TOKEN`.
   - Add storage validation to module setup (call `python base/scripts/check_storage.py auth`).
3. **NextAuth Adapter Integration**
   - Update `ux/auth` adapter to hit `/auth/sessions` and `/auth/providers` instead of the local JSON store.
   - Propagate DataOps validation errors to CMS hint system (`/public/js/account-drawer.js`).
4. **Advanced Providers & Compliance**
   - Add provider schema API for tenant-defined OAuth configs.
   - Implement provider auditing hooks (log to security audit trail), MFA flows, and CLI integration.

## Open Questions & Risks
- **Tenant bootstrap** – Determine how the first admin account is provisioned (manual secret vs. CLI). Consider seeding via `DATAOPS_ADMIN_EMAIL` + `DATAOPS_BOOTSTRAP_TOKEN` env vars.
- **Session storage** – Decide whether to persist sessions in Postgres exclusively or allow stateless JWT sessions for public surfaces.
- **Secrets rotation** – Define rotation playbooks (triggered via MCP `auth/providers.rotate` tool?) to re-encrypt provider secrets without downtime.
- **Compliance mapping** – Align audit logs with ISMS requirements (GDPR data export, right-to-be-forgotten) once CRUD persistence lands.

## References
- [SPEC – DataOps Data Access Pattern](./SPEC-DATAOPS-DATA-ACCESS.md)
- [SPEC – Storage Configuration Management](./SPEC-STORAGE.md)
- `base/backend/opsec/auth/auth_service.py`
- `base/backend/services/secrets_broker`
- `ux/auth/src/server.ts`
- `TODO-AUTH.md`
