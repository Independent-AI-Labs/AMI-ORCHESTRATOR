# AMI-ORCHESTRATOR

**OPEN DISTRIBUTED HYPERSCALER**

Secure infrastructure for scalable enterprise automation and governance. ISO / NIST / EU AI Act compliant by design. Run anywhere.

[![Python 3.12+](https://img.shields.io/badge/Python_-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT_-green.svg)](LICENSE)
[![EU AI Act](https://img.shields.io/badge/EU_AI_Act_|_GDPR_-Compliant-blue.svg)](compliance/)
[![ISO](https://img.shields.io/badge/ISO_9001_|_27001_|_42001_-Compliant-blue.svg)](compliance/)
[![NIST](https://img.shields.io/badge/NIST_AI_CSF_|_RMF_-Compliant-blue.svg)](compliance/)

---

## Why AMI-ORCHESTRATOR

**The only enterprise platform architected for 100% industry-compliance with 0 vendor lock-in.**

### Production Ready

- **Task Execution Framework**: Worker/moderator pattern with retry loops and timeout handling (scripts/automation/tasks.py)
- **Documentation Maintenance**: Automated doc sync with codebase - UPDATE/ARCHIVE/DELETE actions (scripts/automation/docs.py)
- **Git Sync Automation**: Intelligent commit/push with validation and moderator checks (scripts/automation/sync.py)
- **Batch Code Auditing**: Parallel code quality analysis with pattern-based detection (scripts/automation/audit.py)
- **Real-time Streaming**: JSON streaming output for all agent operations via Claude Code `--output-format stream-json`



### Compliance Framework

Layer 4: GOVERNANCE    → Compliance Manifest, Risk Management, Human Oversight
Layer 3: INTELLIGENCE  → Verifiable Software Development & Evolution, Proof Generation, ML Models
Layer 2: OPERATIONAL   → Secure Process Nodes (SPNs), Cryptographic State Tokens for Auditable Provenance (CSTs)
Layer 1: FOUNDATION    → Immutable Code & Axioms, Process Theory, Safety Protocols

### ami-agent: Reliable, Auditable, Verifiable Automation

Unified CLI for secure, hook-protected automation with full auditability (scripts/ami-agent):

```bash
ami-agent                       # Interactive mode with Claude Code
ami-agent --audit base/         # Batch code quality analysis
ami-agent --tasks tasks/        # Execute .md task files
ami-agent --docs docs/          # Maintain documentation
ami-agent --sync base           # Git commit/push with validation
ami-agent --hook code-quality   # Hook validator (called by Claude Code)
```

**Features:**
- Session-based logging for full auditability (logs/{mode}/{session_id}.log)
- Worker/moderator validation pattern prevents premature completion
- Streaming JSON output for real-time monitoring
- Configurable timeouts, retries, and parallel execution
- Hook integration for command safety and code quality gates


### Built-in Validators

Three hook validators protect agent operations (scripts/automation/hooks.py):

1. **CommandValidator** (`command-guard`)
   - Blocks destructive bash operations (rm -rf, force push, rebase)
   - Enforces use of dedicated tools over pipes/redirects
   - Validates file permissions and git operations

2. **CodeQualityValidator** (`code-quality`)
   - Pre-validates Edit/Write tool calls before execution
   - Catches exception handling issues, unchecked subprocess calls
   - Enforces zero-tolerance quality policy

3. **ResponseScanner** (`response-scanner`)
   - Validates completion markers (WORK DONE vs FEEDBACK)
   - Runs completion moderator for premature termination detection
   - Prevents agents from claiming success without verification

All validators log to `logs/hooks/{session_id}.log` and integrate with Claude Code's hook system.


### MCP Integration

Model Context Protocol servers provide specialized capabilities to Claude:

| Module | Server | Script | Capabilities |
|--------|--------|--------|--------------|
| base | SSH | `base/scripts/run_ssh_fastmcp.py` | Secure remote command execution |
| base | DataOps | `base/scripts/run_dataops_fastmcp.py` | Database operations, data access layer |
| browser | Chrome | `browser/scripts/run_chrome.py` | Browser automation, tab management, screenshots |
| files | Filesys | `files/scripts/run_filesys_fastmcp.py` | Filesystem operations, file extraction |
| domains/marketing | Research | `domains/marketing/scripts/run_research_mcp.py` | Research tools and data collection |
| nodes | Launcher | `nodes/scripts/run_launcher_mcp.py` | Service orchestration and management |

MCP servers are configured in `scripts/config/automation.yaml` under `mcp.servers` and automatically loaded in interactive mode.


### Usage Examples

```bash
# Audit codebase for quality issues
ami-agent --audit base/ --parallel

# Execute task files with full logging
ami-agent --tasks tasks/ --root-dir .

# Maintain documentation (sync with codebase)
ami-agent --docs docs/ --root-dir .

# Git sync with validation
ami-agent --sync base --user-instruction "Add new feature"

# Interactive development with MCP servers
ami-agent --interactive

# Run tests across all modules
./scripts/ami-run.sh scripts/run_tests.py
```

### Quick Start

**1. Clone and setup:**
```bash
git clone https://github.com/independent-ai-labs/ami-orchestrator
cd ami-orchestrator
python install.py
```

This bootstraps:
- Git submodules (base, browser, files, nodes, domains, compliance, streams, ux)
- Python 3.12 via `uv`
- Per-module virtual environments
- Pre-commit hooks
- Shell aliases (`ami-run`, `ami-uv`)

**2. Verify installation:**
```bash
./scripts/ami-run.sh base/scripts/run_tests.py
ami-agent --help
```

**3. Start services (optional):**
```bash
docker compose -f docker-compose.services.yml up -d
```


### Running MCP Servers

MCP servers run via `ami-run` wrapper and are automatically configured in interactive mode:

```bash
# SSH remote execution
ami-run base/scripts/run_ssh_fastmcp.py

# DataOps database operations
ami-run base/scripts/run_dataops_fastmcp.py

# Chrome browser automation
ami-run browser/scripts/run_chrome.py

# Filesystem operations
ami-run files/scripts/run_filesys_fastmcp.py --root-dir /path/to/files

# Research tools
ami-run domains/marketing/scripts/run_research_mcp.py

# Service launcher
ami-run nodes/scripts/run_launcher_mcp.py
```

Configuration: `scripts/config/automation.yaml` → `mcp.servers`

### License

MIT License - Copyright © 2025 Independent AI Labs

See [LICENSE](LICENSE) for full text.

---

## Links

- **Documentation**: [docs/](docs/) - Architecture, setup contracts, quality policy
- **Compliance**: [compliance/docs/](compliance/docs/) - ISO/NIST/EU AI Act research
- **Module Setup**: [docs/SPEC-SETUP-CONTRACT.md](docs/SPEC-SETUP-CONTRACT.md)
- **Toolchain Bootstrap**: [docs/GUIDE-TOOLCHAIN-BOOTSTRAP.md](docs/GUIDE-TOOLCHAIN-BOOTSTRAP.md)
- **Architecture Map**: [docs/GUIDE-ARCHITECTURE-MAP.md](docs/GUIDE-ARCHITECTURE-MAP.md)
- **Quality Policy**: [docs/POLICY-QUALITY.md](docs/POLICY-QUALITY.md)

---
