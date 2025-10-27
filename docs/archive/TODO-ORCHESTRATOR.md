# AMI-Orchestrator TODO (Work Plan)

Status legend: [ ] todo  [-] in-progress  [x] done  [!] blocked

## Toolchain & Setup Contract
- [-] Document and enforce single setup contract across modules
  - [x] Add orchestrator/docs: Architecture, Setup Contract, Quality, Bootstrap
  - [x] Add SETUP_CONTRACT.md in each module
  - [ ] Add CI task to validate contract conformance (no top-level 3rd‑party imports in module_setup.py)
- [ ] Submodule access guidance for CI/offline
  - [x] Document HTTPS alternative guidance
  - [ ] Provide example script to switch SSH→HTTPS remotes for CI

## Import/Path Discipline
- [-] Runner-only path setup; no ad-hoc sys.path in packages
  - [x] Capture policy in docs
  - [-] Update UX module_setup to delegate like others (no ami_path)
  - [ ] Audit runner scripts to ensure they set paths centrally via Base

## Module Setup Hygiene
- [-] Remove third-party imports before venv exists in module_setup.py
  - [ ] browser: defer yaml and replace loguru with logging
  - [ ] files: replace loguru with logging
  - [ ] node: replace loguru with logging
  - [x] streams: already delegating without 3rd‑party imports
  - [x] base: conforms by design
- [ ] compliance/domains: confirm non-setup status or add minimal delegating module_setup.py

## Lint/Type Targets
- [-] Align to Python 3.12 globally
  - [ ] Update root mypy.ini to python_version=3.12
  - [ ] Ensure Base template generates module-local mypy.ini with 3.12
  - [ ] Run sample checks (ruff + mypy) across modules post-alignment

## Runner Scripts & Docs Consistency
- [-] base/docs/MCP_SERVERS.md referenced run_mcp.py (fixed)
  - [x] Update docs to reflect programmatic startup and module-specific runners
- [ ] Validate all referenced `run_*` scripts exist and are documented

## Orchestrator Enhancements
- [ ] Optional: write per-module setup logs to artifacts/setup-<module>.log
- [ ] Optional: summarize failures with suggested next actions per module

## Documentation Backlog
- [ ] Fill missing docs referenced by root README: IMPORT_CONVENTIONS.md, MASTER_CODE_QUALITY_REPORT.md, QA.md, TYPE_IGNORE_AUDIT.md
- [x] Add reading map and gaps tracker

## Security & Compliance Notes
- [x] Prefer submodule update over pull; document SSH URL expectations
- [ ] Add note/examples for air-gapped bootstrap mirrors (uv/python toolchains)
