# Next Steps & Suggested Owners

Objective: Converge code and docs on the documented Setup Contract and Quality Policy.

Immediate actions (1–2 days)
- Align typing target to Python 3.12
  - Action: Generate module-local `mypy.ini` from Base template; review root `mypy.ini` usage.
  - Owner: Base
- Fix top-level imports in setup scripts
  - Action: Browser/Files/Node `module_setup.py` → replace `loguru`/`yaml` top-level imports with stdlib `logging` or lazy import post-venv.
  - Owners: Browser, Files, Node
- UX path discovery
  - Action: Replace `scripts/ami_path.py` usage with `PathFinder` for consistency.
  - Owner: UX
- MCP runner doc alignment
  - Action: Update docs to describe programmatic startup and module-specific runners (done in this pass).
  - Owner: Base

Short-term (1 week)
- Submodule access guidance
  - Action: Document HTTPS alternatives for `.gitmodules` and CI usage in `/docs/Quality-Policy.md`.
  - Owner: Orchestrator
- Pre-commit cross-platform
  - Action: Validate template expansion (`{{MYPY_ENTRY}}`) across modules; run sample hooks on Windows/macOS/Linux.
  - Owner: Base

Documentation backlog
- Fill missing references from root `README.md`: `IMPORT_CONVENTIONS.md`, `MASTER_CODE_QUALITY_REPORT.md`, `QA.md`, `TYPE_IGNORE_AUDIT.md`.
- Owner: Orchestrator (coordinate), Module leads (content)

Verification
- Re-run `python module_setup.py` after fixes; capture per-module logs into `artifacts/setup-<module>.log` (optional enhancement to orchestrator runner).
- Smoke-run MCP servers via listed runners; ensure imports succeed without ad-hoc path hacks.
