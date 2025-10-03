# NextAuth.js Integration Blueprint

## Scope and Objectives
- Protect the `ux/cms` Next.js shell, static assets, and API endpoints with session-aware access control.
- Reuse authentication primitives across other `ux` surfaces and extensions without duplicating logic.
- Align frontend session state with the existing `User`, `AuthProvider`, and `SecurityContext` models in `base/backend/dataops` so downstream services inherit the same identity, role, and tenancy guarantees.

_A detailed backend contract lives in [SPEC – Authentication Platform](./SPEC-AUTH.md); this document focuses on the Next.js integration plan._

## Current Implementation (March 2025)
- A standalone `ux/auth` workspace now encapsulates NextAuth configuration, middleware builders, and the DataOps-aware credentials bridge. CMS and the highlight browser extension consume these helpers via the local package alias `@ami/auth/*`.
- All CMS route handlers are wrapped with `withSession`, returning `401` responses for unauthenticated access. A shared middleware enforces sign-in for `/index.html`, API routes, and static assets while allow-listing the auth UI itself.
- `/auth/signin` is implemented as a server/client hybrid with reusable styling, matching the content-directory drawer. Legacy vanilla modules dispatch a global `ami:unauthorized` event that redirects to the sign-in page when a 401 is encountered.
- Automated tests and local scripts fall back to a stub auth implementation whenever `next-auth` (or its credentials provider) is missing on disk. The stub returns an "admin" session and logs a warning, preserving previous unauthenticated behaviour while enabling incremental rollout.
- `public/js/auth-fetch.js` centralises cookie forwarding and 401 handling so the existing vanilla fetch helpers operate transparently with the new auth boundary.

## Current Authentication Footprint
- `ux/cms` runs on Next 15 with an app-router-only backend (`ux/cms/package.json`). All UI is rendered from `public/index.html` via vanilla modules in `public/js`, so there is no built-in session concept; REST handlers under `app/api/**` are publicly reachable.
- The shell redirects `/` to `/index.html` (`ux/cms/next.config.js`), bypassing Next page rendering and any guardrails provided by the app router.
- API handlers (e.g. `/api/tree`, `/api/file`, `/api/media`) directly perform filesystem work using helpers in `app/lib/*` with no user context. SSE endpoints like `/api/events` keep long-lived connections open without authentication hooks.
- The wider `ux` module currently exposes no reusable auth layer; all DataOps security constructs live in Python (`base/backend/dataops/models/security.py`, `models/user.py`).

## Why NextAuth.js
- Offers first-class providers (credentials & OAuth) and session storage, matching the OAuth provider catalogue already modelled in `AuthProviderType`.
- Integrates with the Next app router via route handlers and middleware, letting us gate both React/HTML responses and static asset delivery.
- Supports custom adapters, enabling storage inside our multi-backend DataOps layer rather than introducing a separate SQL schema.

## Frontend Integration (ux/cms)
### Dependencies & Configuration
1. Add `next-auth` (Auth.js v5) and any provider packages to `ux/cms/package.json`; align TypeScript types with Next 15. _(Done; stub mode activates when the dependency is absent during tests.)_
2. Create `auth.config.ts` describing providers, callbacks, and session strategy. Use environment variables for secrets (`AUTH_SECRET`, provider client IDs/secrets) and load defaults from module-level `.env.local`.

### Route Handlers & Session Helpers
1. Implement `app/api/auth/[...nextauth]/route.ts` exporting `GET`/`POST` from `NextAuth(config)`.
2. Export `auth`, `signIn`, `signOut` helpers (Auth.js pattern) from `auth.ts` for reuse in server components and middleware.
3. Wrap existing API handlers with an auth guard utility that calls `auth()` and enforces role/tenant checks before performing filesystem or runner actions.

### Static Shell Protection
1. Introduce `middleware.ts` that calls `auth()` and redirects unauthenticated users to `/auth/signin` before serving `/index.html`, `/docs`, `/public/res/**`, and API routes. Allowlist assets needed for the sign-in page. _(Implemented.)_
2. Replace the hard redirect in `next.config.js` with a Next page (e.g. `app/page.tsx`) that renders the shell via `<iframe src="/index.html">` only after the session resolves, or migrate the shell into a React server component so middleware control is simpler. _(Pending; legacy redirect still exists but is now guarded by middleware.)_

### Client Runtime Adjustments
1. Update `public/js/api.js` and other fetch helpers to send `credentials: 'include'`, handling 401 responses by triggering a redirect to the sign-in route. _(Implemented via a shared fetch wrapper and event bridge.)_
2. Ensure the SSE connection in `/api/events` rejects unauthenticated requests early to avoid hanging sockets.
3. Propagate session context to embedded frames (content directory drawer, highlight dialog) using `postMessage` so legacy JS modules can tailor behaviour (e.g. hide upload buttons for viewers).

### UI & DX
1. Provide a minimal `/auth/signin` page that lists enabled providers and gracefully falls back to credentials when OAuth is unavailable.
2. Add session indicators (user avatar/name via `/api/auth/session`) to the shell header; hook logout into the existing command palette.
3. Extend `scripts/server.mjs` health checks to validate `/api/auth/session` so background runners detect auth misconfiguration quickly.

## Shared UX Module Considerations
- Move NextAuth config into `ux/auth/` (new workspace) exposing both browser-friendly helpers (for cms) and Node utilities (for CLI/dev tools). This keeps the CMS, future panels, and the highlight browser extension aligned. _(Completed.)_
- Expose a lightweight SDK (e.g. `ux/auth/client.ts`) that wraps `fetch` with the correct credentials policy and CSRF headers so legacy vanilla modules can consume protected APIs without knowledge of Auth.js details.
- When packaging the highlight browser extension, reuse the same auth endpoints by pointing it at the CMS host; inject session cookies or use token-based flows derived from NextAuth JWT mode.

## Backend & DataOps Alignment
### User & AuthProvider Mapping
- Map NextAuth `User` objects to `base/backend/dataops/models/user.User`, populating `email`, `full_name`, `avatar_url`, and `auth_provider_ids`. Follow [SPEC – DataOps Data Access Pattern](./SPEC-DATAOPS-DATA-ACCESS.md) by performing lookups/creates through `get_crud(User)` inside a dedicated service (no model-level helpers). Set ownership metadata via the service before persisting.
- Store provider tokens via `AuthProvider` and mark `Vault` storage for secrets to keep OAuth refresh tokens secure (matches current `AuthProvider.Meta` configs).

### Custom Auth.js Adapter
Follow the backend contract in [SPEC – Authentication Platform](./SPEC-AUTH.md). Once the CRUD-backed service ships, implement the adapter in three deliberate passes:
1. Replace the stubbed `ux/auth/src/server.ts` persistence with calls to `/auth/sessions` and `/auth/providers` on the DataOps auth gateway (`DATAOPS_AUTH_URL`). Use `DATAOPS_INTERNAL_TOKEN` for server-to-server calls and surface `NEXT_PUBLIC_DATAOPS_AUTH_URL` to the browser so middleware can resolve the same host.
2. Map Auth.js lifecycle methods to UnifiedCRUD operations: call `createUser`/`linkAccount` against the new endpoints, normalise IDs, and persist secret-bearing fields through the Vault-aware payloads returned by the service; storage failures surface immediately so operators can restore Postgres/Dgraph/Vault.
3. Delegate session `getSession`/`updateSession` to the DataOps API, deleting any local JSON cache, and wire error responses into the CMS hint system so validation issues reach the UI.

### SecurityContext & Roles
- Derive `SecurityContext` from NextAuth session claims: `user_id`, `roles`, `groups`, `tenant_id`. Use callbacks to merge DataOps role assignments (`Role`, `SecurityGroup`) so API route guards can call `check_permission` before touching the filesystem.
- Enforce content-directory authorisation by checking for `Permission.WRITE` before uploads and `Permission.ADMIN` before runner operations.

### Multi-tenancy & Compliance
- Honour tenant isolation by embedding `tenant_id` in the session JWT. On each request, call `TenantIsolation.apply_row_level_security` or `TenantContext.get_storage_config` to scope DataOps queries.
- Log auth events through `security/audit_trail.py` to maintain parity with backend audit requirements; include sign-in, sign-out, and token refresh events.
- Surface rate limits using `security/rate_limiter.py` to throttle repeated login attempts at the edge.

## Implementation Phasing
1. **Phase 0 — Foundations**: add dependencies, scaffold auth routes, wire middleware in preview mode, and introduce a credentials provider backed by a mock adapter for local validation.
2. **Phase 1 — DataOps Adapter**: connect the adapter to Postgres (primary) + Dgraph (metadata), map users/providers, and light up role-based guards on upload/library endpoints while Vault secures secrets.
3. **Phase 2 — OAuth Providers**: configure Google/GitHub/Azure clients (leveraging `base/backend/opsec/oauth/oauth_config.py`) and enable refresh-token persistence via `AuthProvider.refresh_access_token`.
4. **Phase 3 — Multi-surface Rollout**: migrate legacy `public/index.html` into React or wrap it in a session-aware loader, integrate the highlight extension, and provide CLI tokens for automation.

## Open Questions
- Should the CMS remain static HTML, or is it time to progressively refactor into app-router components to simplify session-aware rendering?
- Where should long-lived service accounts (for automated ingestion) live—NextAuth credentials provider, or dedicated DataOps service principals exposed via API keys?
- How aggressively do we enforce RBAC during the bootstrap phase (read-only vs full control), and what migration steps are needed for existing local workflows?
