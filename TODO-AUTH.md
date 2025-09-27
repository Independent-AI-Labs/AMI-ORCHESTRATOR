# TODO – Authentication Providers & Web Login Enablement

## 1. Login Model Overview

- First-party credential flow (AMI Credentials) – email + secret managed entirely in our stack; requires hashing, throttling, MFA, and recovery flows in `base/backend`.
- Fixed-registration OAuth/OIDC (Google, GitHub, Azure AD) – pre-registered client ids/secrets, redirect handling, token refresh, revoke; browser/device grant handled by `base/backend/opsec/oauth` but lacks persistence/config plumbing.
- Bring-your-own OAuth2/OIDC – tenant-defined endpoints/client credentials; needs dynamic form definitions and backend storage for per-account metadata.
- API key / machine identity providers (OpenAI, Anthropic, generic API keys) – secure key capture, rotation, scope notes, and encrypted storage, delegating request signing to `base/backend` clients.
- Service connectors (SMTP, HuggingFace, etc.) – store connection credentials/tokens securely, surface capability flags, and reuse backend clients for connectivity tests.

## 2. Cross-Cutting Tasks

- [ ] Source of truth: design provider configuration storage in `base/backend` (likely `base/backend/dataops/models` + DAO) so the UX only references normalized schemas.
- [ ] Define provider field schema + validations in `base/backend/opsec/oauth` (e.g., extend `OAuthConfig`/new `ProviderConfig` dataclass) and expose via API for the UI.
- [ ] Implement secrets handling (vault integration) for `client_secret`, `api_key`, etc., in `AuthProvider` so values never leave backend once submitted.
- [ ] Extend session/account APIs (`cms/app/api/account-manager/...`) to call into `base/backend` for create/update/delete of provider configs and tokens instead of inline stubs.
- [ ] Add auditing & error propagation path: map backend validation errors into the new hint system in `cms/public/js/account-drawer.js`.
- [ ] Document environment variables/secret management for local dev vs. deployed (update `docs/` + `.env` templates).
- [ ] Extend `AuthProviderType` + enums to include SMTP and HuggingFace provider identifiers and update downstream switch statements.

## 3. Provider-Specific Requirements

### AMI Credentials (first-party)
- Fields: `email`, `password` (admin set/reset), optional display/role metadata.
- Backend:
  - [ ] Implement credential storage + hashing service under `base/backend/dataops` (consider `passlib`/Argon2) with rate-limiting via `base/backend/dataops/security/rate_limiter.py`.
  - [ ] Add user creation + verification endpoints exposed to UI (no direct password handling in frontend beyond submission).
  - [ ] Ensure MFA hooks (TOTP/WebAuthn) planned in backlog.

### Google Workspace (OAuth2/OIDC)
- Required config: `client_id`, `client_secret`, `redirect_uri`, optional domain restriction, scopes (existing default in `GOOGLE_OAUTH_CONFIG`).
- Backend gaps:
  - [ ] Load client credentials from secure store instead of env defaults; expose CRUD via service.
  - [ ] Persist token payload (`access_token`, `refresh_token`, `expires_at`, `userinfo`) in `AuthProvider` and wire `refresh_access_token()` / `revoke()` to actual DAO.
  - [ ] Provide admin UX instructions/warnings for consent screen verification.
  - [ ] Support device-code flow toggles when headless auth required.

### GitHub (OAuth2)
- Config: `client_id`, `client_secret`, `scopes` (currently placeholder), optional enterprise base URL.
- Backend:
  - [ ] Extend `GITHUB_OAUTH_CONFIG` to hydrate defaults from stored provider config (enterprise URL override, scopes).
  - [ ] Implement `revoke_token` and `refresh_token` (GitHub lacks refresh; plan accordingly) with doc updates.
  - [ ] Handle private-email fetch by calling `/user/emails` and storing primary status in provider data.

### Azure AD / Entra ID
- Config: `tenant_id`, `client_id`, `client_secret`, `redirect_uri`, `scopes`, optionally authority override and admin-consent flags.
- Backend:
  - [ ] Surface tenant selection (common/organizations/specific GUID) to UI; persist in `AuthProvider.tenant`.
  - [ ] Implement token refresh (partially present) and add Graph `userinfo` mapping for `email`/`oid`/`roles` into provider data.
  - [ ] Document lack of API revoke; ensure tokens expire gracefully and add UI hint for revocation limitations.

### OpenAI (API key / OAuth hybrid)
- Near-term: treat as API key.
- Fields: `api_key`, optional `organization_id`, environment label.
- Backend:
  - [ ] Extend `AuthProvider.get_headers()` to support per-project org header (`OpenAI-Organization`).
  - [ ] Add rotation endpoint + last-used tracking.
  - [ ] If/when OAuth enabled, add new `OAuthConfig` entry and callback handling.

### Anthropic (API key)
- Fields: `api_key`, optional `workspace_id`, region.
- Backend:
  - [ ] Capture region in `provider_data` and use in request signing.
  - [ ] Enforce secure storage + rotation parity with OpenAI.

### SMTP Accounts
- Fields: `host`, `port`, `username`, `password` (or app password), `use_tls`/`use_ssl`, default `from_address`, optional `auth_mechanism` (LOGIN, PLAIN, OAuth2).
- Backend:
  - [ ] Define SMTP provider type with secure credential storage and integrate with `base/backend` mailer utilities (if absent, implement reusable client under `base/backend/utils`).
  - [ ] Provide connection test endpoint (EHLO/auth, send noop message) with error translation to UI hints.
  - [ ] Store sending limits/quotas and expose metadata (e.g., daily cap) in `provider_data`.

### HuggingFace (API token / OAuth)
- Fields: `api_token` (personal access token), optional `organization`, `default_repo`/`space`, `scopes` (read/write), future-proof for OAuth (`client_id`, `client_secret`, `redirect_uri`).
- Backend:
  - [ ] Add AuthProviderType and header generation (typically `Authorization: Bearer <token>`); include optional `HF_TOKEN` env fallback.
  - [ ] Document required scopes (`read`, `write`, `space`, `model`) and validate via HuggingFace Hub `/api/whoami-v2` check.
  - [ ] Support token refresh/rotation reminders and capture rate limit metadata in `provider_data`.

### Generic API Key
- Fields: `api_key` (or key+secret), `base_url`, `header_name`, label.
- Backend:
  - [ ] Reuse `base/backend/dataops/implementations/rest/rest_dao.py` to manage header injection; allow per-account override of `auth_type`.
  - [ ] Add validation to ensure minimal metadata (no empty base URL when required).

### Generic OAuth2 / OIDC
- Fields: `provider_name`, discovery URL or manual endpoints (`authorization_url`, `token_url`, `userinfo_url`), `client_id`, `client_secret`, `scopes`, `redirect_uri`, PKCE toggle, optional `audience`.
- Backend:
  - [ ] Create dynamic `OAuthConfig` builder that stores per-account config (vs. global constants) and supports discovery via `.well-known/openid-configuration`.
  - [ ] Persist custom scopes/claims mapping (e.g., which claim becomes our user email) in `provider_data`.
  - [ ] Provide connectivity test endpoint that the UI can call before saving.

## 4. Frontend Alignment (CMS UX)

- [ ] Replace hard-coded provider buttons with dynamic forms defined by backend schema (e.g., request `/api/account-manager/providers/schema`).
- [ ] Add per-provider forms for secrets/tenant settings (editable by admins only) and reduce Add Account modal to selecting pre-configured provider + account identifier.
- [ ] Ensure `account-add` flow stores only non-sensitive identifier fields; secret/token capture should happen in a secure admin dialog with server-side rendering (no localStorage).
- [ ] Surface backend validation/errors via existing hint system (`setAccountHint`).

## 5. API & Session Flow

- [ ] Bridge CMS Next.js API routes with `base/backend` services (use a shared client or RPC) for: session bootstrap, account snapshots, token refresh, revoke.
- [ ] Ensure `/api/auth/session` and related endpoints return 200 + session info once backend integration is live (replace current 501).
- [ ] Implement background refresh job leveraging `AuthProvider.refresh_access_token()` for active accounts; record failures and bubble to UI.
- [ ] Define error taxonomy (invalid_config, token_expired, consent_required, rate_limited) to standardize UI states.

## 6. Security & Compliance

- [ ] Thread provider usage through `base/backend/dataops/security/compliance_reporting.py` once real data flows to enforce MFA and audit logging requirements.
- [ ] Document key handling and rotation SOP in `SECURITY_IMPLEMENTATION_SUMMARY.md`.
- [ ] Add tests in `base/tests` covering token refresh, header generation, and validation of required fields per provider.

---

**Ownership Notes**
- Business logic, token exchange, secret storage, and audit responsibilities belong in `base/backend`. The CMS frontend should request provider schemas + hand off credential payloads, but never duplicate OAuth flows.
- Update module setup scripts to ensure required env vars/config entries are validated before enabling a provider.
