# Self-Moderating Reasoner Security Model

## Hierarchical Key Derivation with Infalsifiable Tokens

### Core Principle

**Child processes self-generate cryptographically infalsifiable tokens** using hierarchically derived keypairs. The orchestrator validates but cannot forge tokens.

### Security Flow

```
Genesis Keypair (HSM-protected)
    ↓
Root Process derives keys for Child 1
    ↓
Child 1 self-generates token (infalsifiable)
    ↓
Child 1 phones home (orchestrator validates, cannot forge)
    ↓
Child 1 derives keys for Child 2
    ↓
...continues...
```

### Mathematical Properties

1. **Infalsifiable**: Only holder of parent's private key can derive child's keypair
2. **Hierarchical**: Child's public key mathematically related to parent's
3. **Self-Certifying**: Each process proves identity via self-signed token
4. **Offline Verifiable**: Anyone with genesis public key can verify entire chain
5. **Non-Repudiable**: Cryptographic proof of who spawned whom

### Token Structure

```python
class ProcessToken:
    pid: int                        # Process ID
    public_key: bytes              # This process's pubkey (derived from parent)
    parent_public_key: bytes | None  # Parent's pubkey (for chain verification)
    script_path: str               # What script this process runs
    issued_at: datetime            # When token generated
    signature: bytes               # Self-signed with derived private key
```

### Key Derivation (HKDF-based)

```python
def derive_child_keypair(
    parent_private_key: ed25519.Ed25519PrivateKey,
    child_pid: int,
) -> tuple[ed25519.Ed25519PrivateKey, bytes]:
    """Derive child keypair from parent's private key + child PID.

    Uses HKDF (HMAC-based Key Derivation Function):
    - Input: Parent private key bytes
    - Info: "child_pid_{pid}" (context binding)
    - Output: 32 bytes (Ed25519 key material)

    Result: Deterministic, infalsifiable child keypair
    """
    parent_key_bytes = parent_private_key.private_bytes(...)

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=f"child_pid_{child_pid}".encode()
    )

    child_key_bytes = hkdf.derive(parent_key_bytes)
    child_private_key = ed25519.Ed25519PrivateKey.from_private_bytes(child_key_bytes)

    return child_private_key, child_public_key
```

### Spawn Sequence

**Parent spawning child:**

1. Parent calls launcher: `spawn_process(script_path, args)` → get child PID
2. Parent derives child's keypair: `derive_child_keypair(my_privkey, child_pid)`
3. Parent passes to child via environment:
   - `PARENT_TOKEN`: Parent's token (contains parent's pubkey)
   - `CHILD_PRIVATE_KEY`: Child's derived private key
   - `CHILD_PUBLIC_KEY`: Child's derived public key

**Child self-generates token:**

1. Child loads keys from environment
2. Child creates signing payload:
   ```python
   payload = {
       "pid": my_pid,
       "public_key": my_pubkey,
       "parent_public_key": parent_pubkey,
       "script_path": my_script,
       "issued_at": now()
   }
   ```
3. Child signs with private key: `signature = sign(privkey, payload)`
4. Child constructs token with signature

**Child phones home:**

1. Child sends to orchestrator:
   - Own self-generated token
   - Parent's token
2. Orchestrator validates:
   - Child token signature valid (proves child has derived privkey)
   - Parent token's pubkey matches child's parent_public_key field
   - Parent token's chain validates back to genesis
   - Authorization policy allows spawn (e.g., workers can spawn moderators)
3. If valid, orchestrator registers (but doesn't issue new token)

### Verification Chain

```python
def verify_lineage(
    token: ProcessToken,
    parent_token: ProcessToken | None,
    genesis_public_key: bytes,
) -> bool:
    # 1. Verify self-signature
    if not verify_signature(token.public_key, token.signature, payload):
        return False

    # 2. If root, verify against genesis
    if token.parent_public_key is None:
        return token.public_key == genesis_public_key

    # 3. Verify parent exists and matches
    if parent_token is None or parent_token.public_key != token.parent_public_key:
        return False

    # 4. Recursively verify parent
    return verify_lineage(parent_token, None, genesis_public_key)
```

### Security Guarantees

✅ **Cannot forge tokens**: Need parent's private key to derive child keypair
✅ **Cannot impersonate**: Only holder of derived privkey can sign valid token
✅ **Cannot break chain**: All tokens cryptographically linked to genesis
✅ **Cannot bypass orchestrator**: Policy validation required for registration
✅ **Cannot hide lineage**: Every token contains parent's pubkey
✅ **Cannot tamper**: Any modification breaks signature

### Attack Resistance

| Attack | Defense |
|--------|---------|
| Forge child token | Need parent's private key (infeasible to obtain) |
| Spawn unauthorized child | Orchestrator rejects via policy enforcement |
| Break into process tree | Each process isolated, keys passed via env (cleared after use) |
| Replay old token | Timestamp + nonce in signed payload |
| Man-in-the-middle | TLS for orchestrator comms, tokens self-verifying |
| Compromised orchestrator | Can't forge tokens (no private keys), can only reject valid ones |
| Compromised parent | Can derive children, but children's work validated by moderators |
| Stolen genesis key | HSM-protected, never exposed to processes |

### Key Management

1. **Genesis Keypair**:
   - Generated once, private key in HSM
   - Public key burned into code
   - Never exposed to processes

2. **Process Private Keys**:
   - Derived on-demand by parent
   - Passed to child via environment
   - Child clears from env after token generation
   - Never persisted to disk

3. **Token Distribution**:
   - Tokens contain only public keys
   - Tokens can be logged/stored safely
   - Private keys exist only in process memory

### Revocation

Orchestrator maintains **blacklist of revoked public keys**:

```python
revoked_keys: set[bytes] = {...}

def validate_registration(child_token, parent_token):
    # Check blacklist
    if child_token.public_key in revoked_keys:
        raise ValueError("Child token revoked")

    if parent_token and parent_token.public_key in revoked_keys:
        raise ValueError("Parent token revoked")

    # ... rest of validation
```

Revocation scenarios:
- Compromised process detected → revoke its pubkey → all descendants invalidated
- Malicious worker → revoke → cannot spawn more children
- Policy violation → revoke → existing token becomes invalid

### Comparison: Orchestrator-Issued vs. Self-Generated

| Property | Orchestrator-Issued | Self-Generated (This Design) |
|----------|---------------------|------------------------------|
| Forgery resistance | Depends on orchestrator security | Cryptographically impossible |
| Offline verification | No (need orchestrator) | Yes (anyone with genesis pubkey) |
| Orchestrator compromise | Can forge tokens | Cannot forge tokens |
| Policy enforcement | Yes | Yes (via registration validation) |
| Revocation | Yes | Yes (via blacklist) |
| Key distribution | Centralized | Hierarchical |
| Trust model | Trust orchestrator | Trust cryptography + policy |

### Conclusion

**Self-generated tokens with hierarchical key derivation provide:**

1. **Maximum security**: Cryptographically infalsifiable
2. **Decentralized trust**: Don't need to trust orchestrator for token integrity
3. **Policy enforcement**: Orchestrator still validates authorization
4. **Auditability**: Full cryptographic proof of lineage
5. **Flexibility**: Can verify offline, add revocation, enforce policies

This is **more secure** than orchestrator-issued tokens because even a compromised orchestrator cannot forge valid tokens—it can only reject them via policy.
