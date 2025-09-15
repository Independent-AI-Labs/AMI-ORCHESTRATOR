# UX Multi-Visualization — Master TODO

Scope: `ux/cms` (Next.js app) and its public viewer. Goal: support four visualization modes with detection, serving, upload, and a unified UI.

## Modes

- [x] A: Single HTML+CSS file (sandboxed iframe)
  - [x] Detect single `.html` file; optional `.css` sibling
  - [x] Serve via `/api/media` with strict CSP, deny inline script by default
  - [x] Mount in iframe with `sandbox` attrs; toolbar displays mode and path
- [x] B: HTML+JS/CSS file set (no server code)
  - [x] Detect `.html` with `.js`/`.css` siblings
  - [x] Serve via `/api/media` with strict CSP (allow script, no `unsafe-inline`)
  - [x] Mount in iframe; in-iframe simple search optional
- [x] C: Directory docs viewer (current)
  - [x] Wrap existing viewer as a visualizer (Visualizer C)
  - [x] Bootstrap via new app entry
- [ ] D: Custom Next.js app (self-contained SPA)
  - [ ] Detect `package.json` with `next` dep and `app/` or `pages/`
  - [ ] Launch via runner on ephemeral port; status pill in UI
  - [ ] Embed via iframe or proxy subpath `/app/*`

## Detection

- [x] Implement `canHandle(pathInfo)` for A/B/D (A/B complete, D basic)
- [x] Add server-side utilities to compute `pathInfo` for a selected entry
- [x] Provide selection UI that persists chosen entry

## Runtime / Embedding

- [x] A/B: iframe with strict CSP; static content from `/api/media`
- [ ] C: existing doc-tree UI mounted via Visualizer C
- [ ] D: orchestrate with JS runner `npm run serve` (start/stop/status) and embed

## APIs and Config

- [ ] Extend `/api/config` to include:
  - [x] Keep `docRoot`
  - [x] `selected` media entry `{ type: 'file'|'dir'|'app', path, mode? }`
  - [ ] `preferredMode` (optional)
  - [x] `recents` list
  - [x] PATCH handler to update partial config
- [x] Add `/api/media/list` for quick roots and helpers
  - [ ] Return known roots and resolved labels
- [x] Add `/api/upload` (multipart)
  - [ ] File upload → `files/uploads/<timestamp>/<name>`
  - [ ] Directory upload (webkitdirectory) → preserve relative paths
  - [ ] Security: constrain to uploads root; normalize paths; no traversal
- [x] Add `/api/media` (static serving for A/B)
  - [ ] Whitelist extensions; set CSP headers; ETag/Cache-Control

## UI / UX

- [ ] Floating glass bar (fixed header)
  - [ ] Glassmorphic style, persistent across modes
  - [ ] Mode icon+label, truncated path with tooltip
  - [ ] Global search field
  - [ ] Status pill (SSE/app runner/errors)
  - [ ] “Select Media…” button
- [x] Select Media… modal
  - [ ] Tabs: Recent, Paths, Upload, Enter Path
  - [ ] Recent: list from config with mode badges
  - [ ] Paths: server-provided list + browse input
  - [ ] Upload: file or directory with progress
  - [ ] Enter Path: free-text; validate on submit
- [ ] Icons: inline SVG set (folder, file, search, status, upload, app)
- [ ] Persistence: selected entry, mode, search text, expand state, theme

## Shell Separation (React + Tailwind)

- [ ] Create SPA shell at `app/viewer/page.tsx` (client component)
  - [ ] Glass bar (React) + VisualizationSurface (iframe)
  - [ ] React Select Media modal (replace legacy `public/js/modal.js`)
  - [ ] Wire shell search to visualization via `postMessage`
- [ ] Introduce TailwindCSS to `ux/cms`
  - [ ] Add `tailwind.config.js`, `postcss.config.js`, and `globals.css`
  - [ ] Replace inline styles with Tailwind utilities (shell only)
  - [ ] Keep visualizations isolated; Tailwind styles do not leak into iframes
- [ ] Doc tree embed mode
  - [ ] Support theme param `?theme=dark|light`
  - [ ] Add `postMessage` handlers (search, expand/collapse)
- [ ] D Mode orchestration
  - [ ] /api/app/start|stop|restart endpoints (call JS runner `npm run serve`)
  - [ ] Status polling and logs link in shell
  - [ ] Decide proxy `/app/*` vs direct port; implement chosen path

## Code Quality

- [ ] Extend ESLint/Prettier coverage to `public/` CSS/TS/JS
- [ ] Optional: GitHub Actions for lint on PR

## Acceptance Criteria

- [ ] Can select and render:
  - [ ] Single HTML file in sandbox (A)
  - [ ] HTML+JS/CSS set in sandbox (B)
  - [x] Directory via current doc viewer (C)
  - [ ] Next.js app embedded and status reported (D)
- [ ] Floating glass bar with icons, search, status across modes
- [ ] Select Media… modal (recent, list, input, upload)
- [ ] Config persists choices; SSE/refresh intact for (C)

## Notes & Open Questions

- Next apps (D): allow dev auto-start for any app vs whitelist?
- Proxy under `/app/` vs direct port? Proxy is cleaner but needs Next basePath/assetPrefix.
- Uploads: max size; allowed types; retention policy.
- Security: for (B) JS-in-HTML in iframe with strict CSP acceptable?
