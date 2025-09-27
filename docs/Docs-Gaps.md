# Documentation Gaps & TODOs

## High-Priority
- Compliance backend documentation leads implementation: the package described in `compliance/docs/COMPLIANCE_BACKEND_SPEC.md` is not yet present. Track progress in `compliance/docs/CURRENT_IMPLEMENTATION_STATUS.md` as soon as scaffolding begins.
- Keep `streams/README.md` updated as soon as runtime services move beyond the current dormant state.

## Submodule Access
- `.gitmodules` defaults to SSH URLs. Document HTTPS fallback commands in onboarding material for environments without SSH keys (CI, read-only clones).

## Runners & Setup Scripts
- Verify each module README lists the real runner scripts (`scripts/run_tests.py`, forthcoming MCP runners). Streams and compliance currently lack runnable entry points and should say so explicitly.

## Quality Notes
- Root and module `mypy.ini` files now target Python 3.12. Keep Base templates authoritative when adding new modules.
- Continue to retire legacy references; record any newly discovered gaps here instead of leaving stale statements in place.

Owners should append or strike items as the modernization sweep progresses module by module.
