# AMI-ORCHESTRATOR

A compliance-aware automation framework with multi-storage architecture, document processing, and AI agent integration.

## What This Is

This is a research and development project exploring how to build automation systems that can be audited, traced, and verified against compliance requirements. The core idea: instead of bolting compliance onto AI systems after the fact, build it into the architecture from the ground up.

## What It Does

- **Multi-storage data layer** – Dgraph for ACLs and relationships, PostgreSQL for structured data, vector stores for embeddings, Redis for caching
- **Document processing** – Extract and index PDFs, Word docs, images with AI-powered analysis
- **Browser automation** – Auditable web automation with anti-detection and session management
- **MCP integration** – Standard protocol for AI agents to interact with the system
- **Compliance documentation** – EU AI Act and ISO reference materials, gap tracking

## What It's Not

This isn't a finished product. The infrastructure works—storage, processing, automation—but the ambitious parts (self-evolving AI with formal safety proofs) are still in development.

The OpenAMI documentation describes where this is headed: AI systems that improve themselves through verified steps with guarantees they won't violate constraints. What's here is the infrastructure layer.

## Current State

**Production-ready foundation:**
- Multi-storage DataOps (Dgraph, PostgreSQL, Redis, in-memory) with unified CRUD
- MCP servers for AI agent integration (DataOps, SSH, browser automation)
- Document extraction and indexing (PDF, DOCX, images with Gemini analysis)
- Browser automation with anti-detection and profile management
- Infrastructure orchestration and service management
- Comprehensive test coverage (24 test files in base alone)

**Research complete, implementation in progress:**
- Compliance framework (EU AI Act, ISO standards documented and mapped)
- NextAuth integration for authentication
- Secure process abstractions (SPN/CST formalization)

**Research phase (Open AMI vision):**
- Self-evolution with formal verification
- Cryptographic provenance chain
- Distributed verification protocol
- AAL/AADL compilers for AI architecture modification

The foundation is solid and tested. The ambitious parts—self-evolving AI with mathematical safety guarantees—are moving from research to implementation.

## Getting Started

```bash
# Clone with submodules
git clone --recursive <repo-url>
cd AMI-ORCHESTRATOR

# Bootstrap toolchain
python scripts/bootstrap_uv_python.py --auto

# Run setup
python module_setup.py

# Run module tests
uv run --python 3.12 --project base python scripts/run_tests.py
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design and [docs/](docs/) for detailed documentation.

## Philosophy

Real compliance and auditability require architectural choices, not add-ons:
- Explicit over implicit (no magic defaults)
- Traceable over convenient (audit everything)
- Verifiable over trusted (prove, don't promise)
