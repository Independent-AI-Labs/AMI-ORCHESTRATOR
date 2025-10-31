# Open AMI

**Theoretical framework for building AI systems with formal safety guarantees and compliance-by-design.**

> **⚠️ STATUS**: OpenAMI is a research framework describing future capabilities. The production [AMI-ORCHESTRATOR](../../README.md) platform implements foundational infrastructure (DataOps, MCP servers, compliance mapping), but advanced OpenAMI features (SPNs, CSTs, self-evolution) remain in research phase (target Q4 2025 - Q2 2026).

## What This Is

Open AMI is a theoretical framework and long-term roadmap for self-evolving AI systems that can prove their own safety. Core concept: AI that improves itself through formally verified steps, with cryptographic proof it won't violate safety constraints.

## Current Status

**Research framework documented:**
- Four Pillars architecture: **Compliance** (regulatory mapping), **Integrity** (cryptographic audit trails), **Abstraction** (layered safety guarantees), **Dynamics** (controlled evolution) - [specifications](../../compliance/docs/research/OpenAMI/)
- Bootstrapping approaches for safe self-evolution - [learning/](../../learning/)
- Constraint preservation mechanisms (monotonic safety properties across system evolution)
- Compliance mapping: EU AI Act, ISO 42001, ISO 27001, NIST - [research docs](../../compliance/docs/research/)

**Production infrastructure (AMI-ORCHESTRATOR):**
- ✅ Multi-storage DataOps (Dgraph, PostgreSQL, PgVector, Redis, OpenBao, REST)
- ✅ MCP servers: DataOps (10 tools), SSH (4 tools), Browser (11 families), Files (27 tools)
- ✅ Cryptographic audit trails (UUID v7, immutable logging)
- ✅ 60+ integration tests, production-ready automation
- See [main README](../../README.md) for complete capabilities

**Research phase (estimated Q4 2025 - Q2 2026):**
- Secure Process Nodes (SPN): sandboxed execution environments with cryptographic attestation
- Cryptographic State Tokens (CST): tamper-proof state representation
- Formal verification integration: proof systems (Lean, Coq, or similar)
- Self-evolution engine: verified transformation pipelines
- Compliance MCP server with governance tools

## Documentation

**⚠️ Important**: OpenAMI documentation describes **theoretical/target architecture**, not current production code. For working capabilities, see [main README](../../README.md).

- [**GUIDE-FRAMEWORK.md**](./GUIDE-FRAMEWORK.md) - Theoretical framework overview and research directions
- [**SPEC-VISION.md**](./SPEC-VISION.md) - Vision for decision makers and advisors
- [**SPEC-ARCHITECTURE.md**](./SPEC-ARCHITECTURE.md) - Four-layer design (research/target)

## Research Foundation

Complete theoretical specifications and research:

**Bootstrapping Approaches** ([learning/](../../learning/)):
- [SYNTHESIS-OPENAMI-BOOTSTRAP.md](../../learning/SYNTHESIS-OPENAMI-BOOTSTRAP.md) - Unified framework
- [bootstrap.md](../../learning/bootstrap.md) - Gemini DSE-AI (deterministic self-evolution)
- [incremental.md](../../learning/incremental.md) - Claude formal verification approach
- [SECURITY-MODEL.md](../../learning/SECURITY-MODEL.md) - Threat model and protections

**OpenAMI Specifications** ([compliance/docs/research/OpenAMI/](../../compliance/docs/research/OpenAMI/)):
- [Architecture pillars](../../compliance/docs/research/OpenAMI/architecture/pillars.md) - Four Pillars detailed design
- [Compliance manifest](../../compliance/docs/research/OpenAMI/systems/compliance_manifest.md) - Formal specification system
- [OAMI protocol](../../compliance/docs/research/OpenAMI/systems/oami_protocol.md) - Communication protocol
- [Governance alignment](../../compliance/docs/research/OpenAMI/compliance/governance_alignment.md) - Standards mapping

**Implementation Planning**:
- [OPENAMI-COMPLIANCE-MAPPING.md](../../compliance/docs/research/OPENAMI-COMPLIANCE-MAPPING.md) - Standards integration
- [EXECUTIVE_ACTION_PLAN.md](../../compliance/docs/research/EXECUTIVE_ACTION_PLAN.md) - Implementation roadmap and timeline

## Getting Started

**For production infrastructure:**
See [AMI-ORCHESTRATOR README](../../README.md) for:
- Installation and setup instructions
- MCP server documentation and examples
- Current production capabilities (DataOps, SSH, Browser, Files)
- Integration tests and quality gates

**For OpenAMI research and vision:**
Start with [GUIDE-FRAMEWORK.md](./GUIDE-FRAMEWORK.md) to understand the theoretical framework, then explore:
- [SPEC-VISION.md](./SPEC-VISION.md) - Research value proposition and vision
- [SPEC-ARCHITECTURE.md](./SPEC-ARCHITECTURE.md) - Technical design (research/target)
- [Research specifications](../../compliance/docs/research/OpenAMI/) - Complete framework documentation
