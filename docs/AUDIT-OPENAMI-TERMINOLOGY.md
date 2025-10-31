# OpenAMI Documentation Terminology Audit

**Generated**: 2025-10-31
**Scope**: All docs/openami/ documentation
**Finding**: Excessive made-up terminology obscuring the CORE MISSION: **ACCOUNTABILITY AND RESPONSIBILITY**

---

## CRITICAL: Mission Misalignment

### What the Documentation SHOULD Focus On

**ACCOUNTABILITY AND RESPONSIBILITY**

Every AI behavior and effect must be:
1. **Traceable** to individual development steps, training steps, snapshots, algorithms, and data
2. **Auditable** by both automated systems and human auditors
3. **Attributable** to specific responsible parties (developers, trainers, operators)
4. **Verifiable** through complete provenance chains
5. **Reversible** via versioned snapshots

### What the Documentation ACTUALLY Does

Drowns this mission in made-up terminology, theoretical constructs, and marketing speak that obscures practical accountability mechanisms.

---

## Bullshit Terminology Inventory (23 violations)

### Tier 1: Made-Up Proper Nouns (WORST)

**1. "Gemini DSE-AI" (Deterministic Self-Evolution)**
- **Locations**: README.md:47, GUIDE-FRAMEWORK.md:175-180,194,318, SPEC-ARCHITECTURE.md:249,318,499
- **Issue**: Made-up name for a research approach that adds NO clarity
- **Replace with**: "Deterministic evolution approach" or just describe the mechanism
- **Why it's bullshit**: Creates false impression this is an established framework

**2. "Claude Formal Bootstrap"**
- **Locations**: README.md:48, GUIDE-FRAMEWORK.md:176-177,199,403, SPEC-ARCHITECTURE.md:318,500
- **Issue**: Made-up name for another research approach
- **Replace with**: "Formal verification approach" or describe the verification method
- **Why it's bullshit**: Same as above - sounds official but isn't

**3. "Layer 0 Axioms"**
- **Locations**: Throughout all files (58+ instances)
- **Issue**: Pretentious name for "immutable safety constraints"
- **Replace with**: "Immutable safety constraints" or "foundational safety rules"
- **Why it's bullshit**: "Layer 0" and "Axioms" are both borrowed from formal systems to sound smart; constraints is clearer

**4. "AADL" (AI Architecture Description Language)**
- **Locations**: GUIDE-FRAMEWORK.md:423, SPEC-VISION.md:194
- **Issue**: Made-up programming language that doesn't exist
- **Replace with**: Remove or say "high-level transformation specification"
- **Why it's bullshit**: No implementation, no spec, just a name

**5. "AAL" (AI Assembly Language)**
- **Locations**: GUIDE-FRAMEWORK.md:424, SPEC-VISION.md:194
- **Issue**: Another made-up language
- **Replace with**: Remove or say "low-level operations"
- **Why it's bullshit**: Same as above

**6. "Meta-Compiler"**
- **Locations**: GUIDE-FRAMEWORK.md:425, SPEC-VISION.md:194
- **Issue**: Theoretical construct without implementation or spec
- **Replace with**: "Transformation pipeline" or just remove
- **Why it's bullshit**: No implementation, adds confusion not clarity

**7. "OAMI Protocol"**
- **Locations**: Throughout all files (15+ instances)
- **Issue**: Made-up protocol name when it's just MCP with extensions
- **Replace with**: "Inter-component communication protocol" or "MCP-based protocol"
- **Why it's bullshit**: Creates impression of novel protocol when it's MCP + some extensions

**8. "SDS" (Secure Distributed System)**
- **Locations**: GUIDE-FRAMEWORK.md:215,248, SPEC-ARCHITECTURE.md:83,153-178
- **Issue**: Generic term made to sound like a specific technology
- **Replace with**: "Distributed execution infrastructure" or just describe it
- **Why it's bullshit**: Every distributed system claims to be "secure"; this is marketing

### Tier 2: Made-Up Acronyms/Concepts

**9. "SPNs" (Secure Process Nodes)**
- **Locations**: Throughout all files (40+ instances)
- **Issue**: Made-up abstraction for what are just "isolated execution environments"
- **Replace with**: "Isolated execution environments" or "sandboxed processes"
- **Why it's bullshit**: Unnecessarily obscure when "containers with attestation" is clearer

**10. "CSTs" (Cryptographic State Tokens)**
- **Locations**: Throughout all files (30+ instances)
- **Issue**: Made-up concept for "signed state snapshots"
- **Replace with**: "Cryptographically signed state snapshots"
- **Why it's bullshit**: Acronym obscures what it actually is

**11. "Compliance Manifest"**
- **Locations**: Throughout all files (25+ instances)
- **Issue**: Could just be "compliance requirements specification"
- **Replace with**: "Compliance requirements" or "regulatory requirements specification"
- **Why it's bullshit**: "Manifest" makes it sound special when it's just a requirements document

**12. "Evolution Engine"**
- **Locations**: GUIDE-FRAMEWORK.md:245, SPEC-ARCHITECTURE.md:77,244-263
- **Issue**: Pretentious name for "self-modification system"
- **Replace with**: "Self-modification system" or "automated improvement system"
- **Why it's bullshit**: "Engine" is overused marketing term

**13. "Proof Generators"**
- **Locations**: GUIDE-FRAMEWORK.md:242, SPEC-ARCHITECTURE.md:78,264-272
- **Issue**: Could be "formal verification tools"
- **Replace with**: "Formal verification tools" or "theorem provers"
- **Why it's bullshit**: "Generators" implies they magically create proofs; they don't

**14. "Justification Triad"**
- **Locations**: Previous docs (may be cleaned up)
- **Issue**: Made-up concept for "explanation + proof + test results"
- **Replace with**: Just list the three components
- **Why it's bullshit**: "Triad" is pretentious; just say "three-part justification"

### Tier 3: Marketing Speak

**15. "Four Pillars"**
- **Locations**: Throughout all files (20+ instances)
- **Issue**: Marketing framework name
- **Replace with**: "Four design principles: Compliance, Integrity, Abstraction, Dynamics"
- **Why it's bullshit**: "Pillars" is corporate consulting speak

**16. "Genesis Kernel"**
- **Locations**: May have been cleaned up already
- **Issue**: Marketing term for "initial version"
- **Replace with**: "Initial implementation" or "v1.0"
- **Why it's bullshit**: Biblical reference adds no clarity

**17. "Never-Jettison Guarantee"**
- **Locations**: Should be cleaned up to "constraint preservation"
- **Issue**: Marketing speak
- **Replace with**: "Constraint preservation" or "monotonic safety properties"
- **Why it's bullshit**: Already fixed in recent cleanup

### Tier 4: Unnecessarily Obscure

**18. "Verifiable Reasoning Steps"**
- **Locations**: GUIDE-FRAMEWORK.md:243, SPEC-ARCHITECTURE.md:79
- **Issue**: Could be "audit trail of decisions"
- **Replace with**: "Audit trail of AI decisions" or "decision log"
- **Why it's bullshit**: "Verifiable reasoning steps" sounds academic; "decision audit trail" is clearer

**19. "Coordination Processes"**
- **Locations**: GUIDE-FRAMEWORK.md:276-280, SPEC-ARCHITECTURE.md:199-211
- **Issue**: Could be "workflow orchestration"
- **Replace with**: "Workflow orchestration" or "process coordination"
- **Why it's bullshit**: Not inherently bad but could be clearer

**20. "Process Theory"**
- **Locations**: GUIDE-FRAMEWORK.md:261, SPEC-ARCHITECTURE.md:94,141-149
- **Issue**: Sounds academic for "formal models of AI behavior"
- **Replace with**: "Formal behavioral models" or "AI behavior specifications"
- **Why it's bullshit**: "Theory" makes it sound more abstract than it is

**21. "Constraint Preservation (Monotonic Safety Properties)"**
- **Locations**: Throughout (this replaced "Never-Jettison")
- **Issue**: Technical but potentially still obscure
- **Keep but clarify**: Add plain language: "safety rules that can never be weakened"
- **Why it's marginal**: Actually correct terminology but needs plain language explanation

**22. "Distributed Verification (BFT Consensus)"**
- **Locations**: Throughout all files (15+ instances)
- **Issue**: Technically correct but overcomplicated
- **Simplify**: "Multi-party verification with Byzantine fault tolerance"
- **Why it's marginal**: Correct but could explain better

**23. "Cryptographic Provenance Chain"**
- **Locations**: GUIDE-FRAMEWORK.md:408, SPEC-ARCHITECTURE.md:481
- **Issue**: Technically correct but could be clearer
- **Simplify**: "Tamper-evident history of all changes"
- **Why it's marginal**: Correct but benefits from plain language

---

## The REAL Mission: ACCOUNTABILITY and RESPONSIBILITY

### What Should Be Front and Center

Every file should start by emphasizing:

```markdown
## Core Mission: Complete Accountability

Open AMI ensures every AI behavior and effect is:

1. **Traceable to Source**
   - Development step that introduced the behavior
   - Training data that influenced the decision
   - Algorithm or model architecture responsible
   - Specific code version and configuration
   - Human developer/operator accountable

2. **Auditable by Humans and Systems**
   - Automated compliance checks before deployment
   - Human oversight and approval gates
   - Forensic analysis capabilities
   - Real-time monitoring and alerts
   - Post-incident investigation tools

3. **Provably Correct**
   - Cryptographically signed snapshots
   - Immutable audit logs
   - Formal verification where feasible
   - Empirical testing results
   - Complete version history

4. **Reversible and Recoverable**
   - Rollback to any previous state
   - Snapshot-based recovery
   - State reconstruction from audit trail
   - Impact analysis for changes

5. **Compliant by Design**
   - EU AI Act requirements built-in
   - ISO 42001 alignment
   - NIST AI RMF adherence
   - Sector-specific regulations (FDA, financial, etc.)
```

### What's Currently Obscured

The documentation talks about:
- "Layer 0 Axioms" instead of **WHO defined the safety rules and WHEN**
- "Evolution Engine" instead of **WHAT code changed, WHO approved it, WHICH tests validated it**
- "Proof Generators" instead of **HOW we know it's safe and WHO verified the proof**
- "SPNs" instead of **WHICH process did what and WHO can audit it**
- "CSTs" instead of **WHAT state was captured, WHEN, and WHO can verify it**

### The Fix: Refocus on Actors and Actions

Every concept should answer:
- **WHO** is responsible? (developer, operator, auditor, system)
- **WHAT** happened? (specific action, change, decision)
- **WHEN** did it happen? (timestamp, version, snapshot)
- **WHERE** is it recorded? (which log, which database, which file)
- **HOW** can it be verified? (automated check, human review, formal proof)
- **WHY** did it happen? (justification, trigger, requirement)

---

## Proposed Terminology Replacements

### Replace Made-Up Names

| Current Bullshit | Replace With | Rationale |
|-----------------|--------------|-----------|
| Gemini DSE-AI | Deterministic evolution approach | Descriptive, not a brand name |
| Claude Formal Bootstrap | Formal verification approach | Descriptive, not a brand name |
| Layer 0 Axioms | Immutable safety constraints | Plain language, clearer intent |
| AADL/AAL/Meta-Compiler | High-level and low-level transformations | Describe what they do, not made-up names |
| OAMI Protocol | Inter-component communication protocol | Accurate description |
| SDS | Distributed execution infrastructure | Generic term, not a brand |

### Replace Obscure Acronyms

| Current Bullshit | Replace With | Rationale |
|-----------------|--------------|-----------|
| SPNs (Secure Process Nodes) | Isolated execution environments | What they actually are |
| CSTs (Cryptographic State Tokens) | Signed state snapshots | What they actually are |
| BFT Consensus | Multi-party verification | More accessible |

### Simplify Concepts

| Current Bullshit | Replace With | Rationale |
|-----------------|--------------|-----------|
| Compliance Manifest | Compliance requirements specification | Clearer purpose |
| Evolution Engine | Self-modification system | Descriptive |
| Proof Generators | Formal verification tools | Accurate |
| Verifiable Reasoning Steps | Decision audit trail | Plain language |
| Four Pillars | Four design principles | Less marketing |

### Add Actor-Focused Language

Every description should include:
- **Auditor view**: "Human auditors can review all decisions via..."
- **Developer accountability**: "Developers are accountable for changes through..."
- **Operator responsibility**: "Operators approve deployments by verifying..."
- **System traceability**: "The system traces every action to..."

---

## File-by-File Violations

### docs/openami/README.md (15 violations)

- Line 14: "Four Pillars" → "Four design principles"
- Line 14: Links to non-existent submodule paths (CRITICAL - see FIX-BROKEN-DOC-LINKS.md)
- Line 15: Links to submodule (CRITICAL)
- Line 27: "Secure Process Nodes (SPN)" → "Isolated execution environments"
- Line 28: "Cryptographic State Tokens (CST)" → "Signed state snapshots"
- Line 46: "SYNTHESIS-OPENAMI-BOOTSTRAP.md" - submodule link (CRITICAL)
- Line 47: "Gemini DSE-AI (deterministic self-evolution)" → Just "deterministic evolution approach"
- Line 48: "Claude formal verification approach" → "formal verification approach"
- Line 52-55: All submodule links (CRITICAL)
- Line 54: "OAMI protocol" → "inter-component communication protocol"

### docs/openami/SPEC-VISION.md (18 violations)

- Line 36-43: "Four Pillars" → "Four design principles"
- Line 188: "Layer 0 Axioms (Lean/Coq)" → "Immutable safety constraints"
- Line 194: "Meta-Compiler (AADL → AAL)" → "Transformation pipeline"
- Line 266: "Layer 0 Axioms formalized" → "Immutable safety constraints formalized"
- Line 267: "SPN abstraction operational" → "Isolated execution environment abstraction"
- Line 297: Broken link to what-is-openami.md (BROKEN - see FIX-BROKEN-DOC-LINKS.md)
- Line 354: Submodule link (CRITICAL)
- Uses checkboxes (✅/🎯) inconsistently - should clearly separate IMPLEMENTED from TARGET

### docs/openami/GUIDE-FRAMEWORK.md (45+ violations)

- Line 81-108: "Four Pillars" section - use "Four design principles"
- Line 116: "Layer 0: Axioms" → "Immutable Safety Constraints"
- Line 158: "Layer 0 Axioms (immutable, human-specified safety constraints)" - redundant, pick one term
- Line 175: "Gemini DSE-AI" → "Deterministic evolution approach"
- Line 176: "Claude Formal Bootstrap" → "Formal verification approach"
- Line 177: Submodule link (CRITICAL)
- Line 180-218: References to "Gemini DSE-AI approach" and "Claude Formal Bootstrap approach" throughout
- Line 194: "AADL → AAL" made-up languages
- Line 227: Broken link to ../architecture/system-architecture.md (BROKEN)
- Line 232: "$\mathcal{CM}$" - unnecessary math notation for "Compliance Manifest"
- Line 242: "Proof generators" → "Formal verification tools"
- Line 243: "Verifiable reasoning steps" → "Decision audit trail"
- Line 249: "SPNs (Secure Process Nodes)" → "Isolated execution environments"
- Line 269: "SPNs" acronym usage
- Line 274: Submodule link (CRITICAL)
- Line 282: "Compliance Manifest" → "Compliance requirements specification"
- Line 284: "Layer 0 axioms" → "immutable safety constraints"
- Line 287: Submodule link (CRITICAL)
- Line 289: "CSTs" → "signed state snapshots"
- Line 300: Submodule link (CRITICAL)
- Line 395-401: Lean code example - theoretical only
- Line 403: Submodule link (CRITICAL)
- Line 407: "CSTs" → "signed state snapshots"
- Line 408: "Provenance Chain" - could simplify
- Line 415: "SPNs" → "isolated execution environments"
- Line 417: "OAMI Protocol" → "Inter-component communication protocol"
- Line 423-426: "AADL/AAL/Meta-Compiler" - all made-up
- Line 435: Broken link to ./executive-summary.md (BROKEN)
- Line 445: Broken link (BROKEN)
- Line 446-448: Multiple submodule links (CRITICAL)
- Line 461-472: Multiple submodule links (CRITICAL)
- Line 509-511: Broken links and submodule links
- Line 542: Submodule link (CRITICAL)

### docs/openami/SPEC-ARCHITECTURE.md (50+ violations)

- Line 17-24: "Four Pillars" → "Four design principles"
- Line 32-51: "Four Pillars" section
- Line 92: "Layer 0 Axioms" → "Immutable safety constraints"
- Line 109-125: "Layer 0 Axioms" section - excessive use
- Line 125: Submodule link (CRITICAL)
- Line 149: Submodule link (CRITICAL)
- Line 158: "SDS" → "Distributed execution infrastructure"
- Line 168-171: "SPNs" diagram - use full term
- Line 182-197: "Secure Process Nodes (SPNs)" section - use "Isolated execution environments"
- Line 197: Submodule link (CRITICAL)
- Line 199-211: "Coordination Processes" - could be clearer
- Line 213-225: "Cryptographic State Tokens (CSTs)" - use "Signed state snapshots"
- Line 244-263: "Evolution Engine" section
- Line 249: Submodule link (CRITICAL)
- Line 258: "Gemini DSE-AI"
- Line 264-272: "Proof Generators/Verifiers"
- Line 284-299: "Compliance Manifest" section
- Line 292: "Layer 0 Axioms"
- Line 299: Submodule link (CRITICAL)
- Line 318: "Gemini DSE-AI" and "Claude"
- Line 337: "Layer 0 Axioms"
- Line 404: Submodule link (CRITICAL)
- Line 470: "Layer 0 Axioms in Lean/Coq"
- Line 472: "SPNs (Secure Process Nodes)"
- Line 474: "CSTs (Cryptographic State Tokens)"
- Line 476: "Evolution Engine (high-level → low-level transformation)"
- Line 479: "OAMI Protocol"
- Line 494-522: Multiple submodule links (CRITICAL)

---

## Recommended Actions

### Phase 1: Fix Broken Links (CRITICAL - Do First)
- Replace all submodule relative paths with GitHub URLs
- Fix all renamed file references
- See FIX-BROKEN-DOC-LINKS.md for complete list

### Phase 2: Eliminate Bullshit Terminology
1. Global search/replace for all Tier 1 violations (made-up proper nouns)
2. Replace all Tier 2 violations (made-up acronyms) with full descriptive terms
3. De-marketize Tier 3 violations
4. Clarify Tier 4 violations with plain language

### Phase 3: Refocus on Accountability
1. Add "Core Mission: Complete Accountability" section to every file
2. Replace theoretical discussions with practical accountability mechanisms
3. Emphasize WHO, WHAT, WHEN, WHERE, HOW, WHY for every concept
4. Add auditor/developer/operator perspectives to every major feature

### Phase 4: Restructure Content
1. Lead with CURRENT production capabilities (audit trail, MCP servers)
2. Separate THEORETICAL from IMPLEMENTED clearly
3. Replace made-up frameworks ("Gemini DSE-AI") with implementation descriptions
4. Focus on TRACEABILITY, AUDITABILITY, ACCOUNTABILITY in every section

---

## Success Criteria

Documentation is FIXED when:

1. ✅ ZERO made-up proper nouns (Gemini DSE-AI, Claude Formal Bootstrap, etc.)
2. ✅ ZERO unnecessary acronyms (replace SPNs/CSTs with descriptive terms on first use)
3. ✅ ZERO broken links (all submodule paths → GitHub URLs, all renamed files fixed)
4. ✅ EVERY major concept answers: WHO is accountable, WHAT is tracked, HOW is it audited
5. ✅ CLEAR separation between IMPLEMENTED (audit_trail.py) and THEORETICAL (self-evolution)
6. ✅ EMPHASIS on human auditors, automated auditors, developers, operators as primary actors
7. ✅ FOCUS on traceability to specific data, code, snapshots, training steps

---

**End of Audit**
