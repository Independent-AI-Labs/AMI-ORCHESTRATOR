# UX Multi-Visualization — Progress Log

This log records concrete changes, decisions, and next steps.

## 2025-09-14

- Bootstrapped visualizers registry and default mounting
  - Added `ux/cms/public/js/visualizers.js` with registry and placeholders for A/B/D
  - Wrapped existing docs viewer as Visualizer C in `ux/cms/public/js/app.js`
  - Switched entry to `app.js` in `ux/cms/public/index.html`
  - Refactored `ux/cms/public/js/main.js` to export `startCms()` with `unmount()`

- Started API scaffolding for media and uploads
  - Added `/api/media` (GET) to serve static files for A/B with CSP headers [initial whitelist]
  - Added `/api/media/list` (GET) to return candidate roots and info [minimal]
  - Added `/api/upload` (POST) to accept multipart uploads to `files/uploads/<timestamp>/` [basic fields]
  - Extended `/api/config`: kept `docRoot`; planned `PATCH` to update `selected`, `preferredMode`, `recents`

- Client Select Media… modal and A/B visualizers
  - Added `public/js/modal.js` with tabs: Recent, Paths, Upload, Enter Path
  - Updated header button to `Select Media…` and added `statusPill`
  - Implemented Visualizer A/B as sandboxed iframes loading `/api/media?path=...&mode=A|B`
  - Added `/api/pathinfo` to detect file/dir/app and `hasJs` to prefer B over A
  - App bootstrap now honors `config.selected` and `selected.mode`; falls back to C
  - Added basic status pill that queries `/api/app/status?path=...` for D

- Shell separation on index (no alternate routes)
  - Removed Next route `/app/viewer/page.tsx`
  - Converted `public/index.html` into the shell (bar + iframe) matching existing style
  - Added `public/doc.html` to host the doc viewer; supports `?embed=1`
  - Added `public/js/shell.js` to mount selection and manage iframe; forwards search via postMessage
  - Added `public/js/doc.js` to initialize the doc viewer directly


Pending polish / next steps
- Implement client UI for Select Media… modal
- Wire detection for A/B/D using `pathInfo`
- Integrate runner status pill for D
- Expand `/api/media/list` sources and add labels
- Add persistence for selected entry + recents; add `PATCH` in config
