# Next Steps & Suggested Owners

Objective: keep documentation, setup tooling, and compliance specs aligned with the code that actually ships.

## Immediate Actions (1–2 days)
- **UX path hygiene** – Replace `sys.path` inserts in `ux/scripts/run_tests.py` with Base `PathFinder` helpers once shared utilities are imported (Owner: UX).
- **Streams status update** – Clarify in `streams/README.md` whether runtime services are paused or provide a minimal runner stub (Owner: Streams).
- **Compliance backend kick-off** – Scaffold the `compliance/backend/` package per `docs/COMPLIANCE_BACKEND_SPEC.md` and stub the MCP server for documentation parity (Owner: Compliance).

## Short-Term (1 week)
- **NextAuth DataOps adapter** – Connect the shared auth module to DataOps persistence and update `docs/NextAuth-Integration.md` with the revised flow (Owner: UX).
- **Compliance evidence workflow docs** – Extend `compliance/docs/CURRENT_IMPLEMENTATION_STATUS.md` with the backend roadmap milestones so engineering can trace coverage (Owner: Compliance).
- **Runners & logging review** – Ensure each module documents how to start its MCP servers or services, and that audit logging hooks are referenced where implemented (Owner: Module leads).

## Verification & Automation
- Re-run `python module_setup.py` after each module update; capture logs to module-specific artefacts for traceability.
- Add doc-check or markdown-link-check jobs if available to catch stale references early.
