# Open AMI Quick Start

**For**: Developers, Engineers
**Time**: 15-30 minutes
**Prerequisites**: Basic Python knowledge, Docker (optional)

---

## Goal

By the end of this guide, you will have:

✅ Open AMI core framework running locally
✅ A simple self-evolving AI example deployed
✅ Understanding of the basic workflow
✅ Ability to explore further

---

## Prerequisites

### Required

- **Python 3.12+**: `python --version` should show 3.12 or higher
- **uv**: Package manager ([install instructions](https://docs.astral.sh/uv/))
- **Git**: For cloning repository
- **8GB RAM**: Minimum for basic examples
- **10GB Disk**: For installation and examples

### Optional

- **Docker**: For running distributed verification (recommended for production)
- **PostgreSQL**: For persistent DataOps storage (Docker Compose provided)
- **16GB+ RAM**: For larger models
- **GPU**: For ML training (CUDA-compatible)

---

## Step 1: Clone the Repository

```bash
# Clone with all submodules
git clone --recursive https://github.com/Independent-AI-Labs/OpenAMI.git
cd OpenAMI

# If you already cloned without --recursive:
git submodule update --init --recursive
```

**Verify structure**:
```bash
ls -la
# Should see: base/, browser/, compliance/, dataops/, domains/, files/,
#             nodes/, streams/, ux/, docs/, scripts/, etc.
```

---

## Step 2: Bootstrap the Environment

Open AMI uses `uv` for dependency management. Let's set it up:

```bash
# Install uv and Python 3.12 toolchain
python scripts/bootstrap_uv_python.py --auto

# Verify installation
uv --version
# Should output: uv 0.x.x (or newer)

python3.12 --version
# Should output: Python 3.12.x
```

---

## Step 3: Run Module Setup

Each Open AMI module needs its own virtual environment and dependencies:

```bash
# Run the root setup (provisions all modules)
python module_setup.py

# This will:
# 1. Create .venv/ in each module
# 2. Install dependencies
# 3. Run setup verification
# Time: ~5-10 minutes depending on network speed
```

**Expected output**:
```
============================================================
Setting up AMI-ORCHESTRATOR Root Development Environment
============================================================
[INFO] uv is installed and available
[INFO] Python 3.12 toolchain is available
[INFO] Creating root venv...
[INFO] Syncing dependencies with uv...
[INFO] Setting up module: base
[INFO] Setting up module: browser
...
[SUCCESS] All modules set up successfully!
============================================================
```

---

## Step 4: Start Core Services (Optional)

For persistence and distributed features, start the DataOps stack:

```bash
# Start PostgreSQL and Dgraph via Docker Compose
docker-compose -f docker-compose.data.yml up -d

# Verify services are running
docker ps
# Should show: postgres, dgraph-alpha, dgraph-zero, dgraph-ratel
```

**Skip this** if you just want to try in-memory examples.

---

## Step 5: Run Your First Example

Let's verify Open AMI is working with a simple test:

```bash
# Activate the base module environment
cd base
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the module tests
python scripts/run_tests.py

# Should see: All tests passed
```

---

## Step 6: Hello World - Simple SPN

Let's create a basic Secure Process Node (SPN):

```python
# Create: examples/hello_spn.py
from base.backend.dataops.core.storage_types import StorageConfig
from base.backend.dataops.core.unified_crud import UnifiedCRUD

# Initialize DataOps (in-memory for simplicity)
config = StorageConfig(storage_type="memory")
dao = UnifiedCRUD(config)

# Register a simple model
from dataclasses import dataclass

@dataclass
class HelloModel:
    id: str
    message: str
    version: int

dao.register_model("hello", HelloModel)

# Create an SPN-like operation (simplified)
print("🚀 Creating first entity in SPN-like environment...")
entity = HelloModel(
    id="msg_001",
    message="Hello from Open AMI!",
    version=1
)

# Store (this would be in an SPN with integrity verification)
result = dao.create("hello", entity.__dict__)
print(f"✅ Created: {result}")

# Retrieve
fetched = dao.read("hello", "msg_001")
print(f"✅ Retrieved: {fetched}")
```

**Run it**:
```bash
python examples/hello_spn.py

# Output:
# 🚀 Creating first entity in SPN-like environment...
# ✅ Created: {'id': 'msg_001', 'message': 'Hello from Open AMI!', 'version': 1}
# ✅ Retrieved: {'id': 'msg_001', 'message': 'Hello from Open AMI!', 'version': 1}
```

---

## Step 7: Understanding the Architecture

Open AMI has four layers:

```
GOVERNANCE LAYER
    ↕
INTELLIGENCE LAYER ← You'll work here (ML models, evolution)
    ↕
OPERATIONAL LAYER ← SPNs, verification (what you just used)
    ↕
FOUNDATION LAYER ← Axioms, protocols (configuration)
```

**What you just did**:
- Used `UnifiedCRUD` (Operational Layer component)
- Created data with potential integrity verification (SPN concept)
- This is the foundation for AI operations

---

## Step 8: Self-Evolution Example (Simplified)

Now let's see a simplified self-evolution loop:

```python
# Create: examples/simple_evolution.py
from typing import Dict, Any
import json

class SimplifiedEvolutionEngine:
    """
    Simplified demonstration of Open AMI evolution protocol.
    Real implementation uses AADL, formal proofs, distributed verification.
    """

    def __init__(self, initial_model: Dict[str, Any]):
        self.model = initial_model
        self.version = 1
        self.audit_log = []

    def analyze(self) -> Dict[str, Any]:
        """Step 1: Analyze current model performance"""
        print(f"\n📊 STEP 1: Analyzing model v{self.version}...")
        # In real system: metrics from monitoring
        analysis = {
            "current_accuracy": 0.85,
            "target_accuracy": 0.90,
            "trigger": "accuracy_below_target"
        }
        print(f"   Trigger: {analysis['trigger']}")
        return analysis

    def hypothesize(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: Formulate improvement hypothesis"""
        print(f"\n💡 STEP 2: Formulating hypothesis...")
        hypothesis = {
            "proposed_change": "increase_hidden_layers",
            "expected_improvement": 0.05,
            "rationale": "Current model underfitting on complex patterns"
        }
        print(f"   Hypothesis: {hypothesis['proposed_change']}")
        print(f"   Expected: +{hypothesis['expected_improvement']} accuracy")
        return hypothesis

    def test(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: Empirical testing (simplified)"""
        print(f"\n🧪 STEP 4: Testing proposed change...")
        # In real system: run on test suite
        test_results = {
            "new_accuracy": 0.91,
            "improvement": 0.06,
            "hypothesis_met": True
        }
        print(f"   Result: {test_results['new_accuracy']} accuracy")
        print(f"   Hypothesis: {'✅ MET' if test_results['hypothesis_met'] else '❌ FAILED'}")
        return test_results

    def generate_proof(self) -> Dict[str, Any]:
        """Step 5: Generate safety proof (simplified)"""
        print(f"\n🔒 STEP 5: Generating safety proof...")
        # In real system: formal proof in Lean/Coq
        proof = {
            "axioms_satisfied": ["no_harm", "explainable", "fair"],
            "properties_preserved": ["accuracy>=0.8", "latency<100ms"],
            "proof_hash": "0x3f4a7b9d..."
        }
        print(f"   Axioms checked: {len(proof['axioms_satisfied'])}")
        print(f"   Properties verified: {len(proof['properties_preserved'])}")
        return proof

    def verify(self, proof: Dict[str, Any]) -> bool:
        """Step 6: Distributed verification (simplified)"""
        print(f"\n✓ STEP 6: Verifying proof...")
        # In real system: 4/5 verifiers must approve
        verifier_votes = [True, True, True, True, False]  # 4/5 consensus
        approved = sum(verifier_votes) >= 4
        print(f"   Verifier votes: {sum(verifier_votes)}/5")
        print(f"   Consensus: {'✅ REACHED' if approved else '❌ FAILED'}")
        return approved

    def log_evolution(self, analysis, hypothesis, test_results, proof):
        """Step 7: Audit logging"""
        print(f"\n📝 STEP 7: Logging to immutable audit trail...")
        entry = {
            "version": self.version,
            "timestamp": "2025-10-02T12:00:00Z",
            "justification": {
                "hypothesis": hypothesis,
                "trigger": analysis["trigger"],
                "verification": test_results
            },
            "proof": proof
        }
        self.audit_log.append(entry)
        print(f"   Audit entry created: v{self.version} -> v{self.version+1}")

    def activate(self):
        """Step 8: Activate new version"""
        print(f"\n🚀 STEP 8: Activating new version...")
        self.version += 1
        # In real system: SDS coordinates deployment
        print(f"   Active version: v{self.version}")
        print(f"   Evolution complete! ✨")

    def evolve(self):
        """Execute full evolution protocol"""
        print("=" * 60)
        print(f"🧬 EVOLUTION PROTOCOL: v{self.version} -> v{self.version+1}")
        print("=" * 60)

        # Run 8-step protocol
        analysis = self.analyze()
        hypothesis = self.hypothesize(analysis)
        # (Step 3: Compile - skipped in simplified version)
        test_results = self.test(hypothesis)

        if not test_results["hypothesis_met"]:
            print("\n❌ Evolution REJECTED: Hypothesis not met")
            return False

        proof = self.generate_proof()
        verified = self.verify(proof)

        if not verified:
            print("\n❌ Evolution REJECTED: Verification failed")
            return False

        self.log_evolution(analysis, hypothesis, test_results, proof)
        self.activate()

        print("\n" + "=" * 60)
        print("✅ EVOLUTION SUCCESSFUL")
        print("=" * 60)
        return True

# Run the example
if __name__ == "__main__":
    print("🌟 Open AMI Self-Evolution Demo (Simplified)\n")

    # Initialize with simple model
    initial_model = {
        "type": "neural_network",
        "layers": 3,
        "accuracy": 0.85
    }

    engine = SimplifiedEvolutionEngine(initial_model)

    # Evolve once
    engine.evolve()

    # Show audit trail
    print("\n📚 Audit Trail:")
    print(json.dumps(engine.audit_log, indent=2))
```

**Run it**:
```bash
python examples/simple_evolution.py
```

**Expected output**:
```
🌟 Open AMI Self-Evolution Demo (Simplified)

============================================================
🧬 EVOLUTION PROTOCOL: v1 -> v2
============================================================

📊 STEP 1: Analyzing model v1...
   Trigger: accuracy_below_target

💡 STEP 2: Formulating hypothesis...
   Hypothesis: increase_hidden_layers
   Expected: +0.05 accuracy

🧪 STEP 4: Testing proposed change...
   Result: 0.91 accuracy
   Hypothesis: ✅ MET

🔒 STEP 5: Generating safety proof...
   Axioms checked: 3
   Properties verified: 2

✓ STEP 6: Verifying proof...
   Verifier votes: 4/5
   Consensus: ✅ REACHED

📝 STEP 7: Logging to immutable audit trail...
   Audit entry created: v1 -> v2

🚀 STEP 8: Activating new version...
   Active version: v2
   Evolution complete! ✨

============================================================
✅ EVOLUTION SUCCESSFUL
============================================================
```

---

## What Just Happened?

You ran a simplified version of Open AMI's **8-step evolution protocol**:

1. ✅ **Analyze**: Checked performance vs goals
2. ✅ **Hypothesize**: Proposed specific improvement
3. ⏭️ **Compile**: (Skipped - would use AADL → AAL → Model)
4. ✅ **Test**: Empirically validated hypothesis
5. ✅ **Prove**: Generated safety proof
6. ✅ **Verify**: Distributed verification (4/5 consensus)
7. ✅ **Log**: Created immutable audit entry
8. ✅ **Activate**: New version deployed

**In production Open AMI**:
- Step 3 uses real Meta-Compiler (AADL → AAL)
- Step 5 generates formal proofs (Lean/Coq)
- Step 6 uses distributed SPNs with HSM signing
- Step 7 writes to blockchain-like audit ledger
- Step 8 coordinates across SDS with CST snapshots

---

## Next Steps

### Learn More

1. **Understand the Architecture**
   - Read: [System Architecture](../architecture/system-architecture.md)
   - Read: [Four Pillars](../architecture/four-pillars.md)
   - Read: [Self-Evolution System](../architecture/self-evolution.md)

2. **Build Real Systems**
   - Guide: [Building Your First Self-Evolving AI](./first-self-evolving-ai.md)
   - Guide: [Implementing Compliance Constraints](./compliance-constraints.md)
   - Guide: [Setting up Distributed Verification](./distributed-verification.md)

3. **Explore Modules**
   - [Base Module](../modules/base.md) - Core infrastructure
   - [Compliance Module](../modules/compliance.md) - Governance
   - [DataOps Module](../modules/dataops.md) - Data pipeline

4. **Dive into Theory**
   - [Theoretical Framework](../theory/README.md)
   - [Bootstrapping Theory](../theory/bootstrapping.md)
   - [Formal Verification](../theory/formal-verification.md)

### Try Advanced Examples

```bash
# Navigate to examples directory
cd examples

# Available examples:
ls -la
# - hello_spn.py (you just ran this)
# - simple_evolution.py (you just ran this)
# - distributed_spn.py (multi-node example)
# - formal_proof_demo.py (real proof generation)
# - compliance_enforcement.py (compliance manifest)
# - full_stack_example.py (complete system)

# Try distributed example:
python distributed_spn.py
```

### Get Help

- **Documentation**: Browse [docs/openami/](../)
- **Issues**: [GitHub Issues](https://github.com/Independent-AI-Labs/OpenAMI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Independent-AI-Labs/OpenAMI/discussions)
- **Email**: tech@independentailabs.com

---

## Troubleshooting

### Common Issues

**1. "uv command not found"**

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# Add to PATH
export PATH="$HOME/.cargo/bin:$PATH"
```

**2. "Python 3.12 not found"**

```bash
# Let uv install Python 3.12
uv python install 3.12
uv python pin 3.12
```

**3. "Module not found" errors**

```bash
# Ensure you're in the module's venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Re-sync dependencies
uv sync --dev
```

**4. "Docker services not starting"**

```bash
# Check Docker is running
docker ps

# If not, start Docker daemon, then:
docker-compose -f docker-compose.data.yml up -d

# Check logs
docker-compose -f docker-compose.data.yml logs
```

**5. "Permission denied" on scripts**

```bash
# Make scripts executable
chmod +x scripts/*.py
chmod +x */scripts/*.py
```

---

## Summary

Congratulations! You've:

✅ Installed Open AMI
✅ Set up the development environment
✅ Understood the four-layer architecture
✅ Run a basic SPN example
✅ Seen the 8-step evolution protocol in action
✅ Know where to go next

**You're ready to build trustworthy, self-evolving AI systems with Open AMI!**

---

**Next Recommended Reading**:
- [Building Your First Self-Evolving AI](./first-self-evolving-ai.md) - Complete tutorial
- [System Architecture](../architecture/system-architecture.md) - Deep dive
- [Module Reference](../modules/README.md) - Explore capabilities

**Questions?** Ask in [Discussions](https://github.com/Independent-AI-Labs/OpenAMI/discussions) or email tech@independentailabs.com

---

**Was this guide helpful?** [Give feedback](https://github.com/Independent-AI-Labs/OpenAMI/issues/new?labels=documentation)
