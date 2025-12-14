# Architecture Map

This document summarises the current module boundaries, responsibilities, and primary entry points. For deeper detail, follow the links to module READMEs and docs.

## Root Orchestrator

- **Responsibilities** – Bootstraps the toolchain, initialises submodules, and enforces the setup contract across modules.
- **Key entry points**
- `install.py` – One-time installer that initializes git submodules, registers shell aliases (`ami-run`, `ami-uv`), then runs `make setup-all`.
- `Makefile` – The standard build orchestrator. Each module has a `Makefile` with a `setup` target.
  - `scripts/run_tests.py` – Root test harness that bootstraps into module venv via `runner_bootstrap` and runs pytest if tests exist.

## Modules

| Module | Responsibilities | Primary entry points / notes |
| :--- | :--- | :--- |
| `base/` | Shared environment management, DataOps storage layer (async PostgreSQL, Dgraph, in-memory), FastMCP DataOps + SSH servers, security utilities. | `Makefile`, `scripts/run_tests.py`, `backend/mcp/dataops/dataops_server.py`, `backend/utils/runner_bootstrap.py`. |
| `browser/` | Managed Chromium provisioning and auditable browser automation tooling. | `Makefile`, `scripts/setup_chrome.py`, `backend/mcp/chrome/**`. |
| `files/` | Secure file ingestion/extraction services and MCP tooling for file operations. | `Makefile`, `scripts/run_tests.py`, `backend/mcp/**`, `backend/extractors/**`. |
| `domains/` | Domain models (risk, SDA). | `Makefile`, `risk/`, `sda/`. Marketing is git submodule; keyring contains only type stubs (`__init__.pyi`). |
| `compliance/` | Documentation-only snapshot of code quality and CI/DI alignment. Compliance backend spec and historical standards research in `docs/research/`. | `Makefile`, `docs/README.md`, `docs/research/COMPLIANCE_BACKEND_SPEC.md`. Backend implementation TBD. |
| `nodes/` | Managed infrastructure processes, tunnel configuration, and automation for remote nodes. | `Makefile`, `config/runtime.yaml`, `Procfile`. |
| `streams/` | Matrix messaging infrastructure (Synapse + Element). Stream processing experimentation. | `Makefile`, `config/matrix/`. Matrix homeserver configured; runtime stream processors dormant (per `streams/README.md:49`). |
| `ux/` | CMS app, shared Auth package, prototype UIs. | `Makefile`, `auth/`, `cms/`, `scripts/run_tests.py`. NextAuth rollout in-progress; legacy ES modules still active. |

## Cross-Cutting Policies

- Runner scripts (`run_*`, `scripts/run_tests.py`) use `base/backend/utils/runner_bootstrap.py` for venv bootstrapping and `base/scripts/env/paths.py` for import path setup; application packages must not mutate paths at import time.
- Each module owns a local `.venv` created with `uv venv --python 3.12`. No root virtual environment is provided.
- Setup scripts must log via stdlib `logging` and defer third-party imports until after dependencies are installed.
- Quality targets (mypy/ruff/test runners) must align with Python 3.12. Module-local configs derive from Base templates.
