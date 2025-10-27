# Reading Map (Where Things Live)

High-value docs by area:

## Root Level
- `ARCHITECTURE.md` — high-level platform vision and design
- `README.md` — product overview and quick start
- `CLAUDE.md` — agent guidelines and development rules

## Documentation (`docs/`)
- `README.md` — documentation index and reading order
- `GUIDE-ARCHITECTURE-MAP.md` — module boundaries, responsibilities, entry points
- `GUIDE-TOOLCHAIN-BOOTSTRAP.md` — uv + Python 3.12 setup guidance
- `SPEC-SETUP-CONTRACT.md` — contract between root and modules
- `POLICY-QUALITY.md` — quality policy and guardrails
- `STATUS-INTEGRATION.md` — integration status tracker
- `TODO-DOCS-GAPS.md` — documentation gaps and backlog
- `TODO-NEXT-STEPS.md` — next steps and suggested owners
- `specs/` — specifications and implementation plans (auth, DataOps, security, automation, ISMS)
- `archive/` — historical documents, completed work, progress reports
- `openami/` — OpenAMI framework documentation

## Module Documentation

### Base (`base/`)
- `README.md` — core services, DataOps storage, FastMCP servers, security utilities

### Browser (`browser/`)
- `README.md` — module overview
- `CODE_EXCEPTIONS.md` — intentional deviations
- `docs/research/` — experimental anti-detection work

### Files (`files/`)
- `README.md` — capabilities and operations
- `REQUIREMENTS.md` — functional requirements

### Nodes (`nodes/`)
- `README.md` — specification and node management
- `SPEC-TUNNEL.md` — tunnel specification
- `tests/README.md` — test execution guidance and runners

### Streams (`streams/`)
- `README.md` — module overview
- `REQUIREMENTS.md` — functional scope

### Compliance (`compliance/`)
- `README.md` — compliance framework
- `docs/` — reference material

### Domains (`domains/`)
- `risk/` — risk domain models
- `sda/` — SDA domain models

## Suggested Reading Order

When onboarding or making changes:
1. `docs/GUIDE-ARCHITECTURE-MAP.md`
2. `docs/SPEC-SETUP-CONTRACT.md`
3. `docs/GUIDE-TOOLCHAIN-BOOTSTRAP.md`
4. `docs/POLICY-QUALITY.md`
5. `docs/STATUS-INTEGRATION.md`
6. `docs/README.md` — for complete documentation index
