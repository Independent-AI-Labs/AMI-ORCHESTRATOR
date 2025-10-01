# TODO – Authentication Providers & Web Login Enablement

## Progress Snapshot (2025-10-01)
- ✅ `AuthProvider` model plus adapter plumbing exist, and `AuthService` now uses dedicated helper utilities (currently backed by an in-memory store) instead of model-level stubs (`base/backend/opsec/auth/auth_service.py:40-314`, `opsec/utils/user_utils.py`).
- ✅ OAuth/API-key/SSH adapters + `AuthService` flows are wired for token refresh/revoke (`base/backend/opsec/auth/provider_adapters.py`, `auth_service.py`), and the target wiring uses Postgres for canonical records, Dgraph for metadata, and Vault for secrets (no Redis cache required).
- ⚠️ CMS account APIs write to the local JSON cache; there is no call into DataOps for CRUD (`ux/cms/app/lib/store.ts:184-356`, `ux/cms/app/api/account-manager/accounts/route.ts:1-84`).
- ⚠️ `ux/auth` falls back to a stub NextAuth implementation that manufactures sessions/providers when DataOps/backends fail (`ux/auth/src/server.ts:1-214`).
- ⚠️ `dataOpsClient` only reaches the backend if `DATAOPS_AUTH_URL` is set; otherwise it serves from local files (`ux/auth/src/dataops-client.ts:1-248`).
- ⛔ No dedicated SPEC-AUTH or environment documentation; `TODO-AUTH.md` remains the only source.

## 1. Login Model Overview

- First-party credential flow (AMI Credentials) – email + secret managed entirely in our stack; requires hashing, throttling, MFA, and recovery flows in `base/backend`.
- Fixed-registration OAuth/OIDC (Google, GitHub, Azure AD) – pre-registered client ids/secrets, redirect handling, token refresh, revoke; browser/device grant handled by `base/backend/opsec/oauth` but lacks persistence/config plumbing.
- Bring-your-own OAuth2/OIDC – tenant-defined endpoints/client credentials; needs dynamic form definitions and backend storage for per-account metadata.
- API key / machine identity providers (OpenAI, Anthropic, generic API keys) – secure key capture, rotation, scope notes, and encrypted storage, delegating request signing to `base/backend` clients.
- Service connectors (SMTP, HuggingFace, etc.) – store connection credentials/tokens securely, surface capability flags, and reuse backend clients for connectivity tests.

## 2. Cross-Cutting Tasks

- [ ] Source of truth: design provider configuration storage in `base/backend` (likely `base/backend/dataops/models` + DAO) so the UX only references normalized schemas, with Postgres as primary storage, Dgraph handling relationship metadata, and Vault storing secrets (no Redis tier). _(Current state: `AuthProvider` has `StorageModel` scaffolding but `find_or_create` / DAO hooks are TODO; see `base/backend/dataops/models/user.py:101-177`.)_
- [x] Align all persistence with [SPEC – DataOps Data Access Pattern](docs/SPEC-DATAOPS-DATA-ACCESS.md): port `AuthService`/related helpers to `get_crud(...)`-backed services and delete model-level CRUD stubs.
- [ ] Define provider field schema + validations in `base/backend/opsec/oauth` (e.g., extend `OAuthConfig`/new `ProviderConfig` dataclass) and expose via API for the UI. _(Static configs live in `oauth_config.py:102-144`; nothing dynamic or validated.)_
- [ ] Implement secrets handling (vault integration) for `client_secret`, `api_key`, etc., in `AuthProvider` so values never leave backend once submitted. _(Tokens stored as `SecretStr` and mapped to `StorageType.VAULT`, but there is no DAO persistence or secrets broker integration yet.)_
- [ ] Extend session/account APIs (`cms/app/api/account-manager/...`) to call into `base/backend` for create/update/delete of provider configs and tokens instead of inline stubs. _(Routes still write to `ux/cms/app/lib/store.ts` JSON files.)_
- [ ] Add auditing & error propagation path: map backend validation errors into the new hint system in `cms/public/js/account-drawer.js`. _(UI only sets hints based on local validation.)_
- [ ] Document environment variables/secret management for local dev vs. deployed (update `docs/` + `.env` templates). _(No `SPEC-AUTH`/`.env` guidance exists.)_
- [ ] Extend `AuthProviderType` + enums to include SMTP and HuggingFace provider identifiers and update downstream switch statements. _(Enum in `base/backend/dataops/models/types.py:10-24` lacks these entries.)_

## 3. Provider-Specific Requirements

### AMI Credentials (first-party)
- Fields: `email`, `password` (admin set/reset), optional display/role metadata.
- Backend:
  - [ ] Implement credential storage + hashing service under `base/backend/dataops` (consider `passlib`/Argon2) with rate-limiting via `base/backend/dataops/security/rate_limiter.py`. _(No password pipeline exists.)_
  - [ ] Add user creation + verification endpoints exposed to UI (no direct password handling in frontend beyond submission). _(CMS APIs still stub.)_
  - [ ] Ensure MFA hooks (TOTP/WebAuthn) planned in backlog. _(None implemented.)_

### Google Workspace (OAuth2/OIDC)
- Required config: `client_id`, `client_secret`, `redirect_uri`, optional domain restriction, scopes (existing default in `GOOGLE_OAUTH_CONFIG`).
- Backend gaps:
  - [ ] Load client credentials from secure store instead of env defaults; expose CRUD via service. _(Configs still read from environment defaults.)_
  - [ ] Persist token payload (`access_token`, `refresh_token`, `expires_at`, `userinfo`) in `AuthProvider` and wire `refresh_access_token()` / `revoke()` to actual DAO. _(Model supports it, but persistence layer missing.)_
  - [ ] Provide admin UX instructions/warnings for consent screen verification. _(Documentation absent.)_
  - [ ] Support device-code flow toggles when headless auth required. _(No flag surfaced.)_

### GitHub (OAuth2)
- Config: `client_id`, `client_secret`, `scopes` (currently placeholder), optional enterprise base URL.
- Backend:
  - [ ] Extend `GITHUB_OAUTH_CONFIG` to hydrate defaults from stored provider config (enterprise URL override, scopes). _(Static config only.)_
  - [ ] Implement `revoke_token` and `refresh_token` (GitHub lacks refresh; plan accordingly) with doc updates. _(Adapters defer to OAuth manager; GitHub manager lacks custom handling.)_
  - [ ] Handle private-email fetch by calling `/user/emails` and storing primary status in provider data. _(Not implemented.)_

### Azure AD / Entra ID
- Config: `tenant_id`, `client_id`, `client_secret`, `redirect_uri`, `scopes`, optionally authority override and admin-consent flags.
- Backend:
  - [ ] Surface tenant selection (common/organizations/specific GUID) to UI; persist in `AuthProvider.tenant`. _(Tenant defaults to `common`.)_
  - [ ] Implement token refresh (partially present) and add Graph `userinfo` mapping for `email`/`oid`/`roles` into provider data. _(No Graph integration yet.)_
  - [ ] Document lack of API revoke; ensure tokens expire gracefully and add UI hint for revocation limitations. _(Doc/UI missing.)_

### OpenAI (API key / OAuth hybrid)
- Near-term: treat as API key.
- Fields: `api_key`, optional `organization_id`, environment label.
- Backend:
  - [ ] Extend `AuthProvider.get_headers()` to support per-project org header (`OpenAI-Organization`). _(Adapter currently only sets `Authorization`.)_
  - [ ] Add rotation endpoint + last-used tracking. _(No management endpoints.)_
  - [ ] If/when OAuth enabled, add new `OAuthConfig` entry and callback handling. _(Not started.)_

### Anthropic (API key)
- Fields: `api_key`, optional `workspace_id`, region.
- Backend:
  - [ ] Capture region in `provider_data` and use in request signing. _(Adapter ignores region.)_
  - [ ] Enforce secure storage + rotation parity with OpenAI. _(No rotation APIs.)_

### SMTP Accounts
- Fields: `host`, `port`, `username`, `password` (or app password), `use_tls`/`use_ssl`, default `from_address`, optional `auth_mechanism` (LOGIN, PLAIN, OAuth2).
- Backend:
  - [ ] Define SMTP provider type with secure credential storage and integrate with `base/backend` mailer utilities (if absent, implement reusable client under `base/backend/utils`). _(No SMTP enums or client.)_
  - [ ] Provide connection test endpoint (EHLO/auth, send noop message) with error translation to UI hints. _(Not implemented.)_
  - [ ] Store sending limits/quotas and expose metadata (e.g., daily cap) in `provider_data`. _(Not implemented.)_

### HuggingFace (API token / OAuth)
- Fields: `api_token` (personal access token), optional `organization`, `default_repo`/`space`, `scopes` (read/write), future-proof for OAuth (`client_id`, `client_secret`, `redirect_uri`).
- Backend:
  - [ ] Add AuthProviderType and header generation (typically `Authorization: Bearer <token>`); include optional `HF_TOKEN` env fallback. _(Enum + adapter missing.)_
  - [ ] Document required scopes (`read`, `write`, `space`, `model`) and validate via HuggingFace Hub `/api/whoami-v2` check. _(Not documented.)_
  - [ ] Support token refresh/rotation reminders and capture rate limit metadata in `provider_data`. _(Not implemented.)_

### Generic API Key
- Fields: `api_key` (or key+secret), `base_url`, `header_name`, label.
- Backend:
  - [ ] Reuse `base/backend/dataops/implementations/rest/rest_dao.py` to manage header injection; allow per-account override of `auth_type`. _(Not wired.)_
  - [ ] Add validation to ensure minimal metadata (no empty base URL when required). _(No schema enforcement.)_

### Generic OAuth2 / OIDC
- Fields: `provider_name`, discovery URL or manual endpoints (`authorization_url`, `token_url`, `userinfo_url`), `client_id`, `client_secret`, `scopes`, `redirect_uri`, PKCE toggle, optional `audience`.
- Backend:
  - [ ] Create dynamic `OAuthConfig` builder that stores per-account config (vs. global constants) and supports discovery via `.well-known/openid-configuration`. _(None today.)_
  - [ ] Persist custom scopes/claims mapping (e.g., which claim becomes our user email) in `provider_data`. _(Not implemented.)_
  - [ ] Provide connectivity test endpoint that the UI can call before saving. _(No API route.)_

## 4. Frontend Alignment (CMS UX)

- [ ] Replace hard-coded provider buttons with dynamic forms defined by backend schema (e.g., request `/api/account-manager/providers/schema`). _(Forms still static.)_
- [ ] Add per-provider forms for secrets/tenant settings (editable by admins only) and reduce Add Account modal to selecting pre-configured provider + account identifier. _(Modal still generic.)_
- [ ] Ensure `account-add` flow stores only non-sensitive identifier fields; secret/token capture should happen in a secure admin dialog with server-side rendering (no localStorage). _(Secrets never captured yet; flow incomplete.)_
- [ ] Surface backend validation/errors via existing hint system (`setAccountHint`). _(Only local validation feeding hints.)_

## 5. API & Session Flow

- [ ] Bridge CMS Next.js API routes with `base/backend` services (use a shared client or RPC) for: session bootstrap, account snapshots, token refresh, revoke. _(Currently stubbed to local store and stub auth.)_
- [x] Ensure `/api/auth/session` and related endpoints return 200 + session info once backend integration is live (replace current 501). _(Stub implementation responds with session/CSRF/providers; see `ux/auth/src/server.ts:35-123`.)_
- [ ] Implement background refresh job leveraging `AuthProvider.refresh_access_token()` for active accounts; record failures and bubble to UI. _(No job runner.)_
- [ ] Define error taxonomy (invalid_config, token_expired, consent_required, rate_limited) to standardize UI states. _(Not formalised.)_

## 6. Security & Compliance

- [ ] Thread provider usage through `base/backend/dataops/security/compliance_reporting.py` once real data flows to enforce MFA and audit logging requirements. _(No integration.)_
- [ ] Document key handling and rotation SOP in `SECURITY_IMPLEMENTATION_SUMMARY.md`. _(Document missing.)_
- [ ] Add tests in `base/tests` covering token refresh, header generation, and validation of required fields per provider. _(Only adapter unit tests exist.)_

---

**Ownership Notes**
- Business logic, token exchange, secret storage, and audit responsibilities belong in `base/backend`. The CMS frontend should request provider schemas + hand off credential payloads, but never duplicate OAuth flows.
- Update module setup scripts to ensure required env vars/config entries are validated before enabling a provider.
