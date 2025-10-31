# Open AMI

**Framework for building AI systems with formal safety guarantees, compliance-by-design, and complete auditability.**

> **⚠️ STATUS**: OpenAMI is a research framework describing future capabilities. The production [AMI-ORCHESTRATOR](../../README.md) platform implements foundational infrastructure (DataOps, MCP servers, audit trails), but advanced OpenAMI features (formal verification, self-modification) remain in research phase (target Q4 2025 - Q2 2026).

---

## What This Is

Open AMI is a framework and long-term roadmap for self-evolving AI systems that can prove their own safety. Core concept: AI that improves itself through formally verified steps, with cryptographic proof and human oversight ensuring it won't violate safety constraints. Every decision and change is traceable to specific data, code, and responsible individuals.

---

## Current Status

### ✅ Production Infrastructure (AMI-ORCHESTRATOR - OPERATIONAL TODAY)

**Audit and Provenance**:
- ✅ Cryptographic audit trails (UUID v7, immutable logging)
- ✅ Complete provenance tracking for all operations
- ✅ Multi-storage DataOps (Dgraph, PostgreSQL, PgVector, Redis, OpenBao, REST)
- ✅ Access control and authentication systems

**MCP Servers** (50+ production tools):
- ✅ DataOps server (10 tools): CRUD, search, query
- ✅ SSH server (4 tools): command execution, file transfer
- ✅ Browser server (11 families): navigation, interaction, scraping
- ✅ Files server (27 tools): file operations, search, metadata

**Quality Assurance**:
- ✅ 60+ integration tests
- ✅ Production-ready automation
- ✅ Compliance mapping documentation

See [main README](../../README.md) for complete production capabilities.

### 📋 Research Phase (Estimated Q4 2025 - Q2 2026)

**Advanced Features**:
- Isolated execution environments: sandboxed processes with cryptographic attestation
- Cryptographically signed state snapshots: tamper-proof state representation
- Formal verification integration: proof systems (Lean, Coq, or similar)
- Self-modification with verification: verified transformation pipelines
- Compliance MCP server with governance tools

**Research Framework Documented**:
- Four design principles: **Compliance** (regulatory mapping), **Integrity** (cryptographic audit trails), **Abstraction** (layered safety guarantees), **Dynamics** (controlled evolution)
- Constraint preservation mechanisms (safety rules that can never be weakened)
- Compliance mapping: EU AI Act, ISO 42001, ISO 27001, NIST

---

## Documentation

**⚠️ Important**: OpenAMI documentation describes **theoretical/target architecture**, not current production code. For working capabilities, see [main README](../../README.md).

- [**SPEC-VISION.md**](./SPEC-VISION.md) - Vision for decision makers and advisors
- [**GUIDE-FRAMEWORK.md**](./GUIDE-FRAMEWORK.md) - Theoretical framework overview and research directions
- [**SPEC-ARCHITECTURE.md**](./SPEC-ARCHITECTURE.md) - Four-layer design (research/target)

---

## Research Foundation

Complete theoretical specifications and research:

### Bootstrapping Approaches

External research repositories:
- [SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md) - Unified framework
- [bootstrap.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/bootstrap.md) - Deterministic evolution approach
- [incremental.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/incremental.md) - Formal verification approach
- [SECURITY-MODEL.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SECURITY-MODEL.md) - Threat model and protections

### OpenAMI Specifications

External compliance research repository:
- [Architecture pillars](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/pillars.md) - Four design principles detailed
- [Compliance requirements specification](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/compliance_manifest.md) - Formal specification system
- [Inter-component communication protocol](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/oami_protocol.md) - Communication protocol
- [Governance alignment](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/compliance/governance_alignment.md) - Standards mapping

### Implementation Planning

- [OPENAMI-COMPLIANCE-MAPPING.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OPENAMI-COMPLIANCE-MAPPING.md) - Standards integration
- [EXECUTIVE_ACTION_PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/EXECUTIVE_ACTION_PLAN.md) - Implementation roadmap and timeline

---

## Getting Started

### For Production Infrastructure (Available Now)

See [AMI-ORCHESTRATOR README](../../README.md) for:
- Installation and setup instructions
- MCP server documentation and examples
- Current production capabilities (DataOps, SSH, Browser, Files)
- Audit trail implementation (base/backend/dataops/security/audit_trail.py)
- Integration tests and quality gates

### For OpenAMI Research and Vision

Start with [SPEC-VISION.md](./SPEC-VISION.md) to understand the research vision and business value, then explore:
- [GUIDE-FRAMEWORK.md](./GUIDE-FRAMEWORK.md) - Theoretical framework and research directions
- [SPEC-ARCHITECTURE.md](./SPEC-ARCHITECTURE.md) - Technical design (research/target)
- [Research specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/tree/main/docs/research/OpenAMI/) - Complete framework documentation

---

**Production-ready infrastructure with audit trails exists today. Advanced verification features are in research phase.**
