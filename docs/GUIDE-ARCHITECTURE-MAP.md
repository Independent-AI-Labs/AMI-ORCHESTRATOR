# Architecture Map

This document summarises the current module boundaries, responsibilities, and primary entry points. For deeper detail, follow the links to module READMEs and docs.

## Root Orchestrator

- **Responsibilities** – Bootstraps the toolchain, initialises submodules, and enforces the setup contract across modules.
- **Key entry points**
  - `install.py` – One-time installer that initializes git submodules, registers shell aliases (`ami-run`, `ami-uv`), then runs `module_setup.py` as subprocess.
  - `module_setup.py` – Runs `uv` provisioning and recursively dispatches to each module's setup script.
  - `scripts/run_tests.py` – Root test harness that bootstraps into module venv via `runner_bootstrap` and runs pytest if tests exist.

## Modules

| Module | Responsibilities | Primary entry points / notes |
| --- | --- | --- |
| `base/` | Shared environment management, DataOps storage layer (async PostgreSQL, Dgraph, in-memory), FastMCP DataOps + SSH servers, security utilities. | `module_setup.py`, `scripts/run_tests.py`, `backend/mcp/dataops/dataops_server.py`, `backend/utils/runner_bootstrap.py`. |
| `browser/` | Managed Chromium provisioning and auditable browser automation tooling. | `module_setup.py`, `scripts/setup_chrome.py`, `backend/mcp/chrome/**`. Experimental anti-detection work is documented under `browser/docs/research/`. |
| `files/` | Secure file ingestion/extraction services and MCP tooling for file operations. | `module_setup.py`, `scripts/run_tests.py`, `backend/mcp/**`, `backend/extractors/**`. |
| `domains/` | Domain models (risk, SDA). | `module_setup.py`, `risk/`, `sda/`. Marketing is git submodule; keyring contains only type stubs (`__init__.pyi`). |
| `compliance/` | Documentation-only snapshot of code quality and CI/DI alignment. Compliance backend spec and historical standards research in `docs/research/`. | `module_setup.py`, `docs/README.md`, `docs/research/COMPLIANCE_BACKEND_SPEC.md`. Backend implementation TBD. |
| `nodes/` | Managed infrastructure processes, tunnel configuration, and automation for remote nodes. | `module_setup.py`, `scripts/setup_service.py`, `config/setup-service.yaml`. |
| `streams/` | Matrix messaging infrastructure (Synapse + Element). Stream processing experimentation. | `module_setup.py`, `config/matrix/`. Matrix homeserver configured; runtime stream processors dormant (per `streams/README.md:49`). |
| `ux/` | CMS app, shared Auth package, prototype UIs. | `module_setup.py`, `auth/`, `cms/`, `scripts/run_tests.py`. NextAuth rollout in-progress; legacy ES modules still active. |

## Cross-Cutting Policies

- Runner scripts (`run_*`, `scripts/run_tests.py`) use `base/backend/utils/runner_bootstrap.py` for venv bootstrapping and `base/scripts/env/paths.py` for import path setup; application packages must not mutate paths at import time.
- Each module owns a local `.venv` created with `uv venv --python 3.12`. No root virtual environment is provided.
- Setup scripts must log via stdlib `logging` and defer third-party imports until after dependencies are installed.
- Quality targets (mypy/ruff/test runners) must align with Python 3.12. Module-local configs derive from Base templates.
