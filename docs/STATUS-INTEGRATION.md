# Integration Status

Scope: Track how well modules adhere to the setup contract, highlight remaining drift from Base patterns, and flag documentation required for compliance alignment.

## Summary

- Root `module_setup.py` invokes every module's setup script (base, browser, files, domains, compliance, nodes, streams, ux) with stdlib logging only.
- Base exposes authoritative environment helpers via `base/scripts/env/paths.py` and `base/scripts/env/venv.py`; modules import `setup_imports` and `ensure_venv` instead of duplicating path logic.
- All modules follow the same consolidated setup pattern: bootstrap sys.path, import base utilities, check uv, ensure Python 3.12, sync dependencies via `uv sync --dev`, install git hooks from `base/scripts/hooks/`, then recursively setup child submodules.

## Per-Module Observations

- **base** – Supplies canonical path/environment utilities via `base/scripts/env/`. Test runner available at `base/scripts/run_tests.py`. All modules import from base rather than maintaining separate implementations.
- **browser** – `module_setup.py` follows standard pattern. Provisions Chrome when missing. Verified ✅.
- **files** – Follows standard pattern. Python-only today; extraction services reference actual code paths in docs. ✅
- **domains** – Follows standard pattern. Active focus on `risk/`.
- **compliance** – Follows standard pattern. Module is documentation-only; research specs reside in `compliance/docs/research/`. Building the backend remains a roadmap item.
- **nodes** – Follows standard pattern. Automation lives in `nodes/scripts/setup_service.py`; ensure docs mention the managed process CLI.
- **streams** – Follows standard pattern, but runtime services are placeholders. Documented as experimental; no MCP runners yet.
- **ux** – Follows standard pattern. `scripts/run_tests.py` manually inserts paths via custom `_ensure_repo_on_path()` function at ux/scripts/run_tests.py:15-21, but this is intentional for test isolation. Auth configuration exists in `ux/auth/` with NextAuth integration via DataOps client.

## Outstanding Actions

1. Consider migrating `ux/scripts/run_tests.py:15-21` manual path insertion to use `base/scripts/env/paths.py` helpers for consistency (low priority - current approach works).
2. Implement the compliance backend + MCP server using the research spec once work restarts, updating `docs/README.md` when code lands.
3. Flesh out Streams service runners or mark the module as dormant in its README to avoid overstating functionality.
4. Continue verifying compliance research materials against authoritative PDFs when promoting them back into active documentation.

Track additional backlog items in `docs/TODO-DOCS-GAPS.md` and `docs/TODO-NEXT-STEPS.md`.
