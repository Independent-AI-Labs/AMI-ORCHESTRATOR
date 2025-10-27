# NextAuth.js Integration Status

> **Last Updated**: October 2027
> **Status**: Core implementation complete, DataOps adapter bridge in progress

## Scope and Objectives
- Protect the `ux/cms` Next.js shell, static assets, and API endpoints with session-aware access control.
- Reuse authentication primitives across other `ux` surfaces and extensions without duplicating logic.
- Align frontend session state with the existing `User`, `AuthProvider`, and `SecurityContext` models in `base/backend/dataops` so downstream services inherit the same identity, role, and tenancy guarantees.

_A detailed backend contract lives in [SPEC – Authentication Platform](./SPEC-AUTH.md); this document tracks Next.js integration status._

## ✅ Completed Implementation

### Core Infrastructure (`ux/auth`)
- Standalone `ux/auth` workspace encapsulates NextAuth configuration, middleware builders, and DataOps-aware credentials bridge
- CMS and highlight browser extension consume via `@ami/auth/*` package alias
- Dev mode fallback (`ux/auth/src/server.ts`): returns guest session when `next-auth` unavailable, enabling tests without full auth stack
- Environment-driven configuration with secrets management (`AMI_GUEST_EMAIL`, `AUTH_SECRET`, etc.)

### API Protection (`ux/cms`)
- All CMS route handlers wrapped with `withSession` guard (`ux/cms/app/lib/auth-guard.ts:8`)
- Returns `401` for unauthenticated requests
- 20+ protected routes including `/api/tree`, `/api/upload`, `/api/file`, `/api/media`, `/api/events`

### Middleware & Routes
- `ux/cms/middleware.ts` enforces auth for `/index.html`, API routes, static assets
- Allow-lists auth UI (`/auth/signin`, `/auth/error`) and public assets
- `/auth/signin` implemented as server/client hybrid (`ux/cms/app/auth/signin/page.tsx`)
- Guest provider route (`/auth/signin/guest`) for passwordless dev workflows

### Client Integration
- `public/js/auth-fetch.js` monkey-patches `window.fetch` with `credentials: 'include'`
- Dispatches `ami:unauthorized` event on 401, redirecting to sign-in with callback URL
- Legacy vanilla modules operate transparently with auth boundary

### Provider Configuration
- **Credentials provider**: validates against local JSON (`AMI_CREDENTIALS_FILE`) or DataOps API (`ux/auth/src/config.ts:144`)
- **Guest provider**: derives stable user ID from `AMI_GUEST_EMAIL`, integrates with DataOps user creation (`ux/auth/src/config.ts:66`)
- **OAuth scaffolding**: Google, GitHub, Azure AD provider loaders with catalog-driven configuration (`ux/auth/src/config.ts:185`)

## 🔄 In Progress

### DataOps Adapter Bridge
- `ux/auth/src/dataops-client.ts` implements dual-mode operation:
  - **Remote mode**: calls DataOps auth gateway (`DATAOPS_AUTH_URL`) with `DATAOPS_INTERNAL_TOKEN`
  - **Local fallback**: reads `AMI_CREDENTIALS_FILE` and `AMI_PROVIDER_CATALOG_FILE` when service unavailable
- Methods: `verifyCredentials`, `getUserByEmail`, `ensureUser`, `getAuthProviderCatalog`
- **Pending**: full Auth.js adapter implementing session lifecycle (create/read/update/delete)

### Current Architecture Footprint
- `ux/cms` runs Next 15 with app-router backend; UI rendered from `public/index.html` via vanilla modules
- Hard redirect `/` → `/index.html` still exists in `next.config.js:7-11` (bypasses middleware for root route)
- SSE endpoint `/api/events` **has** auth guard but may need connection lifecycle improvements

## Why NextAuth.js
- Offers first-class providers (credentials & OAuth) and session storage, matching the OAuth provider catalogue already modelled in `AuthProviderType`.
- Integrates with the Next app router via route handlers and middleware, letting us gate both React/HTML responses and static asset delivery.
- Supports custom adapters, enabling storage inside our multi-backend DataOps layer rather than introducing a separate SQL schema.

## 📋 Remaining Work

### Root Route Migration
- **Problem**: `next.config.js` redirect `/` → `/index.html` bypasses middleware auth check
- **Options**:
  1. Replace redirect with auth-aware `app/page.tsx` embedding `<iframe src="/index.html">`
  2. Migrate vanilla shell into React server components
  3. Keep redirect but document that `/` is publicly accessible (redirect happens client-side to `/index.html` which is protected)

### Session UI Integration
- Add user avatar/name display in shell header (via `/api/auth/session`)
- Integrate logout into command palette
- Propagate session to embedded frames (content drawer, highlight dialog) via `postMessage` for role-based UI (hide upload for viewers)

### Developer Experience
- Extend `scripts/server.mjs` health checks to validate `/api/auth/session` endpoint
- Document environment variable setup for local development (`AMI_GUEST_EMAIL`, `AUTH_SECRET`, etc.)

### Browser Extension Integration
- Configure highlight extension to reuse CMS auth endpoints
- Implement cookie injection or JWT token-based auth flow for extension context

## 🔗 Backend & DataOps Integration

### Current State
- `ux/auth/src/dataops-client.ts` provides bridge to DataOps auth services
- Session JWT includes `roles`, `groups`, `tenantId` fields populated from DataOps (`ux/auth/src/config.ts:574-587`)
- Guest user creation attempts DataOps API call before fallback (`ux/auth/src/config.ts:87-133`)
- Local credentials file (`AMI_CREDENTIALS_FILE`) serves as fallback when DataOps unavailable

### Pending: Full Auth.js Adapter
The DataOps client provides user CRUD but doesn't implement full Auth.js adapter interface. Per [SPEC-AUTH.md](./SPEC-AUTH.md), complete adapter requires:

1. **Session lifecycle**: implement `getSession`, `createSession`, `updateSession`, `deleteSession`
   - Store sessions in DataOps backend (Postgres primary, Dgraph metadata)
   - Use `DATAOPS_AUTH_URL` + `DATAOPS_INTERNAL_TOKEN` for server-to-server calls

2. **Account linking**: implement `linkAccount`, `unlinkAccount`
   - Map OAuth provider accounts to `base/backend/dataops/models/user.User`
   - Store refresh tokens in Vault via `AuthProvider` records

3. **Verification tokens**: implement PKCE flow tokens for OAuth providers

### Role-Based Access Control
- **Current**: session includes `roles` and `groups` arrays
- **Pending**:
  - Call `check_permission` in route guards before filesystem operations
  - Enforce `Permission.WRITE` for uploads, `Permission.ADMIN` for automation
  - Integrate with `base/backend/dataops/models/security.py` SecurityContext

### Multi-tenancy & Audit
- **Current**: `tenantId` embedded in JWT (can be `null` for single-tenant)
- **Pending**:
  - Row-level security via `TenantIsolation.apply_row_level_security`
  - Audit trail logging through `security/audit_trail.py` for sign-in/sign-out
  - Rate limiting via `security/rate_limiter.py` for login attempts

## Implementation Progress

| Phase | Status | Notes |
|-------|--------|-------|
| **Phase 0 — Foundations** | ✅ Complete | Dependencies installed (`next-auth 5.0.0-beta.29`), auth routes scaffolded, middleware active, credentials/guest providers functional |
| **Phase 1 — DataOps Bridge** | 🔄 In Progress | DataOps client operational with local fallback; full adapter (session lifecycle, account linking) pending |
| **Phase 2 — OAuth Providers** | ⚠️ Scaffolded | Provider loaders exist for Google/GitHub/Azure; catalog integration ready; end-to-end OAuth flow untested |
| **Phase 3 — Multi-surface** | 📝 Not Started | Shell still vanilla HTML; extension integration pending; service account strategy undefined |

## Decision Points

### Shell Architecture
**Question**: Migrate vanilla `public/index.html` to React or keep current hybrid?

- **Keep hybrid**: Maintains compatibility with existing vanilla modules, lower refactor cost
- **Migrate to React**: Simplifies session-aware rendering, better TypeScript coverage
- **Current lean**: Keep hybrid until vanilla modules prove limiting

### Service Accounts
**Question**: Where should long-lived automation credentials live?

- **Option A**: NextAuth credentials provider with `roles: ['service']`
- **Option B**: Dedicated DataOps API keys outside NextAuth flow
- **Recommendation**: Option B - service accounts shouldn't use session cookies; use Bearer tokens with longer TTL

### RBAC Rollout
**Question**: Enforce strict RBAC immediately or gradual migration?

- **Current**: All authenticated users have full access (guest role grants broad permissions)
- **Recommendation**: Add `ensureRole(session, 'admin')` checks to `/api/upload`, `/api/automation` first; expand granularity iteratively

## Related Specifications
- [SPEC-AUTH.md](./SPEC-AUTH.md) - Backend authentication platform contract
- [SPEC-DATAOPS-DATA-ACCESS.md](./SPEC-DATAOPS-DATA-ACCESS.md) - CRUD patterns for user/role management
