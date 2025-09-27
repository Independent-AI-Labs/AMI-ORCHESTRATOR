# Architecture Map

This document summarises the current module boundaries, responsibilities, and primary entry points. For deeper detail, follow the links to module READMEs and docs.

## Root Orchestrator

- **Responsibilities** – Bootstraps the toolchain, initialises submodules, and enforces the setup contract across modules.
- **Key entry points**
  - `module_setup.py` – Runs `uv` provisioning and dispatches to each module’s setup script.
  - `scripts/bootstrap_uv_python.py` – Trusted installer for `uv` and Python 3.12.
  - `scripts/run_tests.py` – Minimal root test harness (currently a no-op placeholder).

## Modules

| Module | Responsibilities | Primary entry points / notes |
| --- | --- | --- |
| `base/` | Shared environment management, DataOps storage layer (async PostgreSQL, Dgraph, in-memory), FastMCP DataOps + SSH servers, security utilities. | `module_setup.py`, `scripts/run_tests.py`, `backend/mcp/dataops/dataops_server.py`, `backend/utils/path_finder.py`. |
| `browser/` | Managed Chromium provisioning and auditable browser automation tooling. | `module_setup.py`, `scripts/setup_chrome.py`, `backend/automation/**`. Uses stdlib logging until dependencies are installed. |
| `files/` | Secure file ingestion/extraction services and MCP tooling for file operations. | `module_setup.py`, `scripts/run_tests.py`, `backend/mcp/**`, `backend/extractors/**`. |
| `domains/` | Domain models (risk, predictive analytics, SDA) that extend Base DataOps patterns. | `module_setup.py`, `docs/`, `predict/` packages. Focused on models; execution services pending. |
| `compliance/` | Canonical compliance documentation, gap analysis, and forthcoming compliance backend + MCP server. | `module_setup.py`, `docs/COMPLIANCE_BACKEND_SPEC.md`, `docs/COMPLIANCE_GAP_ANALYSIS.md`. Implementation of backend still TODO. |
| `nodes/` | Managed infrastructure processes, tunnel configuration, and automation for remote nodes. | `module_setup.py`, `scripts/setup_service.py`, `config/setup-service.yaml`. |
| `streams/` | Experimental streaming/real-time orchestration. | `module_setup.py`, `docs/` (lightweight). Runtime implementations are in planning. |
| `ux/` | CMS app, shared Auth package, prototype UIs. | `module_setup.py`, `auth/`, `cms/`, `scripts/run_tests.py`. NextAuth rollout in-progress; legacy ES modules still active. |

## Cross-Cutting Policies

- Runner scripts (`run_*`, `scripts/run_tests.py`) are responsible for `sys.path` manipulation via Base `PathFinder`; application packages must not mutate paths at import time.
- Each module owns a local `.venv` created with `uv venv --python 3.12`. No root virtual environment is provided.
- Setup scripts must log via stdlib `logging` and defer third-party imports until after dependencies are installed.
- Quality targets (mypy/ruff/test runners) must align with Python 3.12. Module-local configs derive from Base templates.
