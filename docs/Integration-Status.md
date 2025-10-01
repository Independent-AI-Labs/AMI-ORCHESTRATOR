# Integration Status

Scope: Track how well modules adhere to the setup contract, highlight remaining drift from Base patterns, and flag documentation required for compliance alignment.

## Summary

- Toolchain bootstrap via `scripts/bootstrap_uv_python.py` works on macOS/Linux/Windows; alternate installer commands cover user-local installs.
- Root `module_setup.py` now invokes every module’s setup script (base, browser, files, domains, compliance, nodes, streams, ux) with stdlib logging only.
- Base exposes the authoritative environment helpers (`base/backend/utils/path_finder.py`, `environment_setup.py`); modules are expected to lean on these rather than duplicating path logic.

## Per-Module Observations

- **base** – Delegates to `AMIModuleSetup` and supplies canonical path/environment utilities. Test runner available at `base/scripts/run_tests.py`.
- **browser** – `module_setup.py` defers all third-party imports until after venv creation and provisions Chrome when missing. Verified ✅.
- **files** – Delegates cleanly to Base. Python-only today; extraction services reference actual code paths in docs. ✅
- **domains** – Delegates to Base; active focus on `risk/`. Predictive trading artefacts have been archived under `predict/research/` until a Base-aligned implementation is planned.
- **compliance** – Setup delegates to Base. Module is documentation-only; research specs now reside in `docs/research/`. Building the backend remains a roadmap item.
- **nodes** – Setup script switched to stdlib logging. Automation lives in `nodes/scripts/setup_service.py`; ensure docs mention the managed process CLI.
- **streams** – Setup exists, but runtime services are placeholders. Documented as experimental; no MCP runners yet.
- **ux** – Setup delegates to Base, but `scripts/run_tests.py` inserts paths manually. Needs migration to Base `PathFinder`. NextAuth middleware and `[...nextauth]` route are live; remaining work is wiring the DataOps adapter and trimming legacy path utilities.

## Outstanding Actions

1. Replace `sys.path.insert` calls in `ux/scripts/run_tests.py` with `PathFinder` helpers once the module adopts the shared utilities package.
2. Implement the compliance backend + MCP server using the research spec once work restarts, updating `docs/README.md` when code lands.
3. Flesh out Streams service runners or mark the module as dormant in its README to avoid overstating functionality.
4. Continue verifying compliance research materials against authoritative PDFs when promoting them back into active documentation.

Track additional backlog items in `docs/Docs-Gaps.md` and `docs/Next-Steps.md`.
