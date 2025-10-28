# Contributing to AMI-ORCHESTRATOR

Thank you for your interest in contributing to AMI-ORCHESTRATOR. This document outlines our quality standards, development workflow, and contribution requirements.

## Core Principles

**We build enterprise-grade software for regulated industries. Every line of code must meet the highest standards.**

- Zero tolerance for quality violations
- Production-ready changes only - no workarounds, no backward compatibility adapters
- Security and compliance are non-negotiable
- Read source code before making any changes
- All contributions must pass automated quality gates

## Prerequisites

### Required Tools

- **Python 3.12+** (managed via `uv`)
- **Git** with submodule support
- **Docker** (for infrastructure services)
- **Node.js 18+** (for CMS development)

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/independent-ai-labs/ami-orchestrator
cd ami-orchestrator

# Bootstrap all modules
python install.py

# Verify installation
./scripts/ami-run.sh base/scripts/run_tests.py
```

## Development Workflow

### 1. Branch Strategy

**Main Development:**
- Primary work happens on `main` branch
- Keep `main` stable and production-ready
- All tests must pass before pushing to `main`

**Feature Branches:**
- Create feature branches for experimental work: `git checkout -b feature/feature-name`
- Create fix branches for bug fixes: `git checkout -b fix/bug-description`
- Branch naming: lowercase with hyphens, descriptive names
- Merge back to `main` via pull request after review

**Submodule Branches:**
- Keep submodules on `main` unless working on isolated changes
- Never commit to detached HEAD states
- If detached, return immediately to main: `git checkout main`

**Branch Hygiene:**
- Delete merged branches: `git branch -d feature/old-feature`
- Keep branches focused - one feature/fix per branch
- Rebase on `main` frequently to avoid merge conflicts

### 2. Before Making Changes

**Read the source code first. No exceptions.**

```bash
# Understand the module structure
cat docs/GUIDE-ARCHITECTURE-MAP.md

# Review quality policy
cat docs/POLICY-QUALITY.md

# Read project guidelines
cat CLAUDE.md
```

### 3. Making Changes

#### Module Boundaries

Leave module directories alone unless explicitly directed:
- `base/` - Core infrastructure
- `browser/` - Chrome automation
- `compliance/` - Regulatory framework
- `domains/` - Domain-specific logic
- `files/` - File operations
- `nodes/` - Service orchestration
- `streams/` - Communication infrastructure
- `ux/` - Web platform

**When adding dependencies:**
- New dependencies MUST go in a new module or existing appropriate module
- Ask maintainers where to place it first
- Pin exact versions
- Refresh lock files via module tooling

#### Code Quality Standards

**Zero Tolerance Policy:**
- No `# noqa` comments (except in documented exempt files)
- No `# type: ignore` comments (except in documented exempt files)
- No workarounds or temporary fixes
- No versioned files or temporal markers

**Required Standards:**
- Python 3.12 syntax and features
- Type hints on all function signatures
- Docstrings on all public functions
- Error handling without bare `except:` clauses
- No hardcoded paths or credentials

**Import Organization:**
- Standard library imports FIRST
- Third-party imports SECOND
- Local imports THIRD
- Use `base.scripts.env.paths.setup_imports()` for path bootstrapping

**Example:**
```python
#!/usr/bin/env python3
"""Module description."""

# Standard library imports FIRST
import logging
import sys
from pathlib import Path

# Bootstrap sys.path - MUST come before base imports
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))

# Now we can import from base
from base.scripts.env.paths import setup_imports  # noqa: E402

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

# Third-party imports
import yaml

# Local imports
from base.backend.config.loader import load_config
```

### 4. Testing

**All changes must include tests.**

```bash
# Run module-specific tests
./scripts/ami-run.sh base/scripts/run_tests.py
./scripts/ami-run.sh browser/scripts/run_tests.py

# Run root-level tests
./scripts/ami-run.sh scripts/run_tests.py

# Run integration tests with services
./scripts/run_tests_with_services.sh
```

**Test Requirements:**
- Unit tests for all new functions
- Integration tests for cross-module features
- Fixture data must be committed to repo
- Tests must be deterministic and isolated

### 5. Quality Gates

Before submitting, your code MUST pass:

#### Configuration

**Linting and Type Checking Configurations:**
- **ruff**: `ruff.toml` in root and each module (targets Python 3.12)
- **mypy**: `mypy.ini` or `pyproject.toml` (pinned to `python_version = 3.12`)
- **pre-commit**: `.pre-commit-config.*.yaml` files for Git hooks

**Configuration Hygiene:**
- Module-local configs should be generated from Base templates to avoid drift
- Hooks must use `python -m ...` for portability (no hardcoded binary paths)
- Keep `python.ver`, `requirements*.txt`, and `uv.lock` in sync with actual runtime

**Current Standards:**
- Line length: 160 characters
- Target: Python 3.11+ syntax (transitioning to 3.12)
- Complexity limit: 10 (McCabe)
- Comprehensive rule set: pycodestyle, pyflakes, isort, bugbear, bandit security, pylint

#### Automated Checks

```bash
# Lint with ruff
ami-run -m ruff check .

# Type check with mypy
ami-run -m mypy .

# Run pre-commit hooks (if configured)
pre-commit run --all-files
```

#### Hook Validation

AMI-ORCHESTRATOR uses three-layer hook validation:

**1. Command Guard** - Prevents destructive operations
- Blocks `rm -rf`, force push, destructive git operations
- Enforces dedicated tools over pipes/redirects

**2. Code Quality Gate** - Pre-validates code changes
- Detects exception handling gaps
- Identifies unchecked subprocess calls
- Flags security issues

**3. Completion Verification** - Validates work completion
- Prevents premature "done" claims
- Runs moderator verification

**Your code will be blocked if it fails any validator.**

### 6. Documentation

**Documentation must mirror implemented features.**

- Update relevant README files
- Add entries to `docs/` for architectural changes
- Mark WIP items explicitly
- Update `docs/TODO-DOCS-GAPS.md` when removing features

### 7. Git Commits

**Never use `git commit` or `git push` directly.**

```bash
# Stage all changes (including in submodules if applicable)
git add -A

# In submodules, also stage there
cd base && git add -A && cd ..

# Use the orchestrator's commit script
./scripts/git_commit.sh "feat: add feature description"

# Use the orchestrator's push script
./scripts/git_push.sh
```

**These scripts:**
- Auto-stage all changes
- Run full test suite before committing
- Validate commit messages
- Check for quality issues
- Run CI/CD validation

**Commit Message Format:**
```
<type>: <description>

[optional body explaining what and why, not how]
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

**Examples:**
```
feat: add PostgreSQL connection pooling

Implement connection pooling for PostgreSQL DAO to reduce
connection overhead and improve performance under high load.
Uses asyncpg.create_pool with configurable pool size.
```

```
fix: prevent race condition in service launcher

Service health checks were racing with startup initialization.
Added 2-second startup delay before first health probe.
```

**Banned Patterns:**
- No AI/automation signatures (enforced by pre-commit hooks)
- No emojis
- No URLs or links
- Keep messages professional and descriptive

### 8. Pull Requests

**Before submitting:**

1. Ensure all tests pass locally
2. Run full quality checks
3. Update documentation
4. Squash fixup commits
5. Write clear PR description

**PR Requirements:**
- Link to related issue
- Describe what changed and why
- Include test plan
- Screenshots for UI changes
- Breaking changes clearly marked

## Automation System

### Running Commands

**Never run `python`, `pip`, or `pytest` directly.**

```bash
# Use ami-run for Python scripts
ami-run script.py
ami-run -m module

# Use ami-uv for package management
ami-uv sync
ami-uv add package

# Use ami-agent for automation tasks
ami-agent --audit base/
ami-agent --tasks tasks/
ami-agent --docs docs/
```

### Hook System

Hooks validate operations at three levels:

**Pre-Tool Use Hooks:**
- `command-guard` - Validates bash commands
- `code-quality` - Validates Edit/Write operations

**Stop Hooks:**
- `response-scanner` - Validates completion claims

**Configuration:** `scripts/config/automation.yaml`

**To test hooks locally:**
```bash
ami-agent --hook command-guard < test-input.json
ami-agent --hook code-quality < test-input.json
ami-agent --hook response-scanner < test-input.json
```

## Security

### Reporting Vulnerabilities

**Do NOT open public issues for security vulnerabilities.**

Email: security@independentailabs.com

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Security Standards

- All secrets in `.env` files (never committed)
- OpenBao for cryptographic secrets
- Least-privilege access patterns
- Input validation on all external data
- No eval() or exec() without sandboxing
- Validate URLs before fetching

## Code of Conduct

### Expected Behavior

- Professional and respectful communication
- Focus on technical merit
- Constructive feedback
- Collaborative problem-solving

### Unacceptable Behavior

- Personal attacks or harassment
- Discrimination of any kind
- Trolling or inflammatory comments
- Publishing private information
- Violating security policies

## Getting Help

- **Documentation**: Start with `docs/README.md`
- **Architecture**: Read `docs/GUIDE-ARCHITECTURE-MAP.md`
- **Setup Issues**: Check `docs/GUIDE-TOOLCHAIN-BOOTSTRAP.md`
- **Questions**: Open a GitHub issue with `[Question]` prefix

## Recognition

Contributors will be:
- Listed in commit history with Co-Authored-By tags
- Mentioned in release notes for significant contributions
- Invited to join the community for sustained contributions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Remember: We build software for regulated industries. Quality is not optional.**
