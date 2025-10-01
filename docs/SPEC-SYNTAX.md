# SPEC – Syntax Highlighting Platform

## Scope
This specification defines the unified syntax highlighting platform for AMI Orchestrator. It replaces the ad hoc collection of `highlight.js` scripts in the CMS viewer, the manually synced browser extension bundle, and the bespoke CLI/TUI line renderers with a single tokenisation service that can be consumed by web, extension, and service tooling. The scope spans:

- End-user code rendering inside the CMS shell/document viewer, markdown renderer, and highlight automation dialogs.
- The highlight browser extension packaged from `ux/cms/extension/highlight-plugin`.
- Shared developer ergonomics (copy-to-clipboard, line numbers, language detection, theme palettes).
- Build, bundling, and runtime delivery of syntax assets (languages, themes, WebAssembly) across server-side and client-side contexts.

Out of scope for this iteration:
- CLI/TUI front-ends (`cli-agents/*`) beyond providing a migration path and shared token schema documentation.
- Refactoring domains/predict or other deprecated modules.
- Introducing new code formatting or linting services; focus remains on highlighting fidelity.

## Problem Statement
Highlighting reliability regressed because every surface owns its own assets and heuristics:

- The CMS viewer injects `highlight.js` at runtime via DOM script tags (`ux/cms/packages/highlight-core/src/lib/code-view.js:147`). This breaks in offline/air-gapped environments, duplicates per-language bundles, and causes race conditions when the iframe reloads faster than assets resolve.
- Markdown rendering wraps code fences in `CodeView`, but language inference differs between class names, filename hints, and highlight.js autodetect (`ux/cms/public/js/renderers.js:262`). The result is inconsistent language badges and theme colours compared to raw file viewers.
- The highlight browser extension ships a copy of the CMS plugin and must be manually synced via `scripts/sync-highlight-extension.mjs`. Stale copies drift quickly (`ux/cms/extension/highlight-plugin/pkg/bootstrap.js`).
- Developers lack automated coverage; regressions only surface when someone manually opens the doc iframe. There is no contract for language support, so missing grammars (e.g., `.proto`, `.toml`) fail silently.

## Goals
- Provide a single tokenisation engine with deterministic output for all web-based highlight consumers.
- Support a documented language catalogue and theme palette that meet CMS requirements and are easy to extend without duplicating assets.
- Eliminate runtime `<script>` injection in favour of bundled assets that participate in Next.js builds and CSP checks.
- Offer ergonomics (async loading, controlled recovery hooks, copy-to-clipboard, line numbers) that match or improve current UX.
- Establish automated tests (unit + end-to-end) and observability to prevent silent regressions.

## Non-Goals
- Porting terminal renderers (Ink/Ratatui) in this project phase; instead, publish a schema they can adopt separately.
- Rewriting CMS layouts or dialog infrastructure beyond the minimal changes necessary to consume the new highlighting API.
- Changing markdown rendering libraries (`marked`, `DOMPurify`), though hooks will be exposed to let them use the shared renderer.

## Current Landscape
| Surface | Implementation | Pain Points |
| --- | --- | --- |
| CMS code viewer | `CodeView` class instantiates highlight.js at runtime | Fragile asset discovery, inconsistent language detection, blocking UI during slow network fetches |
| Markdown renderer | Wraps fenced blocks with `CodeView` while leaving inline code unstyled | Duplicated language inference, no shared configuration |
| Highlight extension | Bundled copy of `/public/js/highlight-plugin` | Manual sync script, high drift risk, no build pipeline |
| Assets | Static `vendor/highlightjs/*.js` files | 28 individual language files, no tree shaking, inconsistent updates |

## Target Architecture
```
+------------------------------+
|  packages/highlight-engine   |
|  (Shiki-based token service) |
+---------------+--------------+
                |
    +-----------+------------+
    |                        |
+---v---+              +-----v------+
| CMS   |              | Extension  |
| (Next)|              | Content    |
| app   |              | Script     |
+---+---+              +-----+------+
    |                         |
+---v-------------------------v---+
| Shared bundle exposes:           |
|  - `highlightText()` async API   |
|  - Token schema + themes         |
|  - Language manifest             |
+----------------------------------+
```

### Key Components
- **`packages/highlight-engine`** – New workspace hosting Shiki, Onigasm WASM, language/theme manifests, and helper APIs. Provides two entrypoints: ESM (browser) and Node (for SSR or pre-render).
- **Token Schema** – JSON array of `{ start, end, line, className }` tokens with optional metadata (language, diagnostics). Consumers convert tokens into DOM nodes while reusing existing `CodeView` chrome.
- **Loader Layer** – Thin wrapper that lazy-loads the engine and returns tokens plus formatting metadata. Works both in the main thread and, optionally, via a Web Worker to avoid blocking the UI on large files.
- **Build Integration** – Next.js config imports the engine so bundler handles WASM assets. Extension build reuses the same compiled JS instead of copying sources.

## API Contract
```ts
export interface HighlightRequest {
  id: string;              // trace token
  code: string;            // raw source text
  language?: string;       // optional hint (extension/filename)
  filename?: string;       // optional filename for inference
  theme?: 'ami-light' | 'ami-dark';
}

export interface HighlightToken {
  line: number;            // 0-based line number
  start: number;           // UTF-16 offset within line
  end: number;
  className: string;       // CSS class (e.g., 'token keyword')
}

export interface HighlightResult {
  language: string;        // resolved language id
  tokens: HighlightToken[];
  themedLines: string[];   // optional HTML fragments for SSR paths
  diagnostics?: string[];  // non-fatal notes (e.g., language override)
}
```

Consumers can choose to:
- Render via `CodeView.renderTokens(result)` (updated to apply tokens to DOM nodes).
- Call `renderToHtml(result)` for SSR or static HTML snippets (used by markdown pre-rendering).

## Language & Theme Catalogue
- Base languages: the 28 currently shipped plus additional high-priority grammars (proto, toml, graphql, terraform).
- Managed via `packages/highlight-engine/config/languages.json`, used by build scripts to tree-shake the Shiki registry.
- Themes: `ami-light` and `ami-dark`, derived from existing CSS variables. Generated CSS variables ensure parity with `.code-view .hljs-*` selectors defined in `ux/cms/public/styles/shared.css:2329`.

## Build & Deployment
- Next.js bundler configured to load WASM via `next.config.js` (`experimental.wasm: true`). Onigasm asset emitted to `/_next/static/wasm`.
- Extension bundle imports the compiled ESM entrypoint; build script outputs to `extension/highlight-plugin/dist`. Sync script is retired.
- Feature flag (`process.env.NEXT_PUBLIC_HIGHLIGHT_ENGINE_MODE`) toggles between legacy and new engine for gradual rollout.

## Migration Plan
1. **Baseline (Week 1)**
   - Capture golden snapshots (HTML + JSON tokens) from current highlight.js rendering for a curated corpus.
   - Add regression fixtures under `ux/cms/tests/highlight-fixtures/` consumed by Playwright and Vitest.

2. **Engine Delivery (Week 2)**
   - Scaffold `packages/highlight-engine`, add Shiki integration, generate TypeScript types.
   - Implement core API plus language inference helpers (extension-to-language mapping).

3. **CMS Integration (Week 3)**
   - Update `CodeView` to request tokens and render spans; maintain existing DOM structure for copy, gutter, and accessibility.
   - Replace markdown renderer hook to use `highlightText` instead of `hljs` autodetect.
   - Wire feature flag to allow switching between engines.

4. **Extension Alignment (Week 4)**
   - Replace `pkg/bootstrap.js` with imports from the shared engine. Remove `scripts/sync-highlight-extension.mjs` once parity verified.
   - Add extension-specific lazy loader to account for content-script constraints (no wasm eval until user interaction if CSP restricts).

5. **Cleanup (Week 5)**
   - Remove `vendor/highlightjs` assets and dynamic script loader.
   - Retire legacy globals (`window.__AMI_HIGHLIGHT_ASSET_ROOT__`).
   - Update documentation and onboarding tutorials.

## Testing Strategy
- **Unit Tests** – Vitest suites for language inference, token generation, and theme mapping.
- **Integration Tests** – Playwright flows covering code block rendering, highlight settings dialog toggles, and copy-to-clipboard cues.
- **Snapshot Tests** – Stored token JSON for representative files; diff in CI when languages change.
- **Performance Benchmarks** – Measure tokenisation time for large files (>500 KB) and enforce budget thresholds.

## Observability
- Log tokenisation durations and language override events via `debugLog` hook (reusing `ux/cms/packages/highlight-core/src/highlight-plugin/core/debug.js`).
- Expose Prometheus counters (via CMS API route) for highlight successes/failures to aid Ops triage.

## Rollout & Feature Flags
- `NEXT_PUBLIC_HIGHLIGHT_ENGINE_MODE` environment variable selects `legacy`, `shiki`, or `auto`.
- Admin UI toggle in CMS settings surfaces the same flag for quick rollback during QA.
- Rollout staged: internal environments (dev/staging) -> pilot users -> general availability.

## Risks & Mitigations
| Risk | Mitigation |
| --- | --- |
| WASM bundle size inflates initial load | Lazy-load engine on demand, compress via brotli, cache aggressively |
| CSP blocks WASM execution in extension | Detect CSP, fall back to precompiled HTML tokens or degrade gracefully |
| Slow tokenisation on large files | Offload work to Web Worker, chunk large inputs, provide progress UI |
| Theme mismatch with existing CSS | Generate CSS variables from the same palette and add visual regression tests |

## Maintenance
- Versioned `languages.json` and `themes.json` stored in repo; updates require updating both manifest and Playwright snapshots.
- Document update steps in `docs/Toolchain-Bootstrap.md` to keep developer onboarding current.
- Store engine release notes in `docs/Integration-Status.md` to track adoption.

## Open Questions
1. Do we need server-side pre-rendering of highlighted HTML for static exports? If yes, determine SSR entrypoint for the engine.
2. Should the extension bundle self-host WASM or request it from CMS? Needs security review.
3. Can we delete the current highlight automation UI once new engine lands, or does it depend on legacy class names?

## References
- `ux/cms/packages/highlight-core/src/lib/code-view.js`
- `ux/cms/public/js/renderers.js`
- `ux/cms/extension/highlight-plugin/pkg/bootstrap.js`
- `ux/cms/scripts/sync-highlight-extension.mjs`
