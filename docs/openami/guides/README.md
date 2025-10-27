# Open AMI Guides

Conceptual guides for the OpenAMI theoretical framework.

> **⚠️ STATUS**: OpenAMI is a research framework (Q4 2025 - Q2 2026 target). For **production infrastructure**, see [AMI-ORCHESTRATOR README](../../../README.md).

---

## Quick Navigation

**New to OpenAMI?** → Start with [What is OpenAMI?](../overview/what-is-openami.md) (conceptual overview)

**Need production docs?** → See [AMI-ORCHESTRATOR README](../../../README.md)

**Understanding the vision?** → Read [What is OpenAMI?](../overview/what-is-openami.md)

---

## Available Guides

**Currently Available:**
- [**Quick Start (ARCHIVED)**](../../archive/quickstart-openami-aspirational.md) - Aspirational guide describing features not yet implemented (preserved for reference)

**Future Research Guides** (Q4 2025 - Q2 2026):

These guides will be created as OpenAMI components are implemented:

- **Four Pillars Architecture**: Compliance, Integrity, Abstraction, Dynamics layers
- **Secure Process Nodes (SPNs)**: Auditable computation abstraction
- **Cryptographic State Tokens (CSTs)**: Provenance and audit trails
- **Formal Verification**: Safety proof generation with Lean/Coq
- **Self-Evolution Protocol**: AAL/AADL compilers and safe evolution
- **Compliance Manifest**: Governance and standards mapping

For current architecture specifications, see [research docs](../../../compliance/docs/research/OpenAMI/).

---

## Production Documentation

**For working infrastructure** (available now), see:

**Developers**
- [AMI-ORCHESTRATOR README](../../../README.md) - Setup, installation, capabilities
- [MCP Servers](../../../README.md#mcp-integration) - DataOps, SSH, Browser, Files tools
- [ami-agent CLI](../../../README.md#ami-agent-reliable-auditable-verifiable-automation) - Automation workflows

**Architects**
- [System Architecture](../architecture/system-architecture.md) - Four-layer design (aspirational)
- [Compliance Research](../../../compliance/docs/research/OpenAMI/) - Standards mapping
- [Reading Map](../../GUIDE-READING-MAP.md) - Documentation navigation

**DevOps Engineers**
- [Toolchain Bootstrap](../../GUIDE-TOOLCHAIN-BOOTSTRAP.md) - Development setup
- [Setup Contract](../../SPEC-SETUP-CONTRACT.md) - Environment requirements
- [Integration Status](../../STATUS-INTEGRATION.md) - Component readiness

---

## Understanding OpenAMI vs AMI-ORCHESTRATOR

**OpenAMI** = Theoretical framework for self-evolving AI with formal safety guarantees
- Research phase (Q4 2025 - Q2 2026)
- Describes future capabilities: SPNs, CSTs, formal verification, self-evolution
- Documentation is **aspirational** and **conceptual**

**AMI-ORCHESTRATOR** = Production infrastructure platform available today
- Multi-storage DataOps, MCP servers, cryptographic audit trails
- 60+ production tests, Docker-based deployment
- Documentation is **working** and **tested**

**When to use which docs:**
- Learning about the vision → Read OpenAMI guides
- Building actual systems → Use AMI-ORCHESTRATOR docs

---

## Contributing

OpenAMI guides will be developed alongside implementation (Q4 2025 - Q2 2026).

**Want to contribute now?**
- Improve [AMI-ORCHESTRATOR documentation](../../../README.md)
- Add [production examples](../../../README.md#mcp-integration)
- Enhance [research specifications](../../../compliance/docs/research/OpenAMI/)

**Standards for future OpenAMI guides:**
- Align with actual implementation (not aspirational)
- Provide working code examples
- Test all procedures end-to-end
- Reference specific source code locations

---

## Getting Help

**For AMI-ORCHESTRATOR (production infrastructure):**
- Check [main README](../../../README.md) for setup and usage
- Review [ami-agent documentation](../../../README.md#ami-agent-reliable-auditable-verifiable-automation)
- Browse [MCP server examples](../../../README.md#mcp-integration)

**For OpenAMI (research framework):**
- Read [What is OpenAMI?](../overview/what-is-openami.md)
- Explore [theoretical specifications](../../../compliance/docs/research/OpenAMI/)
- See [Executive Action Plan](../../../compliance/docs/research/EXECUTIVE_ACTION_PLAN.md) for roadmap

**Found documentation errors?**
- File issues or submit PRs to improve accuracy

---

**Next**: Start with [What is OpenAMI?](../overview/what-is-openami.md) to understand OpenAMI concepts, or jump to [AMI-ORCHESTRATOR README](../../../README.md) for production infrastructure.
