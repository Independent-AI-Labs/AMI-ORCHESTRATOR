# Open AMI Overview

This section provides a high-level introduction to the OpenAMI theoretical framework for various audiences.

> **⚠️ STATUS**: OpenAMI is a research framework describing future capabilities (Q4 2025 - Q2 2026 target). For **production infrastructure**, see [AMI-ORCHESTRATOR README](../../../README.md).

## Contents

### Available Now

1. [**Executive Summary**](./executive-summary.md)
   - High-level overview for decision makers
   - Value proposition and strategic benefits
   - Vision and long-term roadmap

2. [**What is Open AMI?**](./what-is-openami.md)
   - Core concepts and philosophy
   - The problem Open AMI solves
   - How it differs from other approaches
   - Four Pillars (Compliance, Integrity, Abstraction, Dynamics)
   - Self-Evolution and Bootstrapping principles

### Future Documentation (Q4 2025 - Q2 2026)

As OpenAMI components are implemented, additional guides will cover:
- **Key Concepts Deep Dive**: Secure Process Nodes (SPNs), Cryptographic State Tokens (CSTs), Formal Verification
- **Use Cases**: Enterprise AI, critical infrastructure, healthcare/financial services, autonomous systems
- **Comparison with Alternatives**: vs. Traditional ML Ops, LLM + Tools, Constitutional AI

For detailed research specifications now, see [OpenAMI research docs](../../../compliance/docs/research/OpenAMI/).

## Who Should Read This?

### For OpenAMI Vision (Aspirational)
- **Executives & Decision Makers**: Start with [Executive Summary](./executive-summary.md)
- **Technical Leaders**: Read [What is Open AMI?](./what-is-openami.md) for theoretical framework
- **Researchers**: Explore [research specifications](../../../compliance/docs/research/OpenAMI/) for detailed theory

### For Production Infrastructure (Available Now)
- **Architects**: See [AMI-ORCHESTRATOR README](../../../README.md) for current system design
- **Developers**: Jump to [AMI-ORCHESTRATOR Setup](../../../README.md) and [MCP Integration](../../../README.md#mcp-integration)
- **DevOps**: Review [Toolchain Bootstrap](../../GUIDE-TOOLCHAIN-BOOTSTRAP.md)

## Quick Decision Tree

```
What are you looking for?
├─ Understanding the OpenAMI vision (theoretical)?
│   ├─ Executive perspective → Read Executive Summary
│   ├─ Technical concepts → Read What is Open AMI?
│   └─ Deep research → See compliance/docs/research/OpenAMI/
│
└─ Building with production infrastructure (available now)?
    ├─ Getting started → AMI-ORCHESTRATOR README
    ├─ MCP integration → MCP Servers documentation
    └─ Development setup → Toolchain Bootstrap guide
```

## Key Takeaways

After reading this overview section, you should understand:

✅ **OpenAMI** is a theoretical framework for self-evolving AI with formal safety guarantees (Q4 2025 - Q2 2026)
✅ **AMI-ORCHESTRATOR** is the production infrastructure platform available today
✅ What problem OpenAMI aims to solve and why it matters
✅ The foundational concepts: Four Pillars (Compliance, Integrity, Abstraction, Dynamics) and Self-Evolution
✅ Where to go next based on your needs:
   - Vision/theory → Read the docs here
   - Production work → See [AMI-ORCHESTRATOR README](../../../README.md)

---

## Understanding OpenAMI vs AMI-ORCHESTRATOR

**OpenAMI** = Theoretical framework for safe self-evolving AI
- Research phase (Q4 2025 - Q2 2026 target)
- Describes future capabilities: SPNs, CSTs, formal verification, self-evolution
- Documentation here is **aspirational** and **conceptual**

**AMI-ORCHESTRATOR** = Production infrastructure available today
- Multi-storage DataOps, MCP servers (DataOps, SSH, Browser, Files)
- Cryptographic audit trails, 60+ integration tests
- Documentation is **working** and **tested**

---

**Next**:
- **For vision**: [Executive Summary](./executive-summary.md) or [What is Open AMI?](./what-is-openami.md)
- **For production**: [AMI-ORCHESTRATOR README](../../../README.md)
