> **ARCHIVED**: This document was superseded by `compliance/docs/research/CURRENT_IMPLEMENTATION_STATUS.md` (updated October 2, 2025).
> The immediate action items are largely completed or documented elsewhere. However, technical references to non-existent Base utilities (PathFinder) and manual path handling in UX remain valid concerns documented below.
> For current project status and roadmap, see `compliance/docs/research/CURRENT_IMPLEMENTATION_STATUS.md`.

# Next Steps & Suggested Owners

Objective: keep documentation, setup tooling, and compliance specs aligned with the code that actually ships.

## Immediate Actions (1–2 days)
- **UX path hygiene** – Replace `sys.path` inserts in `ux/scripts/run_tests.py` with `setup_imports` from `base.scripts.env.paths` (available via `runner_bootstrap.ensure_module_venv` which already calls it). Note: `ux/scripts/run_tests.py` currently uses manual `_ensure_repo_on_path()` at lines 15-21, while Base provides `setup_imports` utility (Owner: UX).
- **Streams status update** – `streams/README.md` now documents operational Matrix services vs in-development components. Note: `streams/README.md:46` references "Base `PathFinder` helpers" which are documented in base/ architecture docs (README.md:65, DESIGN-PATTERNS.md:13, SETUP_CONTRACT.md:4) but not yet implemented. The actual implementation is `setup_imports` from `base.scripts.env.paths`. PathFinder appears to be planned/documented infrastructure (Owner: Streams).
- **Compliance backend kick-off** – When work resumes, scaffold `compliance/backend/` using `compliance/docs/research/COMPLIANCE_BACKEND_SPEC.md` and stub the MCP server for documentation parity (Owner: Compliance).

## Short-Term (1 week)
- **Compliance evidence workflow docs** – `compliance/docs/research/CURRENT_IMPLEMENTATION_STATUS.md` already contains comprehensive backend roadmap milestones (Owner: Compliance).
- **Runners & logging review** – Ensure each module documents how to start its MCP servers or services, and that audit logging hooks are referenced where implemented (Owner: Module leads).

## Verification & Automation
- Re-run `python module_setup.py` after each module update; capture logs to module-specific artefacts for traceability.
- Add doc-check or markdown-link-check jobs if available to catch stale references early.
