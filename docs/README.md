# Documentation Index

The `docs/` folder captures orchestrator-wide policies and the modernization state of each module. Use the table below to jump to the artefacts most relevant to the current compliance and engineering workstream.

## Active Documentation

| Topic | File |
| --- | --- |
| Architecture and ownership map | `GUIDE-ARCHITECTURE-MAP.md` |
| Setup contract between root and modules | `SPEC-SETUP-CONTRACT.md` |
| Toolchain bootstrap guidance (uv + Python 3.12) | `GUIDE-TOOLCHAIN-BOOTSTRAP.md` |
| Quality policy & guardrails | `POLICY-QUALITY.md` |
| Integration status tracker | `STATUS-INTEGRATION.md` |
| Documentation gaps & backlog | `TODO-DOCS-GAPS.md` |
| Reading map (where things live) | `GUIDE-READING-MAP.md` |

## Specifications & Implementation Plans

All specifications and implementation plans have been moved to `specs/`:

- **Authentication:** `specs/SPEC-AUTH.md`, `specs/SPEC-NEXTAUTH-INTEGRATION.md`, `specs/TODO-AUTH.md`
- **DataOps:** `specs/SPEC-DATAOPS-DATA-ACCESS.md`, `specs/SPEC-STORAGE.md`
- **Security:** `specs/SPEC-HARDEN.md`, `specs/SPEC-REMEDIATION.md`
- **Code Quality:** `specs/SPEC-SYNTAX.md`
- **Automation:** `specs/SPEC-AUTOMATION-V2.md`, `specs/SPEC-AUTOMATION-TESTS.md`
- **ISMS:** `specs/SPEC-ISMS-FUNCTIONALITY.md`

## Archived Documents

Historical documents, completed work plans, and assessments have been moved to `archive/`:

- Architecture assessments, completed TODOs, progress reports
- See `archive/` directory for full list

## Suggested Reading Order

When onboarding a change:
1. `GUIDE-ARCHITECTURE-MAP.md`
2. `SPEC-SETUP-CONTRACT.md`
3. `GUIDE-TOOLCHAIN-BOOTSTRAP.md`
4. `POLICY-QUALITY.md`
5. `STATUS-INTEGRATION.md`
6. `TODO-DOCS-GAPS.md`

## Additional Resources

- **Compliance reference material:** `compliance/docs/`
- **Module-specific documentation:** See each module's README
- **OpenAMI framework:** `docs/openami/`
