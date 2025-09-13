# Documentation Gaps & TODOs

High-priority gaps
- Missing docs referenced in root `README.md`: `IMPORT_CONVENTIONS.md`, `MASTER_CODE_QUALITY_REPORT.md`, `QA.md`, `TYPE_IGNORE_AUDIT.md`.
- [Resolved] `base/docs/MCP_SERVERS.md` no longer references a non-existent runner; it now describes programmatic startup.

Submodule access
- `.gitmodules` uses SSH URLs. For read-only clones or CI without SSH keys, provide HTTPS equivalents in documentation (example command snippet), or document how to switch remotes.

Type target mismatch
- Root `mypy.ini` previously set Python 3.11 while `ruff.toml` targets py312. Standardize on 3.12. Prefer module-level `mypy.ini` generated from Base template; consider minimizing root typing until needed.

Setup scripts consistency
- Ensure every code path described in docs has a corresponding `run_*` script and vice versa. Add stubs if needed or annotate WIP.

Owners & follow-ups
- Assign module owners to confirm or correct runner lists and fill missing doc references.
- Track module-specific deviations from the Setup Contract in a short checklist within each module (see `SETUP_CONTRACT.md` files).
