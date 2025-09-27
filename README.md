# AMI-ORCHESTRATOR

## What This Repository Does Today

AMI-ORCHESTRATOR coordinates tooling, documentation, and module setup for a compliance-first automation stack. The focus right now is on:

- A consistent setup contract driven by `module_setup.py` at the root and in every module.
- Shared platform capabilities in `base/` (DataOps persistence, MCP servers, path/environment utilities).
- A rapidly expanding compliance body of knowledge under `compliance/docs/`, including the `ISMS-Functionality-Spec.md` and the pluggable compliance backend specification at `compliance/docs/COMPLIANCE_BACKEND_SPEC.md`.
- Up-to-date documentation that mirrors the actual codebase—legacy marketing copy has been removed in favour of verifiable statements.

## Repository Layout (Active Modules)

- `base/` – Houses environment setup helpers, DataOps storage abstractions (PostgreSQL, Dgraph, in-memory), and FastMCP servers for DataOps and SSH. See `base/docs/` for detailed contracts.
- `browser/` – Provides the audited browser automation agent plus a Chrome provisioning script (`browser/scripts/setup_chrome.py`). Delegates setup to Base and keeps third-party imports lazy.
- `files/` – Implements document extraction, MCP tooling for secure file operations, and configuration loaders. Setup mirrors Base patterns.
- `domains/` – Domain models (risk, predictive, SDA) that depend on Base’s storage contracts. Currently focused on data modelling rather than runners.
- `compliance/` – Consolidated EU AI Act + ISO guidance, gap tracking, and the planned compliance backend/server spec. Implementation work is pending; documentation is the source of truth until the backend ships.
- `nodes/` – Infrastructure automation and node setup orchestration, including `nodes/scripts/setup_service.py` for managed process control.
- `streams/` – Streaming/real-time experiments. Setup exists; runtime services are still to be implemented.
- `ux/` – CMS and shared auth package. The UI currently mixes Next.js API routes with legacy ES modules; the NextAuth rollout is in-progress (see `docs/NextAuth-Integration.md`).

Refer to `docs/Architecture-Map.md` for a text map of ownership boundaries and entry points.

## Getting Started

```bash
# Clone the repository (submodules are required)
git clone --recursive <repo-url>
cd AMI-ORCHESTRATOR

# Ensure uv + Python 3.12 toolchain is available
python scripts/bootstrap_uv_python.py --auto

# Provision root tooling and call each module's setup
python module_setup.py

# Run tests per module (examples)
uv run --python 3.12 python scripts/run_tests.py          # root (no-op today)
uv run --python 3.12 --project base python scripts/run_tests.py
uv run --python 3.12 --project compliance python scripts/run_tests.py
```

Module-level runners live under `<module>/scripts/run_tests.py` and automatically reuse Base’s path setup helpers. Follow the compute profile guidance in `AGENTS.md` before installing GPU-specific wheels.

## Documentation Sources

- `docs/` – Orchestrator-level policies: setup contract, toolchain bootstrap, integration status, architecture map, NextAuth rollout notes.
- `compliance/docs/` – Canonical compliance references, including consolidated EU AI Act/ISO markdown, implementation status tracking, and the compliance backend/server specs.
- Module-specific docs live under `<module>/docs/` (for example `base/docs/` and `files/docs/`).

The documentation modernization initiative is ongoing; expect frequent updates as modules evolve.

## Expectations for Contributors

- Stay on branch `main` (no detached HEADs) and rely on `module_setup.py` rather than ad-hoc path hacks.
- Each module is responsible for its own virtual environment (`uv venv --python 3.12`) and must keep `python.ver`, `requirements*.txt`, and `SETUP_CONTRACT.md` up to date.
- Third-party imports in setup scripts must remain deferred until dependencies are installed—stdlib `logging` only.
- Run per-module test suites and any required service stacks (`docker-compose -f docker-compose.data.yml up -d`) before committing.

## Current Roadmap

1. Implement the compliance backend + MCP server described in `compliance/docs/COMPLIANCE_BACKEND_SPEC.md`, reusing Base DataOps patterns.
2. Bring module documentation in sync with real code paths (browser tooling, files extraction, UX auth migration).
3. Replace the remaining legacy path hacks (e.g., `ux/scripts/ami_path.py`) with Base `PathFinder` helpers.
4. Continue the compliance documentation verification loop against consolidated references and source PDFs.

Track work-in-progress items in `docs/Integration-Status.md` and `docs/Next-Steps.md`.
