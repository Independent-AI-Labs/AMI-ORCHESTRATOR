# Reading Map (Where Things Live)

High-value docs by area
- Root
  - `ARCHITECTURE.md` — high-level platform vision and design.
  - `README.md` — product overview and quick start.
  - `TODO_IDP.md` — IDP backlog and tasks.
- Base
  - `README.md` — core services and runners.
  - `docs/MCP_SERVERS.md` — server interfaces and usage (note: references to `run_mcp.py` require update).
  - `SECURITY*.md` — security architecture, implementation summary, verification report.
  - `CODE_EXCEPTIONS.md` — intentional deviations not to be “fixed”.
- Browser
  - `README.md` — module overview.
  - `CODE_EXCEPTIONS.md`, `CODE_QUALITY_ISSUES.md`, `CONFORMITY.md` — constraints and quality notes.
- Files
  - `README.md`, `REQUIREMENTS.md`, `MIGRATION_GUIDE.md` — capabilities and operations.
- Node
  - `README.md`, `SPEC-TUNNEL.md`, `FIXME.md` — specification and known issues.
  - `tests/README.md` — test execution guidance and runners.
- Streams
  - `REQUIREMENTS.md` — functional scope.
- Compliance / Domains
  - `CONFORMITY.md`, `CODE_QUALITY_ISSUES.md`, `REQUIREMENTS.md` — policy and domain specifics.

Cross-cutting
- Setup contracts live in `SETUP_CONTRACT.md` in each module and `/docs/Setup-Contract.md` at root.
- Toolchain bootstrapping is defined in `/docs/Toolchain-Bootstrap.md`.
- Quality policy and gaps are tracked in `/docs/Quality-Policy.md` and `/docs/Docs-Gaps.md`.
