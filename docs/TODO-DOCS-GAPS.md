# Documentation Gaps & TODOs

## High-Priority
- Compliance backend remains unimplemented (`compliance/backend/` does not exist). Continue tracking specification progress in `compliance/docs/research/CURRENT_IMPLEMENTATION_STATUS.md` and `compliance/docs/research/EXECUTIVE_ACTION_PLAN.md`. Implementation target: Q4 2025 - Q2 2026.
- Streams module has operational Matrix homeserver, but the module should be treated as dormant overall per `streams/README.md:49`. Continue documenting additional streaming capabilities (OBS, RDP, virtual displays) as they move from prototype to production.

## Submodule Access
- `.gitmodules` defaults to SSH URLs. HTTPS onboarding is partially documented in `docs/GUIDE-TOOLCHAIN-BOOTSTRAP.md` but focuses on toolchain setup rather than git submodule access patterns. Add explicit HTTPS clone examples for CI/read-only environments.

## Runners & Setup Scripts
- Each module README should list real runner scripts. Verified: root, base, browser, streams, compliance, files, nodes, domains, and ux all have `scripts/run_tests.py`. Several modules have MCP runners (base: ssh, dataops; files: filesys; nodes: launcher, setup; domains/marketing: research). Document MCP runners in respective module READMEs when missing.

## Quality Notes
- Root and module `mypy.ini` files now target Python 3.12. Keep Base templates authoritative when adding new modules.
- Continue to retire legacy references; record any newly discovered gaps here instead of leaving stale statements in place.

Owners should append or strike items as the modernization sweep progresses module by module.
