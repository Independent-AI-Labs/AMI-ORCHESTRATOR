# CMS Architecture Assessment & Improvement Plan

## Context Snapshot
- **Application split**: The CMS shell (`public/index.html` + `public/js/shell.js`) runs in the primary window, while the document viewer (`public/doc.html` + `public/js/ui.js`) runs inside an iframe that the shell mounts for directory tabs.
- **Tech mix**: Next.js 15 handles API routes only; client UIs are handwritten ES modules served straight from `/public/js`. React 19 UMD builds are loaded at runtime for the content-directory drawer only.
- **State surfaces**: The shell persists tab metadata via `/api/config`; the doc viewer keeps its own global `state` object plus localStorage caches. Cross-window coordination happens through `postMessage` retries.
- **Asset delivery**: Static HTML/JS is served verbatim by Next; there is no bundler-layer cache busting, code splitting, or type enforcement for UI scripts.

## Key Findings

### 1. Split UI without a contract
- Shell and doc viewer duplicate UI controls (highlight toggle, theme button) and depend on optimistic `postMessage` retries to stay in sync.
- Message floods (`postToDoc` fires six times per action) reopen dialogs mid-close and ignore ESC dismissals.
- There is no versioned schema for messages, no ack/timeout handling, and no integration tests across the window boundary.

### 2. Imperative monolith in `ui.js`
- ~1 000 LOC module manages tree rendering, highlight effects, search, dialog lifecycle, and storage with shared mutable state.
- DOM nodes, timers, and event listeners are cached in globals without teardown; reinitialising features (e.g., re-rendering highlight settings) leaks handlers and creates race conditions.
- Feature work requires understanding the entire file—high cognitive load, no unit tests.

### 3. Static assets bypass Next tooling
- `public/js/*.js` modules are shipped raw. Edits skip lint/type checks and rely on manual cache-busting query strings (`?v=20250306`).
- HMR does not apply to the iframe; developers must hard refresh or bump versions to see changes, leading to lost time and stale behaviour in prod.
- CDN dependencies (Mermaid, KaTeX, React UMD) load per iframe without integrity checks or local contingency bundles.

### 4. Dialog patterns reinvented per feature
- Highlight settings, content directory drawer, and other overlays each stitch together their own ESC/backdrop handlers.
- Without a shared controller, rapid toggles during animations leave dialogs in mixed states (backdrop open, surface closed) and break accessibility (`aria-expanded` desync).

### 5. Thin testing story
- Existing TAP suites cover uploads and text-format API endpoints only.
- No coverage for shell/tab lifecycle, iframe messaging, dialogs, or highlight behaviour; regressions ship unnoticed.

### 6. Developer experience mismatches
- README markets a “Next.js service” while the core UI is legacy vanilla JS. Expectations around React patterns, hooks, or SSR are unmet.
- Lack of architectural docs means contributors rediscover iframe boundaries and messaging pitfalls repeatedly.

## Recommendations

### A. Consolidate the UI layer
1. Rebuild the document viewer as a Next.js route (React or server components) that the shell can import directly. Drop the iframe for in-app usage; retain it only if external embedding is required.
2. Share highlight, tree, and dialog components between shell and viewer via a common library (e.g., `/client/` package).
3. Adopt a single state management approach (Context/Zustand/Redux) instead of ad hoc globals. Persist shell/doc settings through the same store.

### B. Formalise inter-window messaging (if iframe retained)
1. Replace fire-and-forget retries with request/response envelopes (`{ id, type, payload }`).
2. Track outstanding requests and cancel retries upon ack; log dropped or late responses.
3. Version message schemas and validate payloads before acting.

### C. Harden dialog infrastructure
1. Promote `createDialogController` into a central dialog service with instance registry, focus trapping, animation state, and ESC/backdrop handling.
2. Provide declarative APIs (`dialog.open('highlight-settings')`) and document lifecycle expectations.
3. Audit accessibility: ensure `aria-modal`, focus return, and inert background states are set consistently.

### D. Bring UI scripts under build governance
1. Move `/public/js` modules into `src/` and build them with Vite/Next bundler. Enable TypeScript + ESLint for all UI code.
2. Generate hashed filenames automatically during build so cache busting is automatic.
3. Replace CDN runtime loads with npm dependencies bundled locally, or at least add Subresource Integrity hashes and local contingency bundles.

### E. Modularise legacy code during transition
1. Extract tree rendering, highlight configuration, and search into separate modules/classes with explicit init/destroy.
2. Remove reliance on global `state` mutations; pass dependencies explicitly to aid testing.
3. Document module responsibilities and event flows.

### F. Expand automated testing
1. Add Playwright (or similar) end-to-end suites covering: tab open/close, highlight settings toggle + ESC, search focus shortcuts, theme sync.
2. Include integration tests for message bus timeouts and error paths.
3. Run UI lint/tests in CI to guarantee consistency.

### G. Clarify developer onboarding
1. Update README with architectural diagrams showing shell ↔ iframe interactions, message flow, and asset pipeline limitations.
2. Provide troubleshooting guidance (e.g., cache busting, restart scripts, known race conditions) until the redesign lands.

## Suggested Roadmap
1. **Stabilise** (short term): Introduce the shared dialog service, formalise message envelopes, add ESC regression tests, document quirks.
2. **Refactor** (mid term): Break `ui.js` into modules, integrate a bundler pipeline, write automated tests.
3. **Re-architect** (long term): Migrate viewer to React/Next route, unify state, remove iframe reliance where feasible.

## Immediate Next Steps
- Decide whether full UI convergence (dropping iframe) is in scope for the next release cycle.
- If not, schedule work on message bus + dialog service to stop highlight regressions while longer-term overhaul proceeds.
- Allocate time for developer documentation updates so contributors stop repeating discovery work.
