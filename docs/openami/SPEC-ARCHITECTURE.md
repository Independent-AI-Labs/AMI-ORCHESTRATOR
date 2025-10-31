# Open AMI System Architecture

**For**: Technical Leaders, Architects, Senior Engineers
**Reading Time**: 15-20 minutes
**Prerequisites**: [GUIDE-FRAMEWORK.md](./GUIDE-FRAMEWORK.md)

> **⚠️ CRITICAL NOTE**: This document describes the **TARGET ARCHITECTURE** for Open AMI, not the current production state of AMI-ORCHESTRATOR. Most components described here are in **research/specification phase** (Q4 2025 - Q2 2026). For actual production capabilities, see the [main README](../../README.md) and [Implementation Reality Check](#implementation-reality-check) at the end of this document.

> **⚠️ COMPLEXITY WARNING**: This architecture involves significant unsolved research challenges, including:
> - Formal verification of neural networks at scale (open research problem)
> - Specification of "safety" in formal logic for natural language domains
> - Meta-verification (who verifies the verifier after evolution?)
> - Computational feasibility of proof generation for complex AI systems

---

## Executive Summary

Open AMI proposes a **four-layer architecture** that integrates **four foundational pillars** for trustworthy, self-evolving AI systems. The research framework aims to combine:

1. **Formal safety assurances** (mathematical verification techniques, immutable constraints)
2. **Verified evolution** (validation before deployment)
3. **Distributed verification** (Byzantine fault-tolerant consensus)
4. **Complete accountability** (cryptographic audit trail - partially implemented)

**Research Goal**: Explore approaches for AI capability growth while maintaining verifiable alignment with specified safety constraints.

**Key Challenge**: Formal methods typically apply to deterministic systems, but AI models exhibit stochastic and emergent behavior that resists formal analysis.

---

## The Four Pillars

Every component in Open AMI is designed around four inseparable pillars:

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ COMPLIANCE  │  INTEGRITY  │ ABSTRACTION │  DYNAMICS   │
├─────────────┼─────────────┼─────────────┼─────────────┤
│ Regulatory  │ Crypto-     │ Multi-level │ Controlled  │
│ alignment,  │ graphically │ representa- │ adaptation  │
│ ethical,    │ verified    │ tions for   │ with        │
│ legal safe  │ data &      │ transparen- │ stability   │
│ by design   │ compute     │ cy at scale │ guarantees  │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

**Compliance**: Formal specification of ethical, legal, safety requirements enforced at runtime
**Integrity**: Cryptographic guarantees for data/computation correctness
**Abstraction**: Multi-level representations (weights → concepts) for transparency
**Dynamics**: Adaptive learning with stability guarantees, preventing catastrophic forgetting

**Implementation Status**:
- Compliance: Documented in [compliance/docs/research/OpenAMI/](../../compliance/docs/research/OpenAMI/)
- Integrity: Partial (audit_trail.py in production)
- Abstraction: Research phase
- Dynamics: Research phase

---

## The Four-Layer Architecture

Open AMI is structured as four bidirectional layers:

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: GOVERNANCE                                            │
│  ├─ Policy Definition & Enforcement                             │
│  ├─ Human Oversight & Control                                   │
│  ├─ Compliance Manifest (formal specification)                  │
│  └─ Risk Management & Audit                                     │
└────────────────────────────┬────────────────────────────────────┘
                             ↕ (bidirectional control/feedback)
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: INTELLIGENCE                                          │
│  ├─ ML Models & Algorithms                                      │
│  ├─ Evolution Engine (verified transformations)                 │
│  ├─ Proof Generators (formal verification)                      │
│  └─ Knowledge Graphs                                            │
└────────────────────────────┬────────────────────────────────────┘
                             ↕ (bidirectional execution/verification)
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: OPERATIONAL (SDS)                                     │
│  ├─ Secure Process Nodes (isolated execution)                   │
│  ├─ Distributed Verification (BFT consensus)                    │
│  ├─ Cryptographic State Tokens (tamper-evident state)           │
│  └─ OAMI Protocol (secure communication)                        │
└────────────────────────────┬────────────────────────────────────┘
                             ↕ (bidirectional state/operations)
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: FOUNDATION                                            │
│  ├─ Layer 0 Axioms (immutable safety constraints)               │
│  ├─ Core Principles (execution invariants)                      │
│  ├─ Process Theory (formal models)                              │
│  └─ OAMI Protocol Specification                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Foundation

### Purpose

Provides **immutable safety constraints** that can never be modified by the AI, regardless of evolution.

### Key Components

#### Layer 0 Axioms

> **📋 SPECIFICATION ONLY** - Not yet implemented. Target: Q4 2025.

Formal safety axioms expressing constraints like:
- No deception
- No harm to humans
- Respect for human autonomy
- Explainability requirements
- Fairness constraints
- Verifiability requirements

**Proposed Approach**: Formalize in theorem prover (Lean/Coq) as immutable constraints loaded from secure storage during every verification.

**Research Challenge**: Translating high-level ethical principles ("no harm") into formal logical predicates that can be mechanically checked is an unsolved problem.

**Reference**: See [compliance/docs/research/OpenAMI/architecture/pillars.md](../../compliance/docs/research/OpenAMI/architecture/pillars.md) for theoretical framework.

#### Core Principles

Immutable execution principles:
- Deterministic execution (same input → same output)
- Complete traceability (every action logged)
- Hypothesis-driven evolution (changes require justification)
- Empirical validation (test before deploy)
- Formal verification (prove safety properties)
- Distributed consensus (no single point of failure)
- Rollback capability (can undo changes)
- Human override (humans have final authority)

**Current Status**: Documented principles; not enforced architecturally.

#### Process Theory

Formal mathematical models for goals, processes, and learning. Includes:
- Goal structures (hierarchical representations)
- Process models (state machines for behavior)
- Learning theory (knowledge acquisition)
- Cognitive maps (multi-level abstractions)

**Reference**: [compliance/docs/research/OpenAMI/architecture/process_theory.md](../../compliance/docs/research/OpenAMI/architecture/process_theory.md)

---

## Layer 2: Operational Layer (SDS)

### Purpose

Provides **verifiable, isolated execution** for all AI operations through the Secure Distributed System (SDS).

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Coordination Layer                                         │
│  Manages groups of SPNs for complex workflows              │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  Secure Process Nodes (SPNs)                                │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐              │
│  │SPN 1│  │SPN 2│  │SPN 3│  │SPN 4│  │SPN 5│  ...         │
│  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘              │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  DataOps Layer (✅ OPERATIONAL)                              │
│  Postgres│Dgraph│Redis│Vault│MongoDB│PgVector|...          │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### Secure Process Nodes (SPNs)

> **🟡 IMPLICIT ONLY** - Currently realized through module isolation (base/, browser/, files/, nodes/). Explicit SPN abstraction: Target Q4 2025.

**Concept**: Isolated execution environments running AI operations with integrity guarantees.

**Proposed Capabilities**:
- Containerized/TEE-based isolation
- Local compliance checks against Compliance Manifest
- Integrity verification (input/output validation)
- Cryptographic operations (signing, encryption)
- State management via Cryptographic State Tokens (CSTs)

**Current Reality**: Module-level isolation via separate Python packages. No explicit SPN abstraction, no CSTs, no formal verification.

**Reference**: [process_theory.md](../../compliance/docs/research/OpenAMI/architecture/process_theory.md)

#### Coordination Processes

> **📋 SPECIFICATION ONLY** - Not yet implemented. Target: Q1 2026.

**Concept**: Coordinate groups of SPNs for distributed operations.

**Proposed Capabilities**:
- Distribute work across multiple SPNs
- Aggregate verification results via Byzantine Fault Tolerance (4/5 consensus)
- Enforce system-wide policies from Governance Layer
- Interface between Operational and Intelligence layers

**Research Challenge**: BFT provides fault tolerance but doesn't prevent coordinated manipulation by correctly-functioning-but-malicious nodes.

#### Cryptographic State Tokens (CSTs)

> **📋 SPECIFICATION ONLY** - Not yet implemented. Target: Q4 2025.

**Concept**: Cryptographically signed snapshots of SPN states for audit and rollback.

**Proposed Structure**:
- State snapshot (model weights, parameters, configuration)
- Cryptographic signature (HSM-signed)
- Timestamp (UUID v7 for ordering)
- Parent CST hash (forms provenance chain)

**Current Reality**: Basic audit logging exists ([audit_trail.py](../../base/backend/dataops/security/audit_trail.py)) but doesn't implement full CST concept.

---

## Layer 3: Intelligence

### Purpose

Hosts ML models, learning algorithms, and the **self-evolution engine** with formal verification.

### Key Components

#### ML Models & Algorithms

Standard machine learning models (neural networks, transformers, etc.) running within SPNs.

**Current**: Various models can run via MCP servers; no SPN abstraction yet.

#### Evolution Engine

> **📋 SPECIFICATION ONLY** - Not yet implemented. Target: Q1-Q2 2026.

**Concept**: AI proposes its own improvements, which are verified before deployment.

**Proposed 8-Step Protocol** (see [SYNTHESIS-OPENAMI-BOOTSTRAP.md](../../learning/SYNTHESIS-OPENAMI-BOOTSTRAP.md)):
1. **Analyze**: Identify improvement opportunity
2. **Design**: Specify change in high-level language
3. **Compile**: Transform to low-level operations
4. **Test**: Empirical validation against hypothesis
5. **Prove**: Generate formal safety proof
6. **Verify**: Distributed proof checking (BFT)
7. **Log**: Create audit entry with justification + proof
8. **Activate**: Deploy if governance approves

**Research Challenges**:
- Proof generation for neural networks is computationally infeasible at scale
- Specification problem: formalizing "improvement" and "safety"
- Who verifies the verifier after it evolves? (infinite regress)

#### Proof Generators/Verifiers

> **📋 SPECIFICATION ONLY** - Not yet implemented. Target: Q1 2026.

**Concept**: Generate and check formal proofs that AI transformations preserve safety properties.

**Proposed Approach**: Integrate with theorem provers (Lean, Coq, Isabelle) to generate proofs that new model satisfies Layer 0 Axioms.

**Research Challenge**: Automated theorem proving for complex systems is undecidable (Halting Problem). Proof generation may not terminate or may require prohibitive computational resources.

---

## Layer 4: Governance

### Purpose

Human oversight, policy enforcement, and compliance management.

### Key Components

#### Compliance Manifest

> **📋 SPECIFICATION ONLY** - Not yet implemented. Target: Q1 2026.

**Concept**: Formal specification of all safety, ethical, and regulatory requirements.

**Proposed Contents**:
- Layer 0 Axioms (from Layer 1)
- Regulatory mappings (EU AI Act, ISO 42001, NIST AI RMF)
- Risk assessments and mitigation strategies
- Human oversight requirements
- Audit and reporting obligations

**Current Status**: Compliance research documented in [compliance/docs/research/](../../compliance/docs/research/). No runtime enforcement mechanism.

**Reference**: [compliance_manifest.md](../../compliance/docs/research/OpenAMI/systems/compliance_manifest.md)

#### Human Oversight Interfaces

Dashboards and controls for human operators to:
- Monitor AI operations in real-time
- Review and approve/reject evolution proposals
- Override AI decisions when necessary
- Conduct audits and investigations
- Update policies (within Layer 0 Axiom constraints)

**Current Status**: Not implemented. Target: Q2 2026.

---

## The Evolution Protocol

### Unified 8-Step Process

Combines deterministic testing (Gemini DSE-AI) with formal verification (Claude) into a single evolution cycle:

```
┌──────────────────────────────────────────────────────────┐
│ 1. ANALYZE: Identify improvement trigger                │
│ 2. DESIGN: Specify change in high-level language        │
│ 3. COMPILE: Transform to executable operations          │
│ 4. TEST: Empirical validation                           │
│ 5. PROVE: Generate formal safety proof                  │
│ 6. VERIFY: Distributed proof checking (BFT)             │
│ 7. LOG: Create audit entry (justification + proof)      │
│ 8. ACTIVATE: Deploy if governance approves              │
└──────────────────────────────────────────────────────────┘
```

**Status**: Entirely theoretical. See [GUIDE-FRAMEWORK.md](./GUIDE-FRAMEWORK.md) for details.

### Constraint Preservation

**Principle**: Every evolution step must validate against **original** Layer 0 Axioms (not evolved versions).

**Mechanism**:
- Layer 0 Axioms stored in immutable storage
- Proof generator must prove new model satisfies **original** axioms
- 4/5 independent verifiers must agree (Byzantine consensus)
- Only then is evolution approved

**Research Challenge**: Assumes proof system itself doesn't have bugs. After 1000 evolutions, how do we trust the proof checker? (Meta-verification problem)

---

## Integration with AMI-ORCHESTRATOR

### Current Production Infrastructure

**What EXISTS today**:

1. **DataOps** (✅ OPERATIONAL)
   - UnifiedCRUD interface
   - 9 storage backends (Postgres, Dgraph, MongoDB, Redis, Vault, OpenBao, etc.)
   - See [base/backend/dataops/](../../base/backend/dataops/)

2. **MCP Servers** (✅ OPERATIONAL)
   - DataOps server (10 tools): CRUD, search, query
   - SSH server (4 tools): command execution, file transfer
   - Browser server (11 families): navigation, interaction, scraping
   - Files server (27 tools): file operations, search, metadata
   - See [README.md](../../README.md#mcp-integration)

3. **Audit Trail** (✅ PARTIAL)
   - Basic immutable logging with UUID v7
   - See [audit_trail.py](../../base/backend/dataops/security/audit_trail.py)
   - **Missing**: CSTs, formal proofs, justification triad

4. **Module Isolation** (✅ IMPLICIT)
   - Separate packages: base/, browser/, compliance/, domains/, files/, nodes/, streams/
   - **Missing**: Explicit SPN abstraction, TEE support, formal verification

### Migration Path

**Phase 1 (Q4 2025)**: Foundation
- Formalize Layer 0 Axioms in Lean/Coq
- Create SPN abstraction wrapping existing modules
- Implement CST generation for audit trail

**Phase 2 (Q1 2026)**: Verification
- Integrate proof generators/verifiers
- Implement distributed verification (BFT)
- Build Compliance Manifest backend

**Phase 3 (Q2 2026)**: Evolution
- Implement evolution engine
- Build Governance Layer interfaces
- Deploy pilot self-evolution experiments

**Phase 4 (Q3 2026+)**: Production
- Scale formal verification
- Harden security (TEEs, HSMs)
- Production deployments

---

## Security Considerations

### Threat Model

See [SECURITY-MODEL.md](../../learning/SECURITY-MODEL.md) for full threat model.

**Key Threats**:
1. **Specification gaming**: AI proves compliance while violating intent
2. **Proof system bugs**: Vulnerabilities in theorem prover or proof checker
3. **Coordinated manipulation**: 3+ SPNs colluding to bypass BFT
4. **Side-channel attacks**: Leaking information via timing, power, etc.
5. **Supply chain attacks**: Compromised dependencies or hardware

**Mitigations**:
- Multiple independent proof checkers
- Diverse SPN implementations (defense in depth)
- HSM-backed cryptographic operations
- Regular security audits and penetration testing
- Formal verification of proof checker itself (meta-verification)

### Cryptographic Primitives

**Required**:
- Digital signatures (Ed25519 or ECDSA)
- Hash functions (SHA-256 or BLAKE3)
- Message authentication codes (HMAC)
- Optional: Zero-knowledge proofs for privacy

**Current Status**: Basic cryptographic primitives used for audit trail. No HSM integration yet.

---

## Performance Considerations

> **⚠️ WARNING**: Performance estimates below are **speculative** and not based on actual benchmarks. Formal verification of complex AI systems may be computationally infeasible.

### Estimated Overheads (Speculative)

- **Proof generation**: Unknown (could be seconds to days, or may not terminate)
- **Proof verification**: Unknown (depends on proof complexity)
- **BFT consensus**: 1-10 seconds (network latency)
- **CST creation**: <1 second (signing + storage)
- **Audit logging**: <100ms (current implementation)

### Scalability Challenges

1. **Proof generation doesn't scale**: Formal verification of neural networks with millions of parameters is an open research problem
2. **Storage requirements**: Full provenance chain grows linearly with evolution steps
3. **Network overhead**: Distributed verification requires synchronization across SPNs

**Mitigation Strategies** (proposed, not validated):
- Hierarchical verification (prove subcomponents separately)
- Proof caching and reuse
- Incremental verification (prove only changed components)
- Approximate verification (statistical guarantees instead of formal proofs)

---

## Implementation Reality Check

### What EXISTS Today (AMI-ORCHESTRATOR Production)

- ✅ UnifiedCRUD with 9 storage backends (Postgres, Dgraph, MongoDB, Redis, Vault, etc.)
- ✅ MCP servers: DataOps, SSH, Browser, Files (50+ tools total)
- ✅ Basic audit trail (base/backend/dataops/security/audit_trail.py)
- ✅ Module-level isolation (base/, browser/, files/, nodes/)
- ✅ 60+ integration tests, production automation

### What DOES NOT Exist (Research/Specification Phase)

- ❌ Layer 0 Axioms in Lean/Coq
- ❌ Core Principles enforcement
- ❌ SPNs (Secure Process Nodes) abstraction
- ❌ Coordination Processes
- ❌ CSTs (Cryptographic State Tokens)
- ❌ Compliance Manifest backend
- ❌ Evolution Engine (high-level → low-level transformation)
- ❌ Proof Generator/Verifier
- ❌ Self-Evolution capability
- ❌ Full OAMI Protocol (only basic MCP response model)
- ❌ Byzantine consensus verification
- ❌ Complete cryptographic provenance chain
- ❌ Governance Layer interfaces

**For actual production capabilities**, see [AMI-ORCHESTRATOR README](../../README.md).

---

## Further Reading

### OpenAMI Research

- [GUIDE-FRAMEWORK.md](./GUIDE-FRAMEWORK.md) - Theoretical framework overview
- [SPEC-VISION.md](./SPEC-VISION.md) - Research vision and value proposition
- [compliance/docs/research/OpenAMI/](../../compliance/docs/research/OpenAMI/) - Detailed specifications

### Bootstrapping Approaches

- [SYNTHESIS-OPENAMI-BOOTSTRAP.md](../../learning/SYNTHESIS-OPENAMI-BOOTSTRAP.md) - Unified framework
- [bootstrap.md](../../learning/bootstrap.md) - Gemini DSE-AI approach
- [incremental.md](../../learning/incremental.md) - Claude formal verification approach
- [SECURITY-MODEL.md](../../learning/SECURITY-MODEL.md) - Threat model and protections

### Standards & Compliance

- [OPENAMI-COMPLIANCE-MAPPING.md](../../compliance/docs/research/OPENAMI-COMPLIANCE-MAPPING.md) - Standards integration
- [EXECUTIVE_ACTION_PLAN.md](../../compliance/docs/research/EXECUTIVE_ACTION_PLAN.md) - Implementation roadmap

### Production Infrastructure

- [AMI-ORCHESTRATOR README](../../README.md) - Current production capabilities
- [DataOps Documentation](../../base/backend/dataops/README.md) - Storage abstraction
- [MCP Integration Guide](../../README.md#mcp-integration) - MCP servers

---

**Last Updated**: 2025-10-31
**Version**: 2.0.0 (Streamlined, removed excessive pseudo-code)
**Status**: TARGET ARCHITECTURE - Most components in research phase (Q4 2025 - Q2 2026)

---

**Questions?** See [compliance/docs/research/OpenAMI/](../../compliance/docs/research/OpenAMI/) for detailed specifications.
