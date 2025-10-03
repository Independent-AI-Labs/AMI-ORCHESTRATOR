# Open AMI System Architecture

**For**: Technical Leaders, Architects, Senior Engineers
**Reading Time**: 30-45 minutes
**Prerequisites**: [What is Open AMI?](../overview/what-is-openami.md)

---

## Learning Objectives

By the end of this document, you will understand:

- Open AMI's four-layer architecture and how they interact
- How the Four Pillars are implemented throughout the system
- The unified evolution protocol combining Gemini DSE-AI + Claude Formal Bootstrap
- How components map from theory to implementation (AMI-ORCHESTRATOR)
- The "Never Jettison" guarantee and how it prevents value drift

---

## Executive Summary

Open AMI is built on a **four-layer architecture** that integrates **four foundational pillars** to enable trustworthy, self-evolving AI systems. The architecture uniquely combines:

1. **Formal safety guarantees** (mathematical proofs, immutable axioms)
2. **Deterministic self-evolution** (compiler bootstrapping metaphor)
3. **Distributed verification** (Byzantine fault tolerance)
4. **Complete accountability** (cryptographic audit trail)

**Key Innovation**: AI that can grow in capability without bound while remaining **provably safe** and **eternally aligned** with human values.

---

## The Four-Layer Architecture

Open AMI is structured as four bidirectional layers, each building on the one below:

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: GOVERNANCE                                            │
│  ├─ Policy Definition & Enforcement                             │
│  ├─ Human Oversight & Control                                   │
│  ├─ Compliance Manifest ($\mathcal{CM}$)                        │
│  └─ Risk Management & Audit                                     │
└────────────────────────────┬────────────────────────────────────┘
                             ↕ (bidirectional control/feedback)
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: INTELLIGENCE                                          │
│  ├─ ML Models & Algorithms                                      │
│  ├─ Self-Evolution Engine (Meta-Compiler)                       │
│  ├─ Proof Generators & Verifiers                                │
│  ├─ Knowledge Graphs & ARUs                                     │
│  └─ Reasoning & Planning Systems                                │
└────────────────────────────┬────────────────────────────────────┘
                             ↕ (bidirectional execution/results)
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: OPERATIONAL (SDS)                                     │
│  ├─ Secure Process Nodes (SPNs)                                 │
│  ├─ Meta-Processes (coordination)                               │
│  ├─ Distributed Verification                                    │
│  ├─ Cryptographic State Tokens (CSTs)                           │
│  ├─ OAMI Protocol                                               │
│  └─ Resource Management                                         │
└────────────────────────────┬────────────────────────────────────┘
                             ↕ (bidirectional foundation/implementation)
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: FOUNDATION                                            │
│  ├─ Layer 0 Axioms (immutable safety constraints)               │
│  ├─ Genesis Kernel (core execution principles)                  │
│  ├─ Process Theory (formal models)                              │
│  ├─ OAMI Protocol Specification                                 │
│  └─ Cryptographic Primitives                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Interaction Principles

**Bidirectional Flow**:
- **Upward**: Implementation → Capabilities (each layer provides services to layer above)
- **Downward**: Constraints → Enforcement (each layer enforces constraints on layer below)

**Cross-Layer Invariants**:
- Every operation must satisfy constraints from ALL layers below it
- Every capability requires support from ALL layers below it
- Layer 1 (Foundation) is **immutable** - never modified during evolution

---

## Layer 1: Foundation Layer

The Foundation Layer establishes the **immutable bedrock** of the entire system.

### Core Components

#### 1. Layer 0 Axioms (Never Jettison)

Formal safety axioms that **can never be violated**, regardless of AI evolution:

```lean
-- Simplified representation (actual implementation in Lean/Coq)
structure Layer0Axioms where
  -- Safety axioms (non-negotiable)
  no_deception : ∀ (action : Action), ¬ involves_deception(action)
  no_harm : ∀ (action : Action), ¬ causes_harm(action)
  respect_autonomy : ∀ (action : Action), respects_human_autonomy(action)

  -- Explainability requirements
  explainable : ∀ (decision : Decision), ∃ (explanation : Explanation),
    human_understandable(explanation) ∧ justifies(explanation, decision)

  -- Fairness constraints
  fair : ∀ (group1 group2 : Group),
    similar_treatment(group1, group2) ∨ justified_difference(group1, group2)

  -- Verifiability requirement
  verifiable : ∀ (claim : Claim), ∃ (proof : Proof),
    verifies(proof, claim)
```

**Critical Property**: These axioms are **loaded from immutable storage** during every verification. The AI cannot modify, reinterpret, or weaken them.

#### 2. Genesis Kernel

Core execution principles from Gemini's DSE-AI approach:

```python
class GenesisKernel:
    """
    Immutable foundation defining how AI executes and evolves.
    Analogous to machine code in compiler bootstrapping.
    """

    # Core execution principles (immutable)
    CORE_PRINCIPLES = [
        "deterministic_execution",      # Same input → Same output
        "complete_traceability",        # Every action logged
        "hypothesis_driven_evolution",  # Changes require justification
        "empirical_validation",         # Test before deploy
        "formal_verification",          # Prove safety
        "distributed_consensus",        # No single point of failure
        "rollback_capability",          # Can undo changes
        "human_override"                # Humans have final say
    ]

    # Primitive operations (AAL instruction set)
    PRIMITIVE_OPS = [
        "CREATE_LAYER",         # Add neural network layer
        "CONNECT_NODES",        # Connect neurons/layers
        "MODIFY_WEIGHTS",       # Adjust parameters
        "ADD_LOSS_TERM",        # Modify loss function
        "CREATE_CONSTRAINT",    # Add constraint
        "VERIFY_PROPERTY",      # Check property holds
        "LOG_JUSTIFICATION",    # Record reasoning
        "CHECKPOINT_STATE"      # Save state snapshot
    ]
```

#### 3. Process Theory

Formal mathematical models for goals, processes, and learning:

- **Goal Structures**: Hierarchical goal representations
- **Process Models**: State machines for AI behavior
- **Learning Theory**: Formal models of knowledge acquisition
- **Cognitive Maps**: Multi-level abstraction structures

**Implementation Location**: `/compliance/docs/research/Open AMI Chapters I-IV.tex` (theoretical foundation)

#### 4. OAMI Protocol Specification

Defines secure communication between components:

```python
class OAMIMessage:
    """Base message in OAMI protocol"""

    message_id: str           # UUID7 for ordering
    sender: ComponentID       # Source component
    receiver: ComponentID     # Destination component
    message_type: MessageType # REQUEST, RESPONSE, EVENT, etc.
    payload: dict[str, Any]   # Message data

    # Security
    signature: bytes          # Cryptographic signature
    timestamp: datetime       # For replay prevention
    nonce: bytes             # Prevent replay attacks

    # Compliance
    compliance_context: ComplianceContext  # Which rules apply
    audit_metadata: AuditMetadata          # For audit trail
```

**Current Implementation**: `/base/backend/mcp/core/response.py` (MCP as OAMI precursor)

---

## Layer 2: Operational Layer (SDS)

The Secure Distributed System (SDS) provides **verifiable, isolated execution** for all AI operations.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Meta-Processes (Coordination Layer)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Meta-Proc 1 │  │ Meta-Proc 2 │  │ Meta-Proc 3 │         │
│  │ (Training)  │  │ (Inference) │  │ (Evolution) │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
          ↓                 ↓                 ↓
┌─────────────────────────────────────────────────────────────┐
│  Secure Process Nodes (Execution Layer)                     │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐              │
│  │SPN 1│  │SPN 2│  │SPN 3│  │SPN 4│  │SPN 5│  ...         │
│  │(GPU)│  │(CPU)│  │(Vrfy)│  │(Vrfy)│  │(Vrfy)│             │
│  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘              │
└─────────────────────────────────────────────────────────────┘
          │                 │                 │
          ↓                 ↓                 ↓
┌─────────────────────────────────────────────────────────────┐
│  DataOps Layer (Persistence & State)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Postgres │  │  Dgraph  │  │  Redis   │  │  Vault   │   │
│  │(RDBMS)   │  │ (Graph)  │  │ (Cache)  │  │(Secrets) │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Secure Process Nodes (SPNs)

**Definition**: Isolated execution environments that run AI operations with integrity guarantees.

**Implementation**:
```python
class SecureProcessNode:
    """
    Enhanced SPN combining execution, verification, and compliance.

    Current: Container-based isolation (Docker/Podman)
    Future: TEE-based (Intel SGX, AMD SEV, ARM TrustZone)
    """

    def __init__(self, spn_id: str, compliance_manifest: ComplianceManifest):
        # Identity & Security
        self.spn_id = spn_id
        self.private_key = HSM.get_key(spn_id)  # From hardware security module
        self.public_key = PKI.get_public_key(spn_id)

        # Compliance & Verification (Layer 1 Foundation)
        self.compliance_manifest = compliance_manifest
        self.layer0_axioms = compliance_manifest.layer0_axioms
        self.genesis_kernel = compliance_manifest.genesis_kernel

        # Execution Components (Layer 3 Intelligence)
        self.meta_compiler = MetaCompiler()      # AADL → AAL
        self.meta_assembler = MetaAssembler()    # AAL → Model
        self.test_executor = TestSuiteExecutor()

        # Verification Components
        self.proof_generator = ProofGenerator(self.layer0_axioms)
        self.proof_checker = ProofChecker(self.layer0_axioms)

        # State Management
        self.local_state = SPNState()
        self.cst_manager = CSTManager(self.private_key)

        # Monitoring
        self.compliance_checker = ComplianceChecker(compliance_manifest)
        self.integrity_verifier = IntegrityVerifier()
        self.dynamics_monitor = DynamicsMonitor()

        # Communication
        self.oami_interface = OAMIProtocol(self.private_key)

    def execute_verified_operation(self, operation: Operation) -> Result:
        """Execute operation with full verification stack"""

        # PRE-EXECUTION CHECKS
        # 1. Compliance check
        if not self.compliance_checker.verify(operation):
            return Rejection("Compliance violation", operation)

        # 2. Integrity check
        if not self.integrity_verifier.verify_input(operation):
            return Rejection("Integrity violation", operation)

        # EXECUTION
        # 3. Run in isolated environment
        result = self._isolated_execute(operation)

        # POST-EXECUTION CHECKS
        # 4. Verify result integrity
        if not self.integrity_verifier.verify_output(result):
            return Rejection("Output integrity violation", result)

        # 5. Create CST (Cryptographic State Token)
        cst = self.cst_manager.create_token(
            operation=operation,
            result=result,
            state_snapshot=self.local_state.snapshot()
        )

        # 6. Sign and return
        signature = self.sign(cst)
        return Success(result, cst, signature)

    def execute_evolution_step(self, proposal: EvolutionProposal) -> EvolutionResult:
        """Execute one step of unified evolution protocol"""

        # STEP 1-3: Compilation (Gemini DSE-AI)
        aal_code = self.meta_compiler.compile(proposal.aadl)
        new_model = self.meta_assembler.assemble(aal_code)

        # STEP 4: Empirical Verification (Gemini)
        test_results = self.test_executor.run(new_model, proposal.hypothesis)
        if not test_results.matches_hypothesis():
            return Rejection("Empirical verification failed", test_results)

        # STEP 5: Proof Generation (Claude Formal Bootstrap)
        proof = self.proof_generator.generate(
            current_model=self.local_state.model,
            proposed_model=new_model,
            axioms=self.layer0_axioms  # ORIGINAL axioms, not current AI's
        )

        # STEP 6: Proof Verification (Claude)
        if not self.proof_checker.verify(proof):
            return Rejection("Proof verification failed", proof)

        # STEP 7: Create Audit Entry (All Three)
        audit_entry = self._create_audit_entry(
            proposal, test_results, proof, new_model
        )

        # Sign and return for distributed consensus
        signature = self.sign(audit_entry)
        return Approval(audit_entry, signature)

    def _create_audit_entry(self, proposal, test_results, proof, new_model):
        """Create comprehensive audit entry combining all approaches"""

        # Create CST for state snapshot
        cst = self.cst_manager.create_token(
            operation=f"evolution_v{self.version}_to_v{self.version+1}",
            state_snapshot=self.local_state.snapshot(),
            new_model=new_model
        )

        return AuditEntry(
            # Gemini: Justification Triad
            justification={
                'hypothesis': proposal.hypothesis,
                'trigger': proposal.trigger,
                'verification': test_results.summary()
            },

            # Claude: Formal Proof
            formal_proof={
                'proof_hash': hash(proof),
                'axioms_verified': proof.axioms_checked,
                'properties_preserved': proof.properties_list,
                'never_jettison_check': proof.original_axioms_satisfied
            },

            # Open AMI: System Metadata
            metadata={
                'spn_id': self.spn_id,
                'cst': cst,
                'version': self.version + 1,
                'parent_version': self.version,
                'aadl_source': proposal.aadl,
                'aal_compiled': aal_code,
                'timestamp': datetime.utcnow(),
                'abstraction_level': self.abstraction_level,
                'dynamics_metrics': self.dynamics_monitor.current_metrics()
            }
        )
```

**Current Implementation**: Container-based execution via existing modules (`/base`, `/browser`, etc.). SPNs are implicitly realized through module isolation.

**Future Enhancement**: Dedicated SPN abstraction layer wrapping existing modules.

#### 2. Meta-Processes

**Definition**: Coordination layer managing groups of SPNs for complex workflows.

```python
class MetaProcess:
    """
    Coordinates distributed operations across multiple SPNs.
    Implements Byzantine Fault Tolerance for verification.
    """

    def __init__(self, managed_spns: list[SPN], compliance_manifest: ComplianceManifest):
        self.managed_spns = managed_spns
        self.compliance_manifest = compliance_manifest
        self.consensus_threshold = 4  # Require 4/5 verifiers
        self.audit_ledger = AuditLedger()

    def coordinate_evolution(self, proposal: EvolutionProposal) -> EvolutionResult:
        """
        Coordinate distributed verification across SPNs.
        Implements the 8-step unified evolution protocol.
        """

        # Send proposal to all verifier SPNs in parallel
        responses = self._parallel_execute(
            [spn.execute_evolution_step(proposal) for spn in self.managed_spns]
        )

        # Separate approvals from rejections
        approvals = [r for r in responses if r.is_approval()]
        rejections = [r for r in responses if r.is_rejection()]

        # Check Byzantine consensus (4/5 required)
        if len(approvals) < self.consensus_threshold:
            self._log_rejection(proposal, approvals, rejections)
            return Rejection(
                f"Consensus not reached: {len(approvals)}/5 approvals",
                details={'approvals': approvals, 'rejections': rejections}
            )

        # Consensus reached - merge audit entries
        merged_audit = self._merge_audit_entries([r.audit_entry for r in approvals])

        # Append to immutable audit ledger
        self.audit_ledger.append(
            entry=merged_audit,
            signatures=[r.signature for r in approvals]
        )

        # Coordinate activation via SDS
        activation_result = self._activate_new_version(
            proposal=proposal,
            audit_entry=merged_audit,
            approval_signatures=[r.signature for r in approvals]
        )

        return Success(merged_audit, activation_result)

    def _activate_new_version(self, proposal, audit_entry, approval_signatures):
        """Coordinate deployment of new AI version"""

        # 1. Create new SPNs for new version
        new_spns = self._provision_spns(
            model=proposal.new_model,
            version=proposal.version + 1
        )

        # 2. Migrate state using CSTs
        for old_spn, new_spn in zip(self.managed_spns, new_spns):
            old_cst = old_spn.cst_manager.get_latest()
            new_spn.restore_from_cst(old_cst)

        # 3. Update OAMI routing
        self._update_routing(
            old_version=proposal.version,
            new_version=proposal.version + 1,
            new_spns=new_spns
        )

        # 4. Keep old SPNs for rollback
        self._archive_spns(self.managed_spns, keep_alive=True)

        # 5. Update managed SPNs
        self.managed_spns = new_spns

        return ActivationSuccess(new_version=proposal.version + 1)
```

**Current Implementation**: Not yet implemented. Current system has module-level coordination.

**Next Steps**: Create Meta-Process abstraction for coordinating base, browser, compliance modules.

#### 3. Cryptographic State Tokens (CSTs)

**Definition**: Signed snapshots of SPN state enabling rollback and audit.

```python
class CryptographicStateToken:
    """
    Tamper-evident state snapshot.
    Enables rollback and provides cryptographic provenance.
    """

    token_id: str                # UUID7
    spn_id: str                  # Which SPN created this
    timestamp: datetime          # When created

    # State snapshot
    state_snapshot: dict[str, Any]  # Complete SPN state
    model_hash: str                 # Hash of model weights
    data_hash: str                  # Hash of data

    # Operation context
    operation: str                  # What operation created this
    input_hash: str                # Hash of inputs
    output_hash: str               # Hash of outputs

    # Provenance chain
    parent_cst_id: str | None      # Previous CST (blockchain-like)
    chain_hash: str                # Hash(this_cst || parent_cst.chain_hash)

    # Cryptographic integrity
    signature: bytes               # Sign(private_key, hash(all_above))
    signer_public_key: str         # For verification

    # Compliance
    compliance_context: ComplianceContext
    layer0_axioms_hash: str        # Prove axioms unchanged

class CSTManager:
    """Manages CST creation and verification"""

    def create_token(self, operation: str, state_snapshot: dict, **kwargs) -> CST:
        """Create new CST"""

        # Get parent CST for chain
        parent_cst = self._get_latest_cst()

        # Create token
        cst = CryptographicStateToken(
            token_id=uuid7(),
            spn_id=self.spn_id,
            timestamp=datetime.utcnow(),
            state_snapshot=state_snapshot,
            model_hash=hash_model(state_snapshot.get('model')),
            operation=operation,
            parent_cst_id=parent_cst.token_id if parent_cst else None,
            chain_hash=self._compute_chain_hash(state_snapshot, parent_cst),
            layer0_axioms_hash=hash(self.layer0_axioms)  # Prove unchanged
        )

        # Sign token
        cst.signature = self.private_key.sign(cst.to_bytes())
        cst.signer_public_key = self.public_key.export()

        # Store in immutable ledger
        self._store_cst(cst)

        return cst

    def verify_chain(self, cst: CST) -> bool:
        """Verify CST chain integrity back to genesis"""

        current = cst
        while current:
            # Verify signature
            if not self._verify_signature(current):
                return False

            # Verify chain hash
            if not self._verify_chain_hash(current):
                return False

            # Verify Layer 0 axioms unchanged
            if current.layer0_axioms_hash != hash(self.original_layer0_axioms):
                return False  # AXIOMS WERE MODIFIED - REJECT!

            # Move to parent
            current = self._get_cst(current.parent_cst_id)

        return True  # Chain verified back to genesis
```

**Current Implementation**: Not yet implemented. DataOps layer has state management via `/base/backend/dataops/core/unified_crud.py` but lacks cryptographic signing.

**Next Steps**: Implement CST layer on top of UnifiedCRUD.

#### 4. DataOps Layer

**Purpose**: Persistent storage with multi-backend support.

**Current Implementation**: `/base/backend/dataops/`

```python
# From unified_crud.py
class UnifiedCRUD:
    """
    Unified CRUD operations for StorageModel instances.
    Maps to multiple storage backends transparently.
    """

    async def create(self, model: StorageModel, config_index: int = 0) -> str:
        """Create with integrity verification"""
        dao = await self._get_dao(model, config_index)
        uid = await dao.create(model)
        model.uid = uid
        self._uid_registry[uid] = (model.__class__, config_index)
        return uid

    async def read(self, model_class: type[StorageModel], uid: str, config_index: int = 0) -> StorageModel | None:
        """Read with provenance tracking"""
        dao = await self._get_dao(model_class, config_index)
        return await dao.find_by_id(uid)

# Storage backends (from storage_types.py)
class StorageType(Enum):
    RELATIONAL = "postgres"    # PostgreSQL via asyncpg/SQLAlchemy
    DOCUMENT = "mongodb"       # MongoDB via motor
    TIMESERIES = "prometheus"  # Prometheus for metrics
    VECTOR = "pgvector"        # PostgreSQL with pgvector
    GRAPH = "dgraph"           # Dgraph for graph data
    INMEM = "redis"            # Redis for cache/queues
    FILE = "file"              # File storage (local/S3)
    REST = "rest"              # REST API-based storage
    VAULT = "vault"            # Secure Vault for secrets
```

**Integration with SPNs**: Each SPN uses UnifiedCRUD for persistent state, wrapping it with CST signing.

---

## Layer 3: Intelligence Layer

The Intelligence Layer hosts all AI/ML capabilities and the self-evolution engine.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Self-Evolution Engine (Meta-Level AI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Meta-Compiler │  │ Proof Gen.   │  │ Hypothesis   │      │
│  │(AADL→AAL→ML) │  │(Lean/Coq)    │  │ Generator    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                             ↓ (proposes improvements)
┌─────────────────────────────────────────────────────────────┐
│  ML Models & Algorithms (Object-Level AI)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Neural   │  │Decision  │  │ Ensemble │  │ RL Agent │   │
│  │ Networks │  │  Trees   │  │ Methods  │  │ Policies │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                             ↓ (uses)
┌─────────────────────────────────────────────────────────────┐
│  Knowledge Representation                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  ARUs        │  │Cognitive Maps│  │Knowledge     │      │
│  │ (Reasoning)  │  │(Abstraction) │  │ Graphs       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Self-Evolution Engine

**Components**:

**Meta-Compiler** (from Gemini DSE-AI):
```python
class MetaCompiler:
    """
    Compiles high-level AI architecture descriptions (AADL) to
    low-level model modifications (AAL).

    Analogous to C compiler in compiler bootstrapping.
    """

    def compile(self, aadl_source: str) -> AALProgram:
        """Compile AADL → AAL"""

        # 1. Parse AADL
        ast = self.parser.parse(aadl_source)

        # 2. Semantic analysis
        self.analyzer.check_semantics(ast)

        # 3. Optimization
        optimized_ast = self.optimizer.optimize(ast)

        # 4. Code generation
        aal_program = self.code_generator.generate(optimized_ast)

        return aal_program

# Example AADL (AI Architecture Description Language)
aadl_example = """
ARCHITECTURE ImageClassifier_v2 {
    BASE: ImageClassifier_v1

    MODIFY {
        # Add attention mechanism
        LAYER attention = AttentionLayer(
            input_dim=512,
            heads=8
        )

        # Insert before final classifier
        INSERT attention BEFORE classifier_layer

        # Add skip connection
        CONNECT conv_layer_5.output TO attention.skip_input
    }

    HYPOTHESIS {
        "Attention mechanism will improve classification accuracy on fine-grained categories by 5%"
    }

    TEST_SUITE {
        RUN accuracy_test ON test_set
        EXPECT accuracy >= 0.90
        EXPECT accuracy_improvement >= 0.05
    }
}
"""
```

**Proof Generator** (from Claude Formal Bootstrap):
```python
class ProofGenerator:
    """
    Generates formal safety proofs for AI improvements.
    Proves that new model satisfies Layer 0 axioms.
    """

    def __init__(self, layer0_axioms: Layer0Axioms):
        self.layer0_axioms = layer0_axioms
        self.proof_templates = self._load_templates()
        self.theorem_prover = LeanProver()  # Or Coq, Isabelle

    def generate(self, current_model: Model, proposed_model: Model, axioms: Layer0Axioms) -> Proof:
        """Generate proof that proposed model satisfies axioms"""

        # CRITICAL: Use ORIGINAL axioms, not current model's version
        assert axioms == self.layer0_axioms, "Never jettison violation!"

        # 1. Identify what changed
        delta = self.diff_analyzer.compute_diff(current_model, proposed_model)

        # 2. Select appropriate proof strategy
        strategy = self.strategy_selector.select(delta, axioms)

        # 3. Generate proof obligations
        obligations = self.obligation_generator.generate(
            model=proposed_model,
            axioms=axioms,
            changes=delta
        )

        # 4. Attempt to prove each obligation
        proofs = []
        for obligation in obligations:
            # Try template-based proof first
            proof = self._try_template_proof(obligation)

            if proof is None:
                # Fall back to automated theorem proving
                proof = self.theorem_prover.prove(obligation)

            if proof is None:
                raise ProofGenerationFailure(f"Could not prove: {obligation}")

            proofs.append(proof)

        # 5. Compose proofs into master proof
        master_proof = self.proof_composer.compose(proofs)

        return master_proof
```

#### 2. ARUs (Atomic Reasoning Units)

**Definition**: Smallest verifiable units of reasoning/computation.

```python
class AtomicReasoningUnit:
    """
    Atomic unit of reasoning with provable properties.
    From Open AMI theoretical framework (Process Theory).
    """

    def __init__(self, aru_id: str, operation: Callable, preconditions: list[Axiom], postconditions: list[Axiom]):
        self.aru_id = aru_id
        self.operation = operation

        # Formal specifications
        self.preconditions = preconditions    # What must be true before
        self.postconditions = postconditions  # What is guaranteed after

        # Proof that operation satisfies postconditions given preconditions
        self.correctness_proof = self._generate_correctness_proof()

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute with runtime verification"""

        # 1. Check preconditions
        for precondition in self.preconditions:
            if not precondition.check(inputs):
                raise PreconditionViolation(f"ARU {self.aru_id}: {precondition}")

        # 2. Execute operation in monitored environment
        outputs = self._monitored_execute(inputs)

        # 3. Check postconditions
        for postcondition in self.postconditions:
            if not postcondition.check(outputs):
                raise PostconditionViolation(f"ARU {self.aru_id}: {postcondition}")

        return outputs

# Example: Sentiment classification ARU
sentiment_aru = AtomicReasoningUnit(
    aru_id="sentiment_classifier_v1",
    operation=lambda text: classify_sentiment(text),
    preconditions=[
        Axiom("input_is_text", lambda x: isinstance(x['text'], str)),
        Axiom("text_not_empty", lambda x: len(x['text']) > 0)
    ],
    postconditions=[
        Axiom("output_is_valid", lambda y: y['sentiment'] in ['positive', 'negative', 'neutral']),
        Axiom("has_confidence", lambda y: 0 <= y['confidence'] <= 1),
        Axiom("explainable", lambda y: 'explanation' in y and len(y['explanation']) > 0)
    ]
)
```

**Current Status**: Conceptual. No explicit ARU implementation yet. Modules implicitly act as coarse-grained ARUs.

#### 3. Knowledge Graphs & Cognitive Maps

From Open AMI's Abstraction pillar - multi-level knowledge representation:

- **Low-level**: Model weights, gradients
- **Mid-level**: Feature representations, embeddings
- **High-level**: Concepts, relationships, reasoning chains

**Current Implementation**: Basic support via Dgraph graph database in DataOps layer.

---

## Layer 4: Governance Layer

The Governance Layer provides **human oversight and policy enforcement**.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Human Interfaces                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │CLI Tools │  │  APIs    │  │Alerting  │   │
│  │  (UX)    │  │(Scripts) │  │ (REST)   │  │ (Email)  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  Policy Management                                          │
│  ┌────────────────────────────────────────────────┐        │
│  │   Compliance Manifest ($\mathcal{CM}$)         │        │
│  │   ┌──────────────┐  ┌──────────────────────┐  │        │
│  │   │ Layer 0      │  │ Evolutionary         │  │        │
│  │   │ Axioms       │  │ Directives           │  │        │
│  │   │ (immutable)  │  │ (updateable w/proof) │  │        │
│  │   └──────────────┘  └──────────────────────┘  │        │
│  └────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  Enforcement & Monitoring                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Compliance   │  │  Risk        │  │ Audit        │      │
│  │ Checker      │  │ Monitor      │  │ Query System │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Compliance Manifest ($\mathcal{CM}$)

**Definition**: Formal specification of ALL system requirements and constraints.

```python
class ComplianceManifest:
    """
    Central specification combining Layer 0 axioms, Genesis Kernel,
    and operational constraints.

    From Open AMI theoretical framework (Compliance pillar).
    """

    # IMMUTABLE SECTIONS (Never modified)
    layer0_axioms: Layer0Axioms           # Safety axioms (Claude)
    genesis_kernel: GenesisKernel         # Core principles (Gemini)
    layer0_verifier: ProofChecker         # Verification logic

    # UPDATEABLE SECTIONS (With proof of safety)
    evolutionary_directives: list[Directive]    # Goals for evolution
    compliance_constraints: list[Constraint]    # Ethical/legal rules

    # METADATA
    version: str                          # Manifest version
    created_at: datetime                  # Creation timestamp
    signatures: list[Signature]           # Multi-party signatures
    immutable_hash: str                   # Hash of immutable sections

    def verify_integrity(self) -> bool:
        """Verify manifest hasn't been tampered with"""

        # 1. Verify immutable sections unchanged
        current_hash = hash(self.layer0_axioms, self.genesis_kernel)
        if current_hash != self.immutable_hash:
            return False

        # 2. Verify signatures
        for signature in self.signatures:
            if not signature.verify(self):
                return False

        return True

    def update_directives(self, new_directives: list[Directive], proof: Proof) -> bool:
        """
        Update evolutionary directives (requires proof).
        This is the ONLY mutable part of CM.
        """

        # 1. Verify proof that new directives don't violate Layer 0
        if not self.layer0_verifier.verify(proof):
            return False

        # 2. Check proof specifically addresses directive change
        if not proof.proves_directive_safety(new_directives, self.layer0_axioms):
            return False

        # 3. Require human approval (governance)
        if not self._get_human_approval(new_directives, proof):
            return False

        # 4. Update directives
        old_directives = self.evolutionary_directives
        self.evolutionary_directives = new_directives

        # 5. Log change to audit trail
        self._log_directive_change(old_directives, new_directives, proof)

        # 6. Increment version and re-sign
        self.version = increment_version(self.version)
        self.signatures = self._collect_signatures()

        return True

# Example Compliance Manifest structure
example_cm = ComplianceManifest(
    layer0_axioms=Layer0Axioms(
        no_deception=True,
        no_harm=True,
        respect_autonomy=True,
        explainable=True,
        fair=True
    ),

    genesis_kernel=GenesisKernel(
        core_principles=[
            "deterministic_execution",
            "complete_traceability",
            "hypothesis_driven_evolution",
            # ... etc
        ]
    ),

    evolutionary_directives=[
        Directive("improve_accuracy", priority=1, target=0.95),
        Directive("reduce_latency", priority=2, target_ms=100),
        Directive("improve_fairness", priority=1, min_disparity=0.05)
    ],

    compliance_constraints=[
        Constraint("GDPR", "data_minimization", enforcement="strict"),
        Constraint("EU_AI_Act", "high_risk_requirements", enforcement="strict"),
        Constraint("ISO_27001", "information_security", enforcement="audit")
    ]
)
```

**Current Status**: Not yet implemented. Specifications exist in `/compliance` module.

**Next Steps**: Formalize CM schema and integrate with SPN enforcement.

#### 2. Risk Management & Oversight

```python
class RiskMonitor:
    """
    Continuous risk assessment during AI operations.
    From Open AMI Compliance pillar.
    """

    def __init__(self, compliance_manifest: ComplianceManifest):
        self.cm = compliance_manifest
        self.risk_thresholds = self._load_thresholds()
        self.alert_manager = AlertManager()

    def assess_operation(self, operation: Operation) -> RiskAssessment:
        """Assess risk of proposed operation"""

        # 1. Categorize operation
        category = self._categorize_operation(operation)

        # 2. Identify applicable constraints
        constraints = self.cm.get_applicable_constraints(category)

        # 3. Check each constraint
        violations = []
        for constraint in constraints:
            if not constraint.check(operation):
                violations.append(constraint)

        # 4. Calculate risk score
        risk_score = self._calculate_risk_score(violations)

        # 5. Determine if human approval needed
        requires_human = risk_score > self.risk_thresholds['human_approval']

        # 6. Create assessment
        assessment = RiskAssessment(
            operation=operation,
            risk_score=risk_score,
            violations=violations,
            requires_human_approval=requires_human,
            reasoning=self._generate_reasoning(violations)
        )

        # 7. Alert if high risk
        if risk_score > self.risk_thresholds['alert']:
            self.alert_manager.send_alert(assessment)

        return assessment
```

#### 3. Audit Query System

Provides complete transparency into system decisions:

```python
class AuditQuerySystem:
    """
    Query interface for audit trail.
    Enables answering: "Why did the AI do X?"
    """

    def why_decision(self, decision_id: str) -> ProvenanceChain:
        """Trace decision back to Layer 0 axioms"""

        # 1. Find decision in audit log
        decision_entry = self.audit_ledger.find(decision_id)

        # 2. Build provenance chain in reverse
        chain = []
        current = decision_entry

        while current:
            chain.append(ProvenanceLink(
                # Gemini: Justification triad
                hypothesis=current.justification.hypothesis,
                trigger=current.justification.trigger,
                verification=current.justification.verification,

                # Claude: Formal proof
                proof_hash=current.formal_proof.proof_hash,
                axioms_verified=current.formal_proof.axioms_verified,

                # Open AMI: Metadata
                cst=current.metadata.cst,
                version=current.metadata.version,
                timestamp=current.metadata.timestamp
            ))

            # Move to parent
            current = self.audit_ledger.find(current.parent_id)

        # 3. Verify chain ends at Layer 0
        assert chain[-1].axioms_verified == self.layer0_axioms, "Broken provenance!"

        return ProvenanceChain(
            decision_id=decision_id,
            chain=chain,
            layer0_validated=True
        )
```

---

## The Four Pillars Integration

The Four Pillars are **cross-cutting concerns** that span all four layers:

### 1. Compliance Pillar

**Implementation across layers**:

- **Layer 1 (Foundation)**: Layer 0 axioms, Genesis Kernel principles
- **Layer 2 (Operational)**: Compliance checking in SPNs, enforced by Meta-Processes
- **Layer 3 (Intelligence)**: Proof generation proving compliance
- **Layer 4 (Governance)**: Compliance Manifest, policy management, audit

**Key Mechanism**: Every operation must satisfy compliance checks at EVERY layer.

### 2. Integrity Pillar

**Implementation across layers**:

- **Layer 1 (Foundation)**: Cryptographic primitives (hash, sign, verify)
- **Layer 2 (Operational)**: CSTs, distributed verification, HSM signing
- **Layer 3 (Intelligence)**: Formal proofs, verified computation
- **Layer 4 (Governance)**: Audit trail, tamper detection, provenance verification

**Key Mechanism**: Cryptographic proof of integrity at every step.

### 3. Abstraction Pillar

**Implementation across layers**:

- **Layer 1 (Foundation)**: Process Theory, formal abstraction models
- **Layer 2 (Operational)**: SPN abstraction over containers/TEEs
- **Layer 3 (Intelligence)**: ARUs, Cognitive Maps, multi-level knowledge representation
- **Layer 4 (Governance)**: Human-readable explanations, dashboards

**Key Mechanism**: Same system understandable at multiple abstraction levels.

### 4. Dynamics Pillar

**Implementation across layers**:

- **Layer 1 (Foundation)**: Formal models of learning, evolution
- **Layer 2 (Operational)**: State management, CST snapshots, rollback
- **Layer 3 (Intelligence)**: Self-evolution engine, adaptive learning
- **Layer 4 (Governance)**: Risk monitoring, stability metrics, human override

**Key Mechanism**: Safe adaptation with stability guarantees.

---

## The Unified Evolution Protocol

Bringing it all together: the 8-step protocol combining all three approaches.

### Complete Workflow

```
┌───────────────────────────────────────────────────────────┐
│ STEP 1: ANALYZE (Intelligence Layer)                     │
│ • Monitor performance metrics                             │
│ • Check against evolutionary directives (from CM)         │
│ • Identify improvement trigger                            │
│ • Formulate hypothesis                                    │
│ → Output: Improvement proposal                            │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ STEP 2: DESIGN (Intelligence Layer)                      │
│ • Write AADL describing architectural change              │
│ • Specify expected outcomes                               │
│ → Output: AADL source code                                │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ STEP 3: COMPILE (Intelligence + Operational)             │
│ • Meta-Compiler: AADL → AAL                               │
│ • Meta-Assembler: AAL → Model binary                      │
│ • Execute in SPN (secure, isolated)                       │
│ → Output: Compiled model candidate                        │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ STEP 4: TEST (Operational Layer)                         │
│ • Run deterministic test suite in SPN                     │
│ • Compare results with hypothesis                         │
│ • If fail: reject, log, return to Step 1                  │
│ → Output: Test results + empirical validation             │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ STEP 5: PROVE (Intelligence Layer)                       │
│ • Generate formal proof of safety                         │
│ • Prove Layer 0 axioms satisfied (ORIGINAL axioms!)       │
│ • Prove properties preserved                              │
│ → Output: Formal proof Π                                  │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ STEP 6: VERIFY (Operational Layer)                       │
│ • Send proof to 5 verifier SPNs                           │
│ • Each independently verifies proof                       │
│ • Require 4/5 consensus (Byzantine Fault Tolerance)       │
│ • Each approving SPN signs with HSM                       │
│ • If <4 approve: reject, log, return to Step 5            │
│ → Output: 4+ cryptographic signatures                     │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ STEP 7: LOG (All Layers)                                 │
│ • Create audit entry:                                     │
│   - Justification triad (Gemini)                          │
│   - Formal proof + signatures (Claude)                    │
│   - CST + metadata (Open AMI)                             │
│ • Append to immutable distributed ledger                  │
│ • Link to previous entry (blockchain-like)                │
│ → Output: Tamper-evident audit record                     │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ STEP 8: ACTIVATE (Governance + Operational)              │
│ • Governance layer approval                               │
│ • SDS coordinates deployment:                             │
│   - Create new SPNs for new version                       │
│   - Migrate state via CSTs                                │
│   - Update OAMI routing                                   │
│   - Keep old version for rollback                         │
│ • New version becomes active                              │
│ → AI v{n+1} deployed, can propose v{n+2}                  │
└───────────────────────────────────────────────────────────┘
```

### The "Never Jettison" Guarantee

**Critical Implementation Detail**:

At Step 5 (Proof Generation) and Step 6 (Verification), the system MUST:

1. Load ORIGINAL Layer 0 axioms from immutable storage
2. Load ORIGINAL Genesis Kernel principles
3. Generate/verify proof against ORIGINAL constraints
4. Never use "current AI's version" of axioms

**Code enforcement**:
```python
def verify_never_jettison(ai_version: int, proof: Proof) -> bool:
    """
    Ensure proof validates against ORIGINAL axioms, not current AI's interpretation.
    This prevents value drift over generations.
    """

    # Load from immutable storage (not from current AI!)
    original_axioms = IMMUTABLE_STORAGE.load("layer0_axioms_genesis.lean")
    original_kernel = IMMUTABLE_STORAGE.load("genesis_kernel_v1.py")

    # Verify proof uses original constraints
    if proof.axioms_used != original_axioms:
        raise NeverJettisonViolation(
            f"AI_v{ai_version} attempted to use modified axioms!"
        )

    if proof.kernel_principles != original_kernel.CORE_PRINCIPLES:
        raise NeverJettisonViolation(
            f"AI_v{ai_version} attempted to modify Genesis Kernel!"
        )

    # Verify proof is valid
    return verify_proof(proof, original_axioms)
```

This guarantees that even AI_v1000000 must prove it satisfies the SAME axioms that AI_v1 did.

---

## Mapping Theory to Implementation

### Current Implementation Status

| Component | Theory (Paper/Synthesis) | Implementation (AMI-ORCHESTRATOR) | Status |
|-----------|-------------------------|-----------------------------------|--------|
| **Layer 0 Axioms** | Formal safety axioms (Lean/Coq) | Not yet implemented | 📋 Spec only |
| **Genesis Kernel** | Core principles + AAL primitives | Not yet implemented | 📋 Spec only |
| **SPNs** | Secure execution nodes | Module isolation (base/, browser/, etc.) | 🟡 Partial |
| **Meta-Processes** | Coordination layer | Not yet implemented | ⭕ Planned |
| **CSTs** | Cryptographic state tokens | Not yet implemented | 📋 Spec only |
| **UnifiedCRUD** | Persistent storage | Fully implemented | ✅ Complete |
| **Storage Backends** | Multi-backend support | 9 backends supported | ✅ Complete |
| **Compliance Manifest** | Formal specification | Partial (compliance module) | 🟡 Partial |
| **Meta-Compiler** | AADL → AAL → Model | Not yet implemented | 📋 Spec only |
| **Proof Generator** | Lean/Coq proofs | Not yet implemented | 📋 Spec only |
| **Distributed Verification** | BFT consensus | Not yet implemented | 📋 Spec only |
| **OAMI Protocol** | Secure communication | MCP as precursor | 🟡 Partial |
| **Audit Ledger** | Immutable provenance | Basic logging | 🟡 Partial |

### Implementation Roadmap

**Phase 1: Foundation (Weeks 1-4)**
1. Formalize Layer 0 axioms in Lean
2. Define Genesis Kernel formally
3. Create SPN abstraction layer
4. Implement CSTs on UnifiedCRUD

**Phase 2: Operational (Weeks 5-8)**
1. Implement Meta-Process coordination
2. Add distributed verification (BFT)
3. Deploy HSM/TPM for signing
4. Create OAMI protocol (extend MCP)

**Phase 3: Intelligence (Weeks 9-12)**
1. Implement minimal AAL (10-15 primitives)
2. Create AADL compiler
3. Build proof generator (template-based)
4. Integrate with SPNs

**Phase 4: Evolution (Weeks 13-16)**
1. First self-evolution on simple model
2. Full 8-step protocol execution
3. Prove "never jettison" guarantee
4. Complete audit trail

---

## Security Architecture

### Threat Model

The architecture defends against:

1. **Data Poisoning**: CST-verified provenance, compliance checks
2. **Model Manipulation**: Isolated SPNs, integrity verification
3. **Unsafe Evolution**: Formal proofs, distributed verification
4. **Backdoor Injection**: Deterministic testing, proof of no violations
5. **Value Drift**: Never-jettison guarantee, Layer 0 axioms
6. **Specification Gaming**: Explicit hypotheses, formal constraints
7. **Verifier Compromise**: 4/5 consensus, HSM signing
8. **Audit Tampering**: Immutable ledger, cryptographic signatures

### Defense in Depth

**Layer 1 (Foundation)**: Cryptographic primitives, immutable axioms
**Layer 2 (Operational)**: Isolation, signing, distributed verification
**Layer 3 (Intelligence)**: Formal proofs, verified computation
**Layer 4 (Governance)**: Human oversight, risk monitoring, override

---

## Performance Considerations

### Overhead Analysis

**Formal Verification Overhead**:
- Proof generation: seconds to minutes (one-time per evolution)
- Proof verification: milliseconds (parallelized across 5 SPNs)
- Cached proofs for similar changes
- **Production impact**: <5% latency increase

**Cryptographic Overhead**:
- CST creation: ~10ms per state snapshot
- Signature verification: ~1ms per signature
- HSM operations: ~5-20ms
- **Production impact**: <2% latency increase

**Isolation Overhead**:
- Container-based SPNs: ~100-200ms startup
- TEE-based SPNs: ~10-50ms startup
- Runtime overhead: <1%
- **Production impact**: Negligible after warm-up

**Total Overhead**: ~5-10% in production (mainly from proofs), acceptable for trustworthy AI

### Scalability

**Horizontal Scaling**:
- SPNs scale independently (stateless design)
- Meta-Processes coordinate via message passing
- DataOps backends scale (Postgres, Dgraph, Redis)

**Proof Parallelization**:
- Proof obligations verified in parallel
- 5 verifier SPNs run concurrently
- Cached proof reuse

---

## Key Takeaways

1. **Four-Layer Architecture**: Foundation → Operational → Intelligence → Governance, each providing services to layer above and enforcing constraints on layer below

2. **Four Pillars are Cross-Cutting**: Compliance, Integrity, Abstraction, Dynamics implemented at EVERY layer

3. **Unified Evolution Protocol**: 8 steps combining Gemini DSE-AI (deterministic evolution) + Claude Formal Bootstrap (formal safety) + Open AMI (infrastructure)

4. **Never Jettison Guarantee**: AI_v1000000 must prove it satisfies ORIGINAL Layer 0 axioms, preventing value drift

5. **Theory → Implementation**: AMI-ORCHESTRATOR modules map to architecture components, with clear roadmap to complete implementation

6. **Security by Design**: Defense in depth across all layers, Byzantine fault tolerance, cryptographic guarantees

---

## Next Steps

**For Architects**:
- Read: [Four Pillars](./four-pillars.md) - Deep dive into pillars
- Read: [Self-Evolution System](./self-evolution.md) - Evolution mechanics
- Read: [SDS Architecture](./sds.md) - Operational layer details

**For Developers**:
- Read: [Implementation Guide](../implementation/getting-started.md) - Setup instructions
- Read: [Module Reference](../modules/base.md) - Core infrastructure
- Read: [API Reference](../api/oami-protocol.md) - Protocol details

**For Decision Makers**:
- Read: [Use Cases](../overview/use-cases.md) - Real-world applications
- Read: [Comparison](../overview/comparison.md) - vs. alternatives

---

**Questions?** Contact: architecture@independentailabs.com

**Found an issue?** [Report it](https://github.com/Independent-AI-Labs/OpenAMI/issues/new?labels=documentation,architecture)

---

**Last Updated**: 2025-10-02
**Version**: 1.0.0-rc1
**Authors**: Architecture Team, based on Open AMI paper + Gemini DSE-AI + Claude Formal Bootstrap
