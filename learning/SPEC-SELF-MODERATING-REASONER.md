# Self-Moderating Reasoner Specification

## 1. Mission & Scope

- Establish a lightweight distributed reasoning system using existing AMI infrastructure (`/nodes/launcher`, `/browser`, `/marketing/research`, `/ux/cms`, `/base/dataops`).
- Enable autonomous worker and moderator processes that spawn, validate, and terminate themselves without central orchestration.
- Integrate with BPMN workflows, MCP servers, and the bootstrapping provenance framework documented in `bootstrap.md` and `incremental.md`.
- Provide a pragmatic implementation that evolves into more sophisticated reasoning architectures while maintaining cryptographic provenance chains.

## 2. Core Concept

The Self-Moderating Reasoner is a distributed process-based reasoning system where:

- **Workers** are autonomous processes that perform tasks (research, analysis, synthesis).
- **Moderators** are autonomous processes that validate worker outputs and make approval/rejection decisions.
- **Each process decides its own fate**: spawn children, wait, or terminate based on local assessment.
- **No central queue or orchestrator**: processes use `/nodes/launcher` as a spawn primitive (like Unix fork()).
- **Shared state via MCP servers**: Browser MCP, Research MCP, and future Planning MCP act as the coordination substrate.
- **Communication via filesystem**: CMS comments in `/research/` directories, PID files, file locks, and file existence checks.
- **Cryptographic provenance chain**: Every process phones home before executing user code, establishing unbroken authentication and audit trail.

## 3. Architecture

### 3.1 Process Model

**Worker Scripts** (`learning/workers/*.sh` or `learning/workers/*.py`)

Simple scripts analogous to existing research automation. Each worker:

1. **Phones Home**: Authenticates with orchestrator before any user code execution, receives cryptographic token.
2. **Senses**: Calls MCP servers (Browser MCP for data, Research MCP for persistence).
3. **Acts**: Performs task (web search, data extraction, analysis).
4. **Decides**: Evaluates own completion status.
5. **Spawns or Terminates**: Either spawns next workers/moderators and exits, or just exits.
6. **Logs**: All stdout/stderr redirected to timestamped files (using existing Base worker management).

**Moderator Scripts** (`learning/moderators/*.sh` or `learning/moderators/*.py`)

Validation scripts that check worker outputs. Each moderator:

1. **Phones Home**: Authenticates, receives validation token linked to worker's provenance.
2. **Validates**: Reads worker output from `/research/` directories.
3. **Decides**: Approve, reject, or request corrections.
4. **Acts**: May perform cleanup, aggregation, or data transformation.
5. **Spawns or Terminates**: Spawns next stage workers or corrective workers, then exits.
6. **Signs**: Cryptographically signs approval decisions, extending provenance chain.

**Launcher Integration** (`/nodes/launcher`)

- Existing `LauncherSupervisor` extended with process hierarchy tracking (parent-child relationships).
- Python orchestrator (`learning/orchestrator.py`) wraps launcher MCP, provides helper functions for workers/moderators.
- Tracks process trees via new hierarchy models extending `ServiceRuntimeState`.

### 3.2 Infrastructure Mapping

| Layer                        | Implementation                    | Location                                                      |
|------------------------------|-----------------------------------|---------------------------------------------------------------|
| Process Management           | `/nodes/launcher` + extensions    | `nodes/backend/launcher/supervisor.py`                        |
| Hierarchy Tracking           | New hierarchy models + tracker    | `nodes/backend/launcher/hierarchy.py`                         |
| Cryptographic Provenance     | Signing service + chain validator | `learning/provenance/chain.py`                                |
| Data Collection & Validation | Browser MCP + Research MCP        | `browser/backend/mcp/`, `domains/marketing/backend/mcp/research/` |
| Communication                | CMS comments + filesystem signals | `/ux/cms`, `/research/` directories                           |
| Planning / PM                | Future MCP server on BPMN models  | `base/backend/dataops/models/bpmn.py` (future integration)    |
| Worker/Moderator Scripts     | Bash/Python scripts               | `learning/workers/`, `learning/moderators/`                   |
| Orchestrator                 | Python coordinator + auth service | `learning/orchestrator.py`                                    |

### 3.3 MCP Server Substrate

**Browser MCP** (`browser/backend/mcp/chrome/`)

- `web_search`: Discover content
- `browser_navigate`, `browser_extract`: Navigate and extract data
- `browser_capture`: Take screenshots for validation
- Shared browser sessions, cookies, screenshots accessible to all workers

**Research MCP** (`domains/marketing/backend/mcp/research/`)

- `create_research_workspace`, `define_research_schema`: Set up data structures
- `capture_research_record`: Persist validated records
- `append_research_audit`, `list_research_audit`: Track decisions and findings
- Shared research workspace under `/domains/marketing/research/`

**Planning MCP** (future, `base/backend/dataops` + BPMN models)

- `create_process`, `start_process_instance`: Decompose high-level goals
- `query_tasks`, `complete_task`: Coordinate work assignments
- Integration with GitHub Projects via API
- Uses `/base/backend/dataops/models/bpmn.py` workflow models

**CMS / Communication** (`ux/cms/`)

- Filesystem-based comment system (documented in `ux/cms/docs/spec.md`)
- Workers and moderators leave structured comments in research directories
- SSE event stream (`/api/events`) for change notifications

## 4. Cryptographic Provenance Chain

### 4.1 Genesis Kernel (Layer 0)

**Immutable Foundation**:

- Cryptographic root authority (master keypair generated once, private key HSM-protected in production)
- Core safety constraints enforced at spawn-time (cannot be bypassed)
- Immutable worker/moderator contract (script interface, exit codes, MCP tool usage)
- Hierarchical key derivation (BIP32-style) for infalsifiable token chain

**Implementation**: `learning/provenance/genesis.py`

```python
from cryptography.hazmat.primitives.asymmetric import ed25519

class GenesisKernel:
    """Immutable root authority for provenance chain."""

    # Burned into code at build time
    GENESIS_PUBLIC_KEY: Final[bytes]  # Root of all verification
    SAFETY_CONSTRAINTS: Final[frozenset[str]]  # Immutable rules

    @staticmethod
    def derive_child_keypair(
        parent_private_key: ed25519.Ed25519PrivateKey,
        child_pid: int,
    ) -> tuple[ed25519.Ed25519PrivateKey, bytes]:
        """Hierarchically derive child keypair from parent.

        Uses HKDF with parent private key material and child PID as context.
        Child's keypair is cryptographically bound to parent - infalsifiable.
        """

    @staticmethod
    def verify_lineage(
        token: ProcessToken,
        parent_token: ProcessToken | None,
        genesis_pubkey: bytes,
    ) -> bool:
        """Verify token's cryptographic lineage back to genesis.

        Checks:
        1. Token's signature is valid (self-signed with private key)
        2. Token's public key hierarchically derived from parent (or is genesis)
        3. Chain validates all the way to genesis public key
        """
```

### 4.2 Process Authentication ("Phone Home")

**Before any user code executes**:

1. **Parent derives child's keypair** using hierarchical derivation:
   - `child_privkey, child_pubkey = derive_child_keypair(parent_privkey, child_pid)`
   - Cryptographically infalsifiable - only parent can derive this keypair

2. **Parent spawns child** via launcher, passing in environment:
   - `PARENT_TOKEN`: Parent's token (contains parent's public key)
   - `CHILD_PRIVATE_KEY`: Child's derived private key (base64 encoded)
   - `CHILD_PUBLIC_KEY`: Child's derived public key (base64 encoded)

3. **Launcher starts child process** (stdout/stderr already redirected to log files)

4. **Child self-generates infalsifiable token**:
   ```python
   child_token = ProcessToken(
       pid=os.getpid(),
       public_key=child_pubkey,  # From environment
       parent_public_key=parent_token.public_key,
       script_path=__file__,
       issued_at=datetime.now(UTC),
       signature=sign(child_privkey, payload)  # Self-signed proof
   )
   ```

5. **Child phones home** to orchestrator: `POST /auth/register-process`
   - Presents self-generated token + parent's token
   - Orchestrator **validates** (but doesn't issue new token)

6. **Orchestrator validation**:
   - Verifies child token signature (proves child holds derived private key)
   - Verifies child's pubkey hierarchically derived from parent's pubkey
   - Verifies parent token's lineage back to genesis
   - Checks authorization policy (parent allowed to spawn this script)
   - Confirms no safety constraint violations (depth, quotas, allowlists)

7. **Orchestrator registers** (if validation passes):
   - Creates `ProvenanceEntry` linking child to parent
   - Updates parent's entry with spawned child PID
   - Returns registration confirmation (NOT a new token - child already has infalsifiable proof)

8. **Child uses its token** for:
   - All MCP calls (servers verify signature + lineage)
   - Deriving keypairs for any children it spawns

**Security Properties**:
- **Infalsifiable**: Only holder of derived private key can generate valid signature
- **Hierarchical**: Child's public key mathematically derived from parent's
- **Offline verifiable**: Anyone with genesis public key can verify entire chain
- **Policy enforcement**: Orchestrator can reject registration despite valid cryptography
- **Revocable**: Orchestrator maintains blacklist of revoked public keys
- **No forgery**: Even orchestrator can't forge tokens (doesn't have private keys)

**Implementation**: `learning/orchestrator.py`

```python
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import base64


class ProcessToken(BaseModel):
    """Self-generated cryptographically infalsifiable token."""

    pid: int
    public_key: bytes  # This process's public key (derived from parent)
    parent_public_key: bytes | None  # Parent's public key (for verification)
    script_path: str
    issued_at: datetime
    signature: bytes  # Self-signed with derived private key

    def verify_signature(self) -> bool:
        """Verify this token's self-signature."""
        try:
            pubkey = ed25519.Ed25519PublicKey.from_public_bytes(self.public_key)
            pubkey.verify(self.signature, self._signing_payload())
            return True
        except Exception:
            return False

    def verify_lineage(
        self,
        parent_token: "ProcessToken | None",
        genesis_public_key: bytes,
    ) -> bool:
        """Verify hierarchical derivation back to genesis.

        Returns True if:
        1. This token's signature is valid
        2. This token's public key matches parent's (if root)
           OR parent_public_key field matches actual parent token
        3. Parent chain validates recursively
        """
        # Verify self-signature
        if not self.verify_signature():
            return False

        # If root token, verify against genesis
        if self.parent_public_key is None:
            return self.public_key == genesis_public_key

        # Verify parent exists and matches our parent_public_key field
        if parent_token is None:
            return False

        if parent_token.public_key != self.parent_public_key:
            return False

        # Recursively verify parent's lineage
        return parent_token.verify_lineage(None, genesis_public_key)

    def _signing_payload(self) -> bytes:
        """Payload that was signed with private key."""
        return json.dumps({
            "pid": self.pid,
            "public_key": base64.b64encode(self.public_key).decode(),
            "parent_public_key": base64.b64encode(self.parent_public_key).decode()
                if self.parent_public_key else None,
            "script_path": self.script_path,
            "issued_at": self.issued_at.isoformat(),
        }, sort_keys=True).encode()

    def serialize(self) -> str:
        """Serialize to pass in environment variable."""
        return json.dumps({
            "pid": self.pid,
            "public_key": base64.b64encode(self.public_key).decode(),
            "parent_public_key": base64.b64encode(self.parent_public_key).decode()
                if self.parent_public_key else None,
            "script_path": self.script_path,
            "issued_at": self.issued_at.isoformat(),
            "signature": base64.b64encode(self.signature).decode(),
        })

    @classmethod
    def deserialize(cls, token_str: str) -> "ProcessToken":
        """Deserialize from environment variable."""
        data = json.loads(token_str)
        return cls(
            pid=data["pid"],
            public_key=base64.b64decode(data["public_key"]),
            parent_public_key=base64.b64decode(data["parent_public_key"])
                if data.get("parent_public_key") else None,
            script_path=data["script_path"],
            issued_at=datetime.fromisoformat(data["issued_at"]),
            signature=base64.b64decode(data["signature"]),
        )


def derive_child_keypair(
    parent_private_key: ed25519.Ed25519PrivateKey,
    child_pid: int,
) -> tuple[ed25519.Ed25519PrivateKey, bytes]:
    """Hierarchically derive child keypair from parent.

    Uses HKDF to derive deterministic child key material from parent's
    private key bytes + child PID as context.

    This creates an infalsifiable chain - only someone with parent's
    private key can derive child's keypair.
    """
    # Extract parent private key bytes
    parent_key_bytes = parent_private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Derive child key material using HKDF
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # Ed25519 key size
        salt=None,
        info=f"child_pid_{child_pid}".encode(),
    )
    child_key_bytes = hkdf.derive(parent_key_bytes)

    # Create child keypair from derived material
    child_private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
        child_key_bytes
    )
    child_public_key = child_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    return child_private_key, child_public_key
```

### 4.3 Provenance Chain Structure

**Every process spawn creates immutable audit entry**:

```python
class ProvenanceEntry(StorageModel):
    """Immutable entry in provenance chain."""

    # Process identity
    process_pid: int
    process_token: str  # Serialized ProcessToken
    script_path: str

    # Hierarchy
    parent_pid: int | None
    parent_entry_uid: str | None  # Links to parent's entry

    # Lifecycle
    spawned_at: datetime
    terminated_at: datetime | None
    exit_code: int | None

    # Work outputs
    research_workspace: str | None
    output_records: list[str]  # UIDs of created records
    spawned_children: list[int]  # PIDs of spawned children

    # Validation (if moderator)
    validated_worker_pid: int | None
    validation_decision: str | None  # "approve", "reject", "correct"
    validation_signature: str | None  # Cryptographic signature

    # Audit
    stdout_log_path: str
    stderr_log_path: str
    mcp_calls: list[dict[str, Any]]  # Log of all MCP interactions
```

**Chain Properties**:

1. **Unbroken lineage**: Every process links to parent via `parent_entry_uid`
2. **Cryptographic verification**: Signatures verify back to genesis kernel
3. **Immutable**: Entries written once, never modified
4. **Auditable**: Complete log of decisions, validations, and spawns
5. **Reproducible**: Can replay process tree from provenance records

### 4.4 Moderator Signing

**When moderator approves work**:

```python
def sign_validation(
    self,
    worker_pid: int,
    decision: Literal["approve", "reject", "correct"],
    rationale: str,
) -> ValidationSignature:
    """Cryptographically sign validation decision."""

    payload = {
        "moderator_pid": self.pid,
        "worker_pid": worker_pid,
        "decision": decision,
        "rationale": rationale,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    signature = hmac.new(
        self.process_token.signature.encode(),
        json.dumps(payload, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()

    return ValidationSignature(
        payload=payload,
        signature=signature,
        moderator_token=self.process_token.signature
    )
```

## 5. Process Lifecycle with Provenance

### 5.1 Worker Lifecycle

```bash
#!/usr/bin/env bash
# learning/workers/worker-research.sh

set -euo pipefail

# PHONE HOME: Self-generate token from derived keys, register with orchestrator
MY_PID=$$

# Parent passed us our derived keypair
PARENT_TOKEN="${PARENT_TOKEN:-}"  # Parent's token (contains parent's pubkey)
CHILD_PRIVKEY="${CHILD_PRIVATE_KEY:-}"  # Our derived private key
CHILD_PUBKEY="${CHILD_PUBLIC_KEY:-}"  # Our derived public key

# Generate our self-signed token
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
OUR_TOKEN=$(python3 -c "
import os, sys, json, base64
from cryptography.hazmat.primitives.asymmetric import ed25519

# Load our keys
privkey = ed25519.Ed25519PrivateKey.from_private_bytes(
    base64.b64decode('$CHILD_PRIVKEY')
)
pubkey_bytes = base64.b64decode('$CHILD_PUBKEY')

# Load parent token to get parent's pubkey
parent_token = json.loads('$PARENT_TOKEN') if '$PARENT_TOKEN' else None
parent_pubkey = parent_token['public_key'] if parent_token else None

# Create signing payload
payload = json.dumps({
    'pid': $MY_PID,
    'public_key': '$CHILD_PUBKEY',
    'parent_public_key': parent_pubkey,
    'script_path': '$0',
    'issued_at': '$TIMESTAMP'
}, sort_keys=True).encode()

# Self-sign
signature = privkey.sign(payload)

# Output our token
print(json.dumps({
    'pid': $MY_PID,
    'public_key': '$CHILD_PUBKEY',
    'parent_public_key': parent_pubkey,
    'script_path': '$0',
    'issued_at': '$TIMESTAMP',
    'signature': base64.b64encode(signature).decode()
}))
")

# Register with orchestrator (presents self-signed token + parent token for validation)
REGISTRATION=$(curl -s -X POST http://localhost:8320/auth/register-process \
    -H "Content-Type: application/json" \
    -d "{
        \"child_token\": $OUR_TOKEN,
        \"parent_token\": \"$PARENT_TOKEN\"
    }")

# Check registration succeeded
if ! echo "$REGISTRATION" | jq -e '.registered' > /dev/null; then
    echo "ERROR: Orchestrator rejected registration: $(echo "$REGISTRATION" | jq -r '.error')" >&2
    exit 1
fi

# Export our token for children to use
export PARENT_TOKEN="$OUR_TOKEN"

# Store private key for deriving children's keys
export MY_PRIVATE_KEY="$CHILD_PRIVKEY"

# NOW user code can execute
WORKSPACE="$1"
TOPIC="$2"

# SENSE & ACT: Call Browser MCP (includes token for auth)
RESULTS=$(mcp browser web_search \
    --auth-token "$PROCESS_TOKEN" \
    --query "$TOPIC")

# Persist via Research MCP
echo "$RESULTS" | jq -r '.results[]' | while read -r url; do
    DATA=$(mcp browser browser_extract \
        --auth-token "$PROCESS_TOKEN" \
        --url "$url")

    mcp research capture_research_record \
        --auth-token "$PROCESS_TOKEN" \
        --workspace "$WORKSPACE" \
        --schema "web_content" \
        --data "$DATA" \
        --sources "$url"
done

# DECIDE & SPAWN
if [ -n "$RESULTS" ]; then
    # Derive moderator's keypair (using our private key + their PID)
    # We'll get the PID after spawn, so spawn then derive

    # Spawn moderator
    SPAWN_RESULT=$(mcp launcher spawn_process \
        --script-path learning/moderators/moderator-quality.sh \
        --parent-pid "$MY_PID" \
        --args "$WORKSPACE")

    MODERATOR_PID=$(echo "$SPAWN_RESULT" | jq -r '.pid')

    # Derive moderator's keypair
    MODERATOR_KEYS=$(python3 -c "
import base64, json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Load our private key
parent_privkey = ed25519.Ed25519PrivateKey.from_private_bytes(
    base64.b64decode('$MY_PRIVATE_KEY')
)

# Derive child key material
parent_key_bytes = parent_privkey.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption()
)

hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
    info=f'child_pid_$MODERATOR_PID'.encode())
child_key_bytes = hkdf.derive(parent_key_bytes)

# Create child keypair
child_privkey = ed25519.Ed25519PrivateKey.from_private_bytes(child_key_bytes)
child_pubkey = child_privkey.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)

print(json.dumps({
    'private_key': base64.b64encode(child_key_bytes).decode(),
    'public_key': base64.b64encode(child_pubkey).decode()
}))
")

    # Pass derived keys to moderator via environment
    PARENT_TOKEN="$OUR_TOKEN" \
    CHILD_PRIVATE_KEY=$(echo "$MODERATOR_KEYS" | jq -r '.private_key') \
    CHILD_PUBLIC_KEY=$(echo "$MODERATOR_KEYS" | jq -r '.public_key') \
    mcp launcher update_process_env \
        --pid "$MODERATOR_PID" \
        --env-vars "$MODERATOR_KEYS"

    # Similar for analyzer (with delay)
    sleep 5
    # ... (same pattern)
fi

# TERMINATE: Children continue independently
exit 0
```

**Key Points**:

- Stdout/stderr already redirected by launcher adapter (LocalProcessAdapter:72-80)
- Token passed via environment variable to children
- All MCP calls include auth token for validation
- Orchestrator logs all MCP calls to provenance entry

### 5.2 Moderator Lifecycle

```python
#!/usr/bin/env python3
# learning/moderators/moderator-quality.py

import os
import sys
from learning.orchestrator import ReasonerOrchestrator, register_process

# PHONE HOME: Present parent's token, get our own
token = register_process(
    pid=os.getpid(),
    parent_token=os.environ.get("PROCESS_TOKEN"),  # Parent's token
    script_path=__file__
)

workspace = sys.argv[1]
orch = ReasonerOrchestrator(workspace, process_token=token)

# VALIDATE: Check research outputs
records = orch.call_mcp("research", "list_records", workspace=workspace)
errors = [r for r in records if r.get("validation_errors")]

# DECIDE
if not errors:
    # APPROVE: Sign validation
    validation = orch.sign_validation(
        worker_pid=os.getppid(),  # Parent was the worker
        decision="approve",
        rationale=f"All {len(records)} records passed schema validation"
    )

    orch.call_mcp("research", "append_research_audit",
        workspace=workspace,
        note=f"Quality validation passed: {len(records)} records approved",
        signature=validation.signature
    )

    sys.exit(0)
else:
    # REJECT: Log issues and spawn corrective worker
    validation = orch.sign_validation(
        worker_pid=os.getppid(),
        decision="reject",
        rationale=f"Found {len(errors)} records with validation errors"
    )

    orch.call_mcp("research", "append_research_audit",
        workspace=workspace,
        note=f"Quality issues found: {len(errors)} records failed validation",
        signature=validation.signature
    )

    # SPAWN: Corrective worker
    orch.spawn(
        "learning/workers/worker-fix-data.sh",
        args=[workspace, str(len(errors))],
        parent_token=token
    )

    sys.exit(1)
```

### 5.3 Process Tree with Provenance

**User invokes**:
```bash
mcp launcher spawn_process \
    --script-path learning/workers/worker-research.sh \
    --args "AI agents" "ai-research"
```

**Process tree grows with signed chain**:

```
worker-research.sh (PID 1001, Token: sig_ABC...123 [root])
  │
  ├─ moderator-quality.py (PID 1002, Token: sig_DEF...456 [parent: sig_ABC...123])
  │   │
  │   └─ worker-fix-data.sh (PID 1005, Token: sig_GHI...789 [parent: sig_DEF...456])
  │       │
  │       └─ moderator-quality.py (PID 1006, Token: sig_JKL...012 [parent: sig_GHI...789])
  │
  └─ worker-analyze.sh (PID 1003, Token: sig_MNO...345 [parent: sig_ABC...123])
      │
      ├─ worker-synthesize.sh (PID 1004, Token: sig_PQR...678 [parent: sig_MNO...345])
      │
      └─ moderator-final.py (PID 1007, Token: sig_STU...901 [parent: sig_MNO...345])
```

**Provenance Chain**:

Every node has `ProvenanceEntry` with:
- Signature linking to parent
- Complete MCP call log
- Validation signatures (for moderators)
- Output record UIDs
- Stdout/stderr log paths

## 6. Launcher Extensions for Hierarchy

### 6.1 Process Hierarchy Models

**New file**: `nodes/backend/launcher/hierarchy.py`

```python
"""Process hierarchy tracking for self-moderating reasoner."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from nodes.backend.launcher.supervisor import ServiceState


class ProcessRole(str, Enum):
    """Role of process in reasoning hierarchy."""

    ROOT = "root"
    WORKER = "worker"
    MODERATOR = "moderator"


@dataclass
class ProcessNode:
    """Node in process hierarchy tree."""

    pid: int
    service_id: str
    script_path: str
    args: list[str]
    role: ProcessRole

    parent_pid: int | None
    children: list[ProcessNode] = field(default_factory=list)

    state: ServiceState
    spawned_at: datetime
    terminated_at: datetime | None = None
    exit_code: int | None = None

    # Provenance
    process_token: str | None = None
    provenance_entry_uid: str | None = None

    # Logs (redirected by LocalProcessAdapter)
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None


class HierarchyTracker:
    """Track process spawning relationships."""

    def __init__(self):
        self._nodes: dict[int, ProcessNode] = {}
        self._roots: set[int] = set()
        # Track children orphaned when parent dies
        self._orphaned_lineage: dict[int, int] = {}  # child_pid -> dead_parent_pid

    def register_spawn(
        self,
        pid: int,
        service_id: str,
        script_path: str,
        args: list[str],
        role: ProcessRole,
        parent_pid: int | None = None,
        process_token: str | None = None,
        provenance_entry_uid: str | None = None,
    ) -> ProcessNode:
        """Register a newly spawned process.

        Parent may already be dead - we still record the relationship.
        """
        node = ProcessNode(
            pid=pid,
            service_id=service_id,
            script_path=script_path,
            args=args,
            role=role,
            parent_pid=parent_pid,
            state=ServiceState.RUNNING,
            spawned_at=datetime.now(UTC),
            process_token=process_token,
            provenance_entry_uid=provenance_entry_uid,
        )
        self._nodes[pid] = node

        if parent_pid is None:
            # Root process
            self._roots.add(pid)
        else:
            parent = self._nodes.get(parent_pid)
            if parent:
                # Parent still tracked - link directly
                parent.children.append(node)
            else:
                # Parent already exited - record lineage anyway
                self._orphaned_lineage[pid] = parent_pid
                # Still track as potential root for tree operations
                self._roots.add(pid)

        return node

    def get_tree(self, root_pid: int) -> ProcessNode | None:
        """Get full tree including processes spawned by dead root."""
        root = self._nodes.get(root_pid)
        if not root:
            return None

        # Recursively attach orphaned children
        self._attach_orphaned_children(root)
        return root

    def _attach_orphaned_children(self, node: ProcessNode) -> None:
        """Find and attach children that were orphaned."""
        for child_pid, dead_parent_pid in self._orphaned_lineage.items():
            if dead_parent_pid == node.pid:
                child = self._nodes.get(child_pid)
                if child and child not in node.children:
                    node.children.append(child)
                    # Recursively attach their children
                    self._attach_orphaned_children(child)

    def kill_tree(self, root_pid: int, force: bool = False) -> list[int]:
        """Kill entire subtree, returns list of terminated PIDs.

        Post-order traversal: kill children first.
        """
        import os
        import signal

        node = self._nodes.get(root_pid)
        if not node:
            return []

        terminated = []

        # Recursively kill children first
        for child in node.children:
            terminated.extend(self.kill_tree(child.pid, force))

        # Kill this node
        try:
            signal_type = signal.SIGKILL if force else signal.SIGTERM
            os.kill(node.pid, signal_type)
            node.state = ServiceState.STOPPED
            node.terminated_at = datetime.now(UTC)
            terminated.append(node.pid)
        except ProcessLookupError:
            # Already dead
            pass

        return terminated

    def update_node_state(
        self,
        pid: int,
        state: ServiceState | None = None,
        exit_code: int | None = None,
        stdout_log_path: str | None = None,
        stderr_log_path: str | None = None,
    ) -> None:
        """Update node state (called by launcher adapter)."""
        node = self._nodes.get(pid)
        if not node:
            return

        if state is not None:
            node.state = state
            if state == ServiceState.STOPPED:
                node.terminated_at = datetime.now(UTC)

        if exit_code is not None:
            node.exit_code = exit_code

        if stdout_log_path is not None:
            node.stdout_log_path = stdout_log_path

        if stderr_log_path is not None:
            node.stderr_log_path = stderr_log_path
```

### 6.2 Launcher MCP Extensions

**Add to**: `nodes/backend/mcp/launcher/tools.py`

```python
"""Extended launcher MCP tools for process hierarchy."""

from nodes.backend.launcher.hierarchy import HierarchyTracker, ProcessRole


async def spawn_process(
    supervisor: LauncherSupervisor,
    script_path: str,
    args: list[str] | None = None,
    parent_pid: int | None = None,
    parent_token: str | None = None,
    working_dir: str | None = None,
) -> dict[str, Any]:
    """Spawn a new process and track it in hierarchy.

    Args:
        supervisor: Launcher supervisor instance
        script_path: Path to script to execute
        args: Command-line arguments
        parent_pid: PID of parent process (for hierarchy)
        parent_token: Cryptographic token from parent (for provenance)
        working_dir: Working directory for process

    Returns:
        Dict with service_id, pid, token (from orchestrator auth)
    """
    import uuid
    from pathlib import Path
    from nodes.backend.launcher.config import (
        ServiceSpec, ExecutionConfig, LocalExecutionConfig
    )

    # Determine process role from script path
    role = ProcessRole.ROOT
    if parent_pid is not None:
        if "moderator" in script_path:
            role = ProcessRole.MODERATOR
        else:
            role = ProcessRole.WORKER

    # Create dynamic service spec
    service_id = f"reasoner-{uuid.uuid4().hex[:8]}"
    spec = ServiceSpec(
        service_id=service_id,
        summary=f"Reasoner: {Path(script_path).name}",
        module="learning",
        execution=ExecutionConfig(
            local=LocalExecutionConfig(
                enabled=True,
                kind="local",
                command=[script_path] + (args or []),
                cwd=Path(working_dir) if working_dir else None,
                env={"PROCESS_TOKEN": parent_token} if parent_token else {}
            )
        )
    )

    # Add to supervisor and start
    supervisor._runtimes[service_id] = ServiceRuntime(spec=spec)
    await supervisor.start([service_id])

    # Get PID from adapter metadata
    runtime = supervisor._runtimes[service_id]
    metadata = await runtime.adapter.collect_metadata()
    pid = metadata.get("pid")

    # Register in hierarchy
    if not hasattr(supervisor, "_hierarchy"):
        supervisor._hierarchy = HierarchyTracker()

    # Process will authenticate with orchestrator to get token
    # We register with placeholder, orchestrator updates later
    node = supervisor._hierarchy.register_spawn(
        pid=pid,
        service_id=service_id,
        script_path=script_path,
        args=args or [],
        role=role,
        parent_pid=parent_pid,
        process_token=None,  # Will be set by orchestrator
        provenance_entry_uid=None,  # Will be set by orchestrator
    )

    # Extract log paths from metadata
    stdout_log = metadata.get("log_path")
    if stdout_log:
        supervisor._hierarchy.update_node_state(
            pid=pid,
            stdout_log_path=stdout_log,
            stderr_log_path=stdout_log  # LocalProcessAdapter merges them
        )

    return {
        "service_id": service_id,
        "pid": pid,
        "script_path": script_path,
        "args": args or [],
        "role": role.value,
        "parent_pid": parent_pid,
        "log_path": stdout_log,
    }


async def get_process_tree(
    supervisor: LauncherSupervisor,
    root_pid: int,
) -> dict[str, Any]:
    """Get full process tree starting from root_pid."""

    if not hasattr(supervisor, "_hierarchy"):
        return {"error": "No hierarchy tracker initialized"}

    tree = supervisor._hierarchy.get_tree(root_pid)
    if not tree:
        return {"error": f"No process found with PID {root_pid}"}

    def serialize_node(node: ProcessNode) -> dict[str, Any]:
        return {
            "pid": node.pid,
            "service_id": node.service_id,
            "script_path": node.script_path,
            "args": node.args,
            "role": node.role.value,
            "parent_pid": node.parent_pid,
            "state": node.state.value,
            "spawned_at": node.spawned_at.isoformat(),
            "terminated_at": node.terminated_at.isoformat() if node.terminated_at else None,
            "exit_code": node.exit_code,
            "provenance_entry_uid": node.provenance_entry_uid,
            "stdout_log_path": node.stdout_log_path,
            "stderr_log_path": node.stderr_log_path,
            "children": [serialize_node(child) for child in node.children],
        }

    return serialize_node(tree)


async def kill_process_tree(
    supervisor: LauncherSupervisor,
    root_pid: int,
    force: bool = False,
) -> dict[str, Any]:
    """Kill entire process tree starting from root_pid."""

    if not hasattr(supervisor, "_hierarchy"):
        return {"error": "No hierarchy tracker initialized"}

    terminated = supervisor._hierarchy.kill_tree(root_pid, force)

    return {
        "root_pid": root_pid,
        "terminated_pids": terminated,
        "count": len(terminated),
    }
```

## 7. Orchestrator & Provenance Service

**New file**: `learning/orchestrator.py`

```python
"""Orchestrator helpers for Self-Moderating Reasoner.

Provides:
- Process authentication ("phone home")
- Cryptographic token issuance
- Provenance chain management
- Helper functions for workers/moderators
"""

import hashlib
import hmac
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from base.backend.dataops.models.base_model import StorageModel
from base.backend.dataops.services.unified_crud import UnifiedCRUD


class ProcessToken(BaseModel):
    """Cryptographically signed process authentication token."""

    pid: int
    parent_pid: int | None
    script_path: str
    issued_at: datetime
    parent_signature: str | None  # Links to parent in chain
    signature: str  # Signed by orchestrator using genesis key

    def verify(self, genesis_secret: bytes) -> bool:
        """Verify signature chain."""
        payload = f"{self.pid}:{self.script_path}:{self.issued_at.isoformat()}"
        if self.parent_signature:
            payload = f"{payload}:{self.parent_signature}"

        expected = hmac.new(
            genesis_secret,
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, self.signature)

    def serialize(self) -> str:
        """Serialize to pass in environment variable."""
        return json.dumps({
            "pid": self.pid,
            "parent_pid": self.parent_pid,
            "script_path": self.script_path,
            "issued_at": self.issued_at.isoformat(),
            "parent_signature": self.parent_signature,
            "signature": self.signature,
        })

    @classmethod
    def deserialize(cls, token_str: str) -> "ProcessToken":
        """Deserialize from environment variable."""
        data = json.loads(token_str)
        return cls(
            pid=data["pid"],
            parent_pid=data.get("parent_pid"),
            script_path=data["script_path"],
            issued_at=datetime.fromisoformat(data["issued_at"]),
            parent_signature=data.get("parent_signature"),
            signature=data["signature"],
        )


class ProvenanceEntry(StorageModel):
    """Immutable entry in provenance chain."""

    # Process identity
    process_pid: int
    process_token_json: str  # Serialized ProcessToken
    script_path: str

    # Hierarchy
    parent_pid: int | None
    parent_entry_uid: str | None  # Links to parent's entry

    # Lifecycle
    spawned_at: datetime
    terminated_at: datetime | None = None
    exit_code: int | None = None

    # Work outputs
    research_workspace: str | None = None
    output_records: list[str] = []  # UIDs of created records
    spawned_children: list[int] = []  # PIDs of spawned children

    # Validation (if moderator)
    validated_worker_pid: int | None = None
    validation_decision: str | None = None  # "approve", "reject", "correct"
    validation_signature: str | None = None  # Cryptographic signature

    # Audit
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    mcp_calls: list[dict[str, Any]] = []  # Log of all MCP interactions

    class Meta:
        """Storage configuration."""
        path = "learning_provenance_entries"
        indexes = [
            {"field": "process_pid", "type": "hash"},
            {"field": "parent_pid", "type": "hash"},
            {"field": "spawned_at", "type": "datetime"},
        ]


class ValidationSignature(BaseModel):
    """Cryptographically signed validation decision."""

    moderator_pid: int
    worker_pid: int
    decision: str  # "approve", "reject", "correct"
    rationale: str
    timestamp: datetime
    signature: str
    moderator_token_sig: str  # Link to moderator's token


class AuthService:
    """Process authentication and token issuance service."""

    def __init__(self, genesis_secret: bytes):
        self.genesis_secret = genesis_secret
        self.crud = UnifiedCRUD()

    def register_process(
        self,
        pid: int,
        script_path: str,
        parent_token_str: str | None = None,
    ) -> ProcessToken:
        """Register process and issue new token.

        Called when child process "phones home" presenting parent's token.

        Args:
            pid: Child's process ID
            script_path: Child's script path
            parent_token_str: Parent's token (serialized) - proves authorization to spawn

        Returns:
            New token for child (signed, chaining to parent)

        Raises:
            ValueError: If parent token invalid or spawn unauthorized
        """
        # Validate script path against allowlist
        self._validate_script_path(script_path)

        # Parse and validate parent token
        parent_token = None
        parent_pid = None
        parent_signature = None
        parent_entry_uid = None

        if parent_token_str:
            parent_token = ProcessToken.deserialize(parent_token_str)

            # CRITICAL: Verify parent token signature chain
            if not parent_token.verify(self.genesis_secret):
                raise ValueError("Invalid parent token signature - chain broken")

            # Check parent is authorized to spawn this script type
            if not self._authorized_to_spawn(parent_token, script_path):
                raise ValueError(
                    f"Parent {parent_token.pid} not authorized to spawn {script_path}"
                )

            parent_pid = parent_token.pid
            parent_signature = parent_token.signature

            # Find parent's provenance entry to link to
            parent_entries = self.crud.read(
                ProvenanceEntry,
                filters={"process_pid": parent_pid},
                limit=1
            )
            if parent_entries:
                parent_entry_uid = parent_entries[0].uid
                # Update parent's entry with spawned child
                parent_entries[0].spawned_children.append(pid)
                self.crud.update(parent_entries[0])

        # Issue new token for child (chains to parent)
        token = ProcessToken(
            pid=pid,
            parent_pid=parent_pid,
            script_path=script_path,
            issued_at=datetime.now(UTC),
            parent_signature=parent_signature,  # Links to parent's token
            signature=self._sign_token(pid, script_path, parent_signature),
        )

        # Create provenance entry for child
        entry = ProvenanceEntry(
            process_pid=pid,
            process_token_json=token.serialize(),
            script_path=script_path,
            parent_pid=parent_pid,
            parent_entry_uid=parent_entry_uid,  # Links to parent's entry
            spawned_at=token.issued_at,
        )

        self.crud.create(entry)

        return token

    def _authorized_to_spawn(
        self,
        parent_token: ProcessToken,
        child_script_path: str,
    ) -> bool:
        """Check if parent is authorized to spawn child script.

        Authorization rules:
        - Workers can spawn moderators
        - Workers can spawn other workers
        - Moderators can spawn corrective workers
        - Moderators cannot spawn other moderators (prevents validation bypass)
        """
        parent_path = Path(parent_token.script_path)
        child_path = Path(child_script_path)

        parent_is_worker = "workers" in parent_path.parts
        parent_is_moderator = "moderators" in parent_path.parts
        child_is_worker = "workers" in child_path.parts
        child_is_moderator = "moderators" in child_path.parts

        # Workers can spawn anything
        if parent_is_worker:
            return True

        # Moderators can only spawn workers (for corrections)
        if parent_is_moderator and child_is_worker:
            return True

        # Moderators cannot spawn other moderators (security)
        if parent_is_moderator and child_is_moderator:
            return False

        return False

    def _sign_token(
        self,
        pid: int,
        script_path: str,
        parent_signature: str | None,
    ) -> str:
        """Sign token using genesis secret."""
        payload = f"{pid}:{script_path}:{datetime.now(UTC).isoformat()}"
        if parent_signature:
            payload = f"{payload}:{parent_signature}"

        return hmac.new(
            self.genesis_secret,
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def _validate_script_path(self, script_path: str) -> None:
        """Validate script against safety constraints."""
        # Must be in learning/workers or learning/moderators
        normalized = Path(script_path).resolve()
        allowed_dirs = [
            Path("learning/workers"),
            Path("learning/moderators"),
        ]

        if not any(
            str(normalized).startswith(str(d.resolve()))
            for d in allowed_dirs
        ):
            raise ValueError(
                f"Script path {script_path} not in allowed directories"
            )

    def update_provenance_exit(
        self,
        pid: int,
        exit_code: int,
        stdout_log_path: str | None = None,
        stderr_log_path: str | None = None,
    ) -> None:
        """Update provenance entry when process exits."""
        entries = self.crud.read(
            ProvenanceEntry,
            filters={"process_pid": pid},
            limit=1
        )

        if not entries:
            return

        entry = entries[0]
        entry.terminated_at = datetime.now(UTC)
        entry.exit_code = exit_code

        if stdout_log_path:
            entry.stdout_log_path = stdout_log_path
        if stderr_log_path:
            entry.stderr_log_path = stderr_log_path

        self.crud.update(entry)

    def log_mcp_call(
        self,
        pid: int,
        server: str,
        tool: str,
        args: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Log MCP call to provenance entry."""
        entries = self.crud.read(
            ProvenanceEntry,
            filters={"process_pid": pid},
            limit=1
        )

        if not entries:
            return

        entry = entries[0]
        entry.mcp_calls.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "server": server,
            "tool": tool,
            "args": args,
            "result": result,
        })

        self.crud.update(entry)


class ReasonerOrchestrator:
    """Helper for distributed reasoning processes."""

    def __init__(
        self,
        workspace_root: Path,
        process_token: ProcessToken | None = None,
    ):
        self.workspace_root = workspace_root
        self.control_dir = workspace_root / ".control"
        self.locks_dir = workspace_root / ".locks"
        self.control_dir.mkdir(parents=True, exist_ok=True)
        self.locks_dir.mkdir(parents=True, exist_ok=True)

        self.process_token = process_token
        self.pid = os.getpid()
        self.crud = UnifiedCRUD()

    def spawn(
        self,
        script_path: str,
        args: list[str] | None = None,
        delay: float = 0,
    ) -> int:
        """Spawn a new worker/moderator process.

        Returns PID of spawned process.
        """
        if delay > 0:
            time.sleep(delay)

        # Call launcher MCP via subprocess
        cmd = [
            "mcp", "launcher", "spawn_process",
            "--script-path", script_path,
            "--parent-pid", str(self.pid),
        ]

        if self.process_token:
            cmd.extend(["--parent-token", self.process_token.serialize()])

        if args:
            cmd.extend(["--args", json.dumps(args)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        response = json.loads(result.stdout)

        # Update our provenance entry with spawned child
        self._record_spawned_child(response["pid"])

        return response["pid"]

    def _record_spawned_child(self, child_pid: int) -> None:
        """Record spawned child in our provenance entry."""
        entries = self.crud.read(
            ProvenanceEntry,
            filters={"process_pid": self.pid},
            limit=1
        )

        if entries:
            entry = entries[0]
            if child_pid not in entry.spawned_children:
                entry.spawned_children.append(child_pid)
                self.crud.update(entry)

    def acquire_lock(self, lock_name: str, timeout: float = 30) -> bool:
        """Acquire a named lock for critical sections."""
        lock_file = self.locks_dir / f"{lock_name}.lock"
        start = time.time()

        while (time.time() - start) < timeout:
            try:
                fd = os.open(
                    lock_file,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                os.write(fd, str(self.pid).encode())
                os.close(fd)
                return True
            except FileExistsError:
                time.sleep(0.1)

        return False

    def release_lock(self, lock_name: str) -> None:
        """Release a named lock."""
        lock_file = self.locks_dir / f"{lock_name}.lock"
        lock_file.unlink(missing_ok=True)

    def wait_for_file(
        self,
        file_path: Path,
        timeout: float = 60
    ) -> bool:
        """Wait for a file to exist (synchronization primitive)."""
        start = time.time()

        while (time.time() - start) < timeout:
            if file_path.exists():
                return True
            time.sleep(0.5)

        return False

    def call_mcp(
        self,
        server: str,
        tool: str,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Call an MCP tool and return parsed result."""
        cmd = ["mcp", server, tool]

        # Add auth token if we have one
        if self.process_token:
            cmd.extend(["--auth-token", self.process_token.serialize()])

        # Add arguments
        for key, value in kwargs.items():
            cmd.append(f"--{key.replace('_', '-')}")
            if isinstance(value, (dict, list)):
                cmd.append(json.dumps(value))
            else:
                cmd.append(str(value))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return json.loads(result.stdout)

    def sign_validation(
        self,
        worker_pid: int,
        decision: str,
        rationale: str,
    ) -> ValidationSignature:
        """Cryptographically sign validation decision."""
        if not self.process_token:
            raise ValueError("Cannot sign without process token")

        timestamp = datetime.now(UTC)

        payload = {
            "moderator_pid": self.pid,
            "worker_pid": worker_pid,
            "decision": decision,
            "rationale": rationale,
            "timestamp": timestamp.isoformat(),
        }

        signature = hmac.new(
            self.process_token.signature.encode(),
            json.dumps(payload, sort_keys=True).encode(),
            hashlib.sha256
        ).hexdigest()

        validation = ValidationSignature(
            moderator_pid=self.pid,
            worker_pid=worker_pid,
            decision=decision,
            rationale=rationale,
            timestamp=timestamp,
            signature=signature,
            moderator_token_sig=self.process_token.signature,
        )

        # Update our provenance entry
        self._record_validation(worker_pid, decision, signature)

        return validation

    def _record_validation(
        self,
        worker_pid: int,
        decision: str,
        signature: str,
    ) -> None:
        """Record validation in our provenance entry."""
        entries = self.crud.read(
            ProvenanceEntry,
            filters={"process_pid": self.pid},
            limit=1
        )

        if entries:
            entry = entries[0]
            entry.validated_worker_pid = worker_pid
            entry.validation_decision = decision
            entry.validation_signature = signature
            self.crud.update(entry)

    def comment(
        self,
        message: str,
        context: dict[str, Any] | None = None
    ) -> None:
        """Leave a CMS comment in workspace for inter-process communication."""
        comment_file = (
            self.workspace_root /
            f".comment-{self.pid}-{int(time.time())}.md"
        )

        content = f"# Process {self.pid}\n\n{message}\n"
        if context:
            content += (
                f"\n## Context\n"
                f"```json\n{json.dumps(context, indent=2)}\n```\n"
            )

        comment_file.write_text(content)


def register_process(
    pid: int,
    parent_token: str | None,
    script_path: str,
) -> ProcessToken:
    """Register process with orchestrator, presenting parent's token.

    Called at start of worker/moderator script to "phone home".

    Args:
        pid: Our process ID
        parent_token: Parent's token (proves they authorized our spawn)
        script_path: Our script path

    Returns:
        Our new token (signed by orchestrator, chaining to parent)

    Raises:
        ValueError: If parent token invalid or we're not authorized
    """
    # In production, this would call orchestrator HTTP endpoint
    # For now, use local auth service

    # Load genesis secret from environment
    genesis_secret = os.environ.get("AMI_GENESIS_SECRET")
    if not genesis_secret:
        raise ValueError("AMI_GENESIS_SECRET not set")

    auth = AuthService(genesis_secret.encode())
    return auth.register_process(pid, script_path, parent_token)
```

## 8. Implementation Roadmap

### Phase 0: Foundation (Current)

- [ ] Document specification (this file)
- [ ] Create `learning/orchestrator.py` with provenance chain
- [ ] Extend launcher with hierarchy tracking (`nodes/backend/launcher/hierarchy.py`)
- [ ] Add launcher MCP tools for process spawning and tree operations
- [ ] Write unit tests for hierarchy tracking and provenance chain

### Phase 1: First Workers & Moderators

- [ ] Implement `worker-research.sh` (simple bash version with phone-home)
- [ ] Implement `moderator-quality.sh` (basic validation with signing)
- [ ] Integrate with Browser MCP and Research MCP
- [ ] Test end-to-end: User → worker-research → moderator-quality → termination
- [ ] Verify provenance chain integrity

### Phase 2: Advanced Workers

- [ ] Implement `worker-analyze.sh`, `worker-synthesize.sh`
- [ ] Add Python-based workers using `orchestrator.py` helper
- [ ] Implement multi-stage workflows (research → analyze → synthesize → final moderation)
- [ ] Add CMS comment-based inter-process communication
- [ ] Resource limit enforcement (max depth, max children, timeouts)

### Phase 3: Moderator Logic

- [ ] Implement schema-based validation in moderators
- [ ] Add corrective worker spawning on validation failure
- [ ] Implement approval/rejection audit trail
- [ ] Multi-moderator consensus (require N moderators to approve)
- [ ] Integration with Research MCP audit system

### Phase 4: BPMN Integration

- [ ] Build Planning MCP server on BPMN models
- [ ] Implement BPMN adapter to spawn workers from tasks
- [ ] Add compensation task support (rollback on moderator rejection)
- [ ] GitHub Projects integration for high-level PM
- [ ] End-to-end test: BPMN process → worker tree → completion

### Phase 5: Provenance & Evolution

- [ ] Implement provenance chain viewer (CLI tool)
- [ ] Workers can propose new worker scripts
- [ ] Meta-moderators validate proposed workers
- [ ] HSM integration for production signing
- [ ] Self-improvement cycle: analyze outcomes, propose better workers, validate, deploy

## 9. Security & Safety Constraints

### 9.1 Process Isolation

- Workers/moderators run with no special privileges
- Cannot access files outside research workspace (enforced by MCP servers)
- Cannot spawn arbitrary processes (must use launcher MCP spawn primitive)
- Cannot modify launcher state directly (only via MCP tools)

### 9.2 Resource Limits

**Implementation via Launcher Extensions**:

```python
@dataclass
class HierarchyLimits:
    max_depth: int = 10
    max_children_per_node: int = 5
    max_total_processes: int = 50
    process_timeout_seconds: int = 300


class LimitEnforcer:
    """Enforce resource limits on process hierarchies."""

    def check_spawn(
        self,
        parent_pid: int,
        hierarchy: HierarchyTracker,
        limits: HierarchyLimits,
    ) -> None:
        """Raise exception if spawn would violate limits."""
        # Implementation in hierarchy.py
```

### 9.3 Validation & Audit

- All worker outputs validated by moderators before acceptance
- Moderators append audit entries with validation results
- Failed validations logged with error details
- Provenance chain allows tracing bad outputs to source worker
- Cryptographic signatures prevent tampering

## 10. Alignment with Existing Frameworks

### 10.1 Bootstrap Provenance Integration

Alignment with `bootstrap.md` and `incremental.md` frameworks:

**Layer 0: Genesis Kernel**

- Implemented as: Immutable worker/moderator contract + cryptographic root
- Enforces: Safety constraints (no direct filesystem writes outside research dir)
- Verification: Moderators check worker outputs against schemas and rules

**Layer 1: Bootstrap Verifier**

- Implemented as: Moderator scripts that validate worker outputs
- Signing: Moderators append audit entries with cryptographic signatures
- Cannot modify: Layer 0 contracts (script interfaces are immutable)

**Layer 2+: Evolving Reasoning**

- Workers can propose new worker/moderator scripts
- New scripts must be validated by existing moderators
- Audit trail in Research MCP tracks provenance

**Provenance Chain Example**:

```
Research Task: "Analyze AI agent market"
├─ worker-research.sh (Layer 0, validated by genesis)
│   └─ Audit: "Spawned by user, token sig_ABC...123"
├─ moderator-quality.sh (Layer 0, validated by genesis)
│   └─ Audit: "Validated worker PID 1001, approved, sig_DEF...456"
├─ worker-analyze.sh (Layer 2, spawned by worker-research)
│   └─ Audit: "Spawned by PID 1001, token sig_GHI...789 [parent: sig_ABC...123]"
└─ worker-synthesize-v2.sh (Layer 2+, proposed by worker-analyze)
    └─ Audit: "Proposed by PID 1003, verified by moderator-meta, sig_JKL...012"
```

### 10.2 Extension of SPEC-LEARNING

The Self-Moderating Reasoner complements SPEC-LEARNING:

- **Dataset creation** → Research workers collecting and validating data
- **Experiment orchestration** → Worker scripts running training loops
- **Model registry** → Moderators approving model checkpoints
- **Monitoring & drift** → Workers detecting anomalies, spawning corrective actions

## 11. Open Questions & Future Work

### 11.1 Research Questions

1. Optimal moderator granularity: Single moderator per worker, or shared moderators?
2. Consensus mechanisms: How many independent moderators needed?
3. Worker specialization: Generic vs. specialized workers?
4. Failure recovery: Moderator escalation vs. automatic retry?
5. Resource optimization: Detect and prevent redundant spawns?

### 11.2 Technical Challenges

1. Process cleanup: Orphaned processes when parent crashes
2. Deadlock detection: Workers waiting on each other's outputs
3. Concurrent workspace access: Multiple workers writing simultaneously
4. State consistency: Filesystem sync vs. distributed coordination
5. Observability: Real-time process tree visualization

### 11.3 Evolution Paths

1. **Worker Evolution**: Workers proposing new scripts (bootstrapping)
2. **Moderator Evolution**: Meta-moderators validating moderator improvements
3. **Planning Evolution**: BPMN definitions generated by workers
4. **Cross-Domain Reasoning**: Workers from different domains collaborating
5. **Human-in-the-Loop**: Strategic escalation for human guidance

## 12. References

- Launcher Implementation: `nodes/backend/launcher/supervisor.py`, `nodes/backend/launcher/models.py`
- Browser MCP: `browser/backend/mcp/chrome/chrome_server.py`
- Research MCP Spec: `domains/marketing/backend/mcp/research/SPEC-RESEARCH.md`
- CMS Communication: `ux/cms/docs/spec.md`
- BPMN Models: `base/backend/dataops/models/bpmn.py`
- Bootstrap Framework: `learning/bootstrap.md`, `learning/incremental.md`
- Learning Module Spec: `learning/SPEC-LEARNING.md`
- LocalProcessAdapter (stdout/stderr redirection): `nodes/backend/launcher/adapters/local.py:72-80`

---

**Document Status**: Specification v1.0
**Date**: 2025-10-05
**Author**: System design based on AMI-ORCHESTRATOR codebase analysis
**Dependencies**: `/nodes/launcher`, `/browser`, `/marketing/research`, `/ux/cms`, `/base/dataops`
