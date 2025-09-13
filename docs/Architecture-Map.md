# Architecture Map

Purpose: Provide a concise map of the orchestrator and module boundaries, their responsibilities, and primary entrypoints, without duplicating per-module READMEs.

- Orchestrator (root)
  - Responsibilities: submodule orchestration, bootstrap of toolchain (uv + Python 3.12), unified setup runner, cross-module policy.
  - Entrypoints:
    - `module_setup.py` — initializes submodules, ensures toolchain, runs each module’s setup.
    - `scripts/bootstrap_uv_python.py` — trusted install path for `uv` and Python 3.12 toolchain.

- Base (`base/`)
  - Responsibilities: core platform contracts, shared utils, path + environment setup centralization, security model, MCP servers.
  - Entrypoints: see module README (runners are module-specific).
  - Shared APIs: `base/backend/utils/{path_finder.py, environment_setup.py, path_utils.py}`.

- Browser (`browser/`)
  - Responsibilities: auditable browser automation (MCP).
  - Entrypoints: see module README.

- Files (`files/`)
  - Responsibilities: secure local file operations (MCP), analysis utilities.
  - Entrypoints: see module README.

- Streams (`streams/`)
  - Responsibilities: streaming and real-time pipelines.
  - Entrypoints: module-specific runners (TBD), see README.

- Node (`node/`)
  - Responsibilities: network tunnel/infra MCP server(s) per SPEC-TUNNEL.
  - Entrypoints: see `README.md` and `tests/README.md`.

- UX (`ux/`)
  - Responsibilities: UI/UX concepts and related tooling.

- Compliance (`compliance/`) and Domains (`domains/`)
  - Responsibilities: policy frameworks, domain models, risk/requirements.

Cross-cutting policies
- Runner-only path/import initialization: code executed via `run_*` and `run_tests` scripts sets up Python paths; application packages avoid ad-hoc path mutations.
- Each module owns its `.venv` using `uv`; orchestrator does not provide a root venv.
- Python 3.12 as the standard runtime and lint/type-check target.
