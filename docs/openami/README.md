# Open AMI

Research framework for building AI systems with formal safety guarantees and compliance-by-design.

## What This Is

Open AMI is the theoretical framework and implementation roadmap for self-evolving AI systems that can prove their own safety. The core idea: AI that improves itself through formally verified steps, with cryptographic proof it won't violate constraints.

## Current Status

**Theory and design complete:**
- Four Pillars architecture (Compliance, Integrity, Abstraction, Dynamics)
- Bootstrapping approach for safe self-evolution
- Never-Jettison principle for constraint preservation
- Compliance framework mapping to EU AI Act, ISO, NIST

**Infrastructure implemented:**
- Multi-storage DataOps layer
- MCP servers for AI integration
- Document processing and browser automation
- See [AMI-ORCHESTRATOR](../../README.md) for working code

**In development:**
- Secure Process Nodes (SPN) abstraction
- Cryptographic State Tokens (CST)
- Formal verification integration
- Self-evolution engine (AAL/AADL compilers)

## Documentation

Most documentation describes the target architecture, not current implementation:

- [What is Open AMI?](./overview/what-is-openami.md) - Core concepts
- [Executive Summary](./overview/executive-summary.md) - Vision and goals
- [Implementation Status](./IMPLEMENTATION-STATUS.md) - What exists vs. what's planned
- [Quick Start](./guides/quickstart.md) - Getting started guide

## Research Foundation

The theoretical work is complete:
- [Bootstrapping approaches](../../learning/) - DSE-AI and formal verification methods
- [Open AMI paper](../../compliance/docs/research/) - Complete framework specification
- [Synthesis](../../learning/SYNTHESIS-OPENAMI-BOOTSTRAP.md) - Integration of approaches

## Getting Started

See the main [AMI-ORCHESTRATOR README](../../README.md) for setup instructions and current capabilities.

For the OpenAMI vision and roadmap, start with [What is Open AMI?](./overview/what-is-openami.md).
