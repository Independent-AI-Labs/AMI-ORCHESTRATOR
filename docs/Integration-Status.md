# Integration Status (Initial)

Scope: Current operational state of module setup under orchestrator control, with observed issues to be addressed by code changes inside the respective modules (not here).

Summary
- Toolchain: `uv` + Python 3.12 bootstrap script present and working (`scripts/bootstrap_uv_python.py`).
- Orchestrator: `module_setup.py` initializes submodules, ensures toolchain, and drives per-module setup with `uv run --python 3.12`.
- Base: Provides `AMIModuleSetup`, `PathFinder`, and `EnvironmentSetup` as the central contract.

Per-module setup observations
- base: Uses centralized setup; OK.
- streams: Delegates to base `module_setup.py`; OK.
- browser: Has `module_setup.py`; ensure third-party imports are deferred until after venv creation (verify).
- files: Has `module_setup.py`; ensure third-party imports are deferred until after venv creation (verify).
- node: `module_setup.py` imports `loguru` at top-level (violates setup policy: third-party imports before venv). Use stdlib logging in setup script or defer import until after deps install.
- ux: Uses `scripts/ami_path.py` for path discovery; previously failed to find module root on some paths. Align with Base `PathFinder` for consistency.
- compliance: No `module_setup.py`. Documented as non-setup module for now; decide whether to add a no-op setup or a contract-compliant setup delegating to Base.
- domains: No `module_setup.py`. Same as compliance.

Documentation mismatches (examples)
- `base/docs/MCP_SERVERS.md` references `base/scripts/run_mcp.py`, which does not exist; update doc or add the runner.
- Root `README.md` references `IMPORT_CONVENTIONS.md`, `MASTER_CODE_QUALITY_REPORT.md`, `QA.md`, `TYPE_IGNORE_AUDIT.md` which are not present. Track in Docs-Gaps.

Next validation steps
- Align module setup scripts to use Base `AMIModuleSetup` and avoid third-party imports pre-venv.
- Ensure all MCP runner references in docs correspond to real scripts; update or add wrappers where missing.
- Converge typing configs to Python 3.12 via Base templates across modules.
