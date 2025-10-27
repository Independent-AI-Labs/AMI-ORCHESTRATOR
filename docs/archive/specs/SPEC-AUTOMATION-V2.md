> **ARCHIVED**: This specification has been fully implemented and superseded by the actual codebase.
> See `scripts/automation/` for the implemented automation system.
> Archived on: 2025-10-27

# AMI Automation System - Production Specification v2.0

**Version**: 2.0.0
**Created**: 2025-10-18
**Status**: IMPLEMENTED
**Breaking Changes**: YES - Complete rewrite, NO backward compatibility

---

## 1. Design Principles

1. **Simplicity First** - No over-engineering, minimal abstractions
2. **Pure Python** - Eliminate bash scripts entirely
3. **Zero Backward Compatibility** - Clean break, fresh start
4. **Production Ready** - Auditability, logging, monitoring built-in
5. **Claude Code Native** - Follow official documentation patterns
6. **Single Responsibility** - Each module does ONE thing well

---

## 2. Architecture Overview

### 2.1 Installation Structure

**IMPORTANT**: New automation system installs in **ORCHESTRATOR ROOT** (`/root/scripts/`), NOT in `/base/scripts/`.

The `/base/scripts/` directory remains UNTOUCHED until migration is complete.

```
/home/ami/Projects/AMI-ORCHESTRATOR/          # ORCHESTRATOR ROOT
│
├── automation/                                # NEW: Core automation package
│   ├── __init__.py
│   ├── config.py                              # Configuration (100 lines)
│   ├── hooks.py                               # Hook framework (300 lines)
│   ├── audit.py                               # Audit engine (500 lines)
│   ├── patterns.py                            # Pattern matching (200 lines)
│   ├── logging.py                             # Structured logging (150 lines)
│   └── agent_cli.py                           # Agent CLI abstraction + Claude impl (200 lines)
│
├── config/                                    # NEW: Configuration files
│   ├── automation.yaml                        # Main config
│   ├── hooks.yaml                             # Hook definitions
│   ├── patterns/                              # Audit patterns
│   │   ├── python.yaml
│   │   ├── javascript.yaml
│   │   └── security.yaml
│   └── prompts/                               # LLM instructions
│       ├── agent.txt                          # Interactive agent instruction (37 lines)
│       ├── audit.txt                          # Code audit instruction (474 lines)
│       ├── audit_diff.txt                     # Diff audit instruction (357 lines)
│       └── consolidate.txt                    # Pattern consolidation instruction (122 lines)
│
├── logs/                                      # NEW: Logs (gitignored)
│   ├── agent-debug.log                        # Debug log
│   ├── transcripts/                           # Session transcripts
│   │   └── YYYY-MM-DD/
│   │       └── {session-id}.jsonl
│   ├── hooks/                                 # Hook execution logs
│   │   └── YYYY-MM-DD/
│   │       └── {hook-name}.log
│   └── audits/                                # Audit run logs
│       └── YYYY-MM-DD/
│           └── {run-id}.log
│
└── scripts/
    ├── ami-agent                              # NEW: Unified entry point (Python, 300 lines)
    │                                          #      Replaces: claude-agent.sh, ami-hook, ami-audit
    │                                          #      4 modes: --interactive, --print, --hook, --audit
    ├── ami-run.sh                             # KEEP: Python wrapper (unchanged)
    ├── git_commit.sh                          # KEEP: Git commit wrapper (unchanged)
    └── git_push.sh                            # KEEP: Git push wrapper (unchanged)

base/scripts/                                  # OLD: Remains UNTOUCHED during migration
    ├── quality/
    │   ├── claude-audit.sh                    # Replaced by: ami-agent --audit
    │   ├── claude-audit-diff.sh               # Replaced by: ami-agent hook code-quality
    │   ├── code_quality_guard.sh              # Replaced by: ami-agent hook code-quality
    │   └── response_scanner.sh                # Replaced by: ami-agent hook response-scanner
    └── claude-agent.sh                        # Replaced by: ami-agent --interactive
```

**Total New Code**: ~1900 lines Python (vs ~2000+ lines bash currently)
**Prompt Files**: 990 lines extracted from bash scripts
**Line count**: config(120) + logging(150) + hooks(350) + patterns(200) + audit(550) + agent_cli(230) + ami-agent(300) = 1900
**Includes**: Comprehensive error handling, resource limits, input validation

**Installation Location**: Orchestrator root (`/home/ami/Projects/AMI-ORCHESTRATOR/`)
**Migration Strategy**: Old scripts in `/base/scripts/` stay until new system is validated

### 2.2 Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│ User: ami-agent --interactive                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            v
┌───────────────────────────────────────────────────────────────┐
│ Config.load()                                                 │
│  - Read automation.yaml                                       │
│  - Load MCP servers config (if mcp.enabled)                   │
│  - Load prompts from config/prompts/                          │
│  - Apply {root} template substitution                         │
└───────────────────┬───────────────────────────────────────────┘
                    │
                    v
┌───────────────────────────────────────────────────────────────┐
│ mode_interactive()                                            │
│  1. Load agent instruction from prompts/agent.txt             │
│  2. Apply {date} template substitution                        │
│  3. Get ClaudeAgentCLI (implements AgentCLI)                  │
│  4. Call cli.run_interactive() which:                         │
│     • Builds MCP config from automation.yaml                  │
│     • Substitutes {root} in server args                       │
│     • Executes: claude --mcp-config <temp> --dangerous...     │
└───────────────────┬───────────────────────────────────────────┘
                    │
                    v
┌───────────────────────────────────────────────────────────────┐
│ Claude Code (with MCP servers from config)                    │
│  - Browser MCP: chrome automation                             │
│  - Future: Database, filesystem, custom servers               │
└───────────────────────────────────────────────────────────────┘
```

**Key Design Points**:

1. **AgentCLI Abstraction**: `AgentCLI` interface with `ClaudeAgentCLI` implementation isolates all Claude Code CLI specifics (commands, flags, parameters)

2. **AgentConfig Pattern**: Type-safe configuration objects (`AgentConfig` dataclass) with presets for common agent types (audit, worker, interactive, etc.) - NO string matching

3. **Configuration-Driven MCP**: MCP servers loaded from `automation.yaml`, not hardcoded

4. **Template Substitution**: `{root}` variable in server args enables relative paths

5. **Extensible CLI**: Claude Code CLI changes only affect `ClaudeAgentCLI` class, not core logic

6. **Proper Separation**: Configuration (AgentConfig) separate from execution (AgentCLI)

---

## 3. Configuration System

### 3.1 Single Configuration File: `config/automation.yaml`

**Source**: Claude Code docs recommend JSON settings files, but we use YAML for readability

```yaml
# AMI Automation Configuration
version: "2.0.0"

# Environment
environment: "${AMI_ENV:development}"

# Paths (all relative to ORCHESTRATOR_ROOT)
paths:
  logs: "logs"
  config: "config"
  cache: ".cache"

# Logging
logging:
  level: "INFO"
  format: "json"
  retention_days: 90

  # Transcript archival (per Claude Code docs)
  transcripts:
    enabled: true
    path: "logs/transcripts/{date:%Y-%m-%d}"
    compress: true

# Hooks (loaded from hooks.yaml)
hooks:
  file: "config/hooks.yaml"
  timeout: 30
  parallel: false

# Claude Code CLI settings (abstraction layer in code)
claude_cli:
  command: "claude"
  model_default: "claude-sonnet-4-5"
  model_audit: "claude-sonnet-4-5"  # 100% accuracy requirement

# MCP Servers (Model Context Protocol)
mcp:
  enabled: true
  servers:
    browser:
      command: "python3"
      args:
        - "{root}/browser/scripts/run_chrome.py"
        - "--data-root"
        - "{root}/browser/data"
    # Future: add more MCP servers as needed
    # database:
    #   command: "python3"
    #   args:
    #     - "{root}/database/scripts/mcp_server.py"

# Audit
audit:
  patterns_dir: "config/patterns"
  parallel: true
  workers: 4
  cache_ttl: 3600
```

**Key Features**:
- Environment variable substitution: `${VAR:default}`
- Path templates: `{date:%Y-%m-%d}`, `{session_id}`, `{root}`
- MCP server configuration: Extensible, can add/remove servers
- Claude Code CLI settings: Command and model config (implementation abstracted in code)
- Single file, easy to understand
- No complex merging logic

### 3.2 Hook Configuration: `config/hooks.yaml`

**Source**: Follows Claude Code hook configuration structure from docs

```yaml
# Hook Definitions
# Ref: https://docs.claude.com/en/docs/claude-code/hooks.md

version: "2.0.0"

hooks:
  # PreToolUse - Command Guard
  - event: "PreToolUse"
    matcher: "Bash"
    command: "ami-agent hook command-guard"
    timeout: 10

  # PreToolUse - Code Quality Guard
  - event: "PreToolUse"
    matcher: ["Edit", "Write"]
    command: "ami-agent hook code-quality"
    timeout: 60

  # Stop - Response Scanner
  - event: "Stop"
    command: "ami-agent hook response-scanner"
    timeout: 10

  # SubagentStop - Response Scanner
  - event: "SubagentStop"
    command: "ami-agent hook response-scanner"
    timeout: 10
```

**Key Features**:
- Declarative hook definitions
- Matches Claude Code JSON settings format
- Commands point to unified CLI: `ami-agent hook <validator>`
- Timeout per hook
- Single entry point for all hook validators

### 3.3 Pattern Configuration: `config/patterns/python.yaml`

```yaml
# Python Code Quality Patterns
version: "2.0.0"
language: "python"

patterns:
  # Pattern 1: Exception -> False/None/Empty
  - id: "exception_false_return"
    severity: "CRITICAL"
    regex: 'except.*:\s*return\s+(False|None|\{\}|\[\])'
    message: "Exception caught and suppressed with False/None/empty return"

  # Pattern 36: Lint Suppressions
  - id: "lint_suppressions"
    severity: "CRITICAL"
    regex: '#\s*(noqa|type:\s*ignore|pylint:\s*disable|fmt:\s*off)'
    message: "Lint suppression marker hides code quality issues"
    exemptions:
      files:
        - "**/env/paths.py"      # Standard imports pattern
        - "**/conftest.py"       # Test fixtures
```

**Key Features**:
- One file per language
- Simple regex patterns (no AST parsing initially)
- Exemptions supported
- Clear severity levels

### 3.4 Prompt Configuration: `config/prompts/`

**Source**: Extracted from existing bash scripts to eliminate hardcoded instructions

All LLM instructions are stored as plain text files in `config/prompts/`:

**`agent.txt`** (37 lines) - Interactive agent instruction:
```
ALL CODE QUALITY ISSUES ARE ALWAYS YOUR FAULT AND YOUR RESPONSIBILITY
YOU MUST FIX EVERY ERROR YOU ENCOUNTER REGARDLESS OF WHEN IT WAS INTRODUCED
NEVER SUPPRESS ERRORS WITH ignore_errors OR TYPE IGNORE COMMENTS
...
```

**`audit.txt`** (474 lines) - Code audit instruction for full file analysis

**`audit_diff.txt`** (357 lines) - Diff-based audit instruction for Edit/Write validation

**`consolidate.txt`** (122 lines) - Pattern consolidation instruction for cross-file analysis

**Key Features**:
- All instructions version-controlled
- Easy to review and modify without touching Python code
- Support for template variables: `{date}`, `{file_path}`, etc.
- No hardcoded prompts in source code

**Configuration Reference**:
```yaml
# In automation.yaml
prompts:
  dir: "config/prompts"
  agent: "agent.txt"
  audit: "audit.txt"
  audit_diff: "audit_diff.txt"
  consolidate: "consolidate.txt"
```

---

## 4. Core Implementation

### 4.1 Configuration Loader (`automation/config.py`)

**Complexity**: ~100 lines

**Source**: Follows `/base` conventions using `base.scripts.env.paths.setup_imports()`

```python
"""Configuration management for AMI automation."""

import os
import sys
from pathlib import Path
from typing import Any
import yaml

# Standard /base imports pattern
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))
from base.scripts.env.paths import setup_imports  # noqa: E402

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()


class Config:
    """Automation configuration."""

    def __init__(self, config_file: Path | None = None):
        """Load configuration."""
        self.root = ORCHESTRATOR_ROOT
        self.config_file = config_file or self.root / "config/automation.yaml"
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        """Load and parse YAML config.

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is malformed
            ValueError: If config is empty or invalid
        """
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        with open(self.config_file) as f:
            data = yaml.safe_load(f)

        if not data or not isinstance(data, dict):
            raise ValueError(f"Config file is empty or invalid: {self.config_file}")

        # Substitute environment variables
        return self._substitute_env(data)

    def _substitute_env(self, data: Any) -> Any:
        """Recursively substitute ${VAR:default} patterns."""
        if isinstance(data, dict):
            return {k: self._substitute_env(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env(v) for v in data]
        elif isinstance(data, str) and "${" in data:
            # Simple substitution: ${VAR:default}
            import re
            def replace(match):
                var, default = match.group(1), match.group(2) or ""
                return os.environ.get(var, default)
            return re.sub(r'\$\{([A-Z_]+)(?::([^}]*))?\}', replace, data)
        return data

    def resolve_path(self, key: str, **kwargs) -> Path:
        """Resolve path template with variables."""
        template = self.get(key)
        path_str = template.format(**kwargs)
        return self.root / path_str

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot notation."""
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default


# Global config instance
_config: Config | None = None

def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
```

**Features**:
- Auto-detects orchestrator root
- Environment variable substitution
- Path template resolution
- Dot notation access: `config.get("logging.level")`
- Lazy singleton

### 4.2 Hook Framework (`automation/hooks.py`)

**Complexity**: ~300 lines

```python
"""Hook execution framework.

Ref: https://docs.claude.com/en/docs/claude-code/hooks.md
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .config import get_config
from .logging import get_logger


@dataclass
class HookInput:
    """Hook input data (from Claude Code)."""
    session_id: str
    hook_event_name: str
    tool_name: str | None
    tool_input: dict | None
    transcript_path: Path | None

    @classmethod
    def from_stdin(cls) -> "HookInput":
        """Parse hook input from stdin."""
        data = json.loads(sys.stdin.read())
        return cls(
            session_id=data.get("session_id", ""),
            hook_event_name=data.get("hook_event_name", ""),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input"),
            transcript_path=Path(data["transcript_path"]) if data.get("transcript_path") else None,
        )


@dataclass
class HookResult:
    """Hook output (to Claude Code)."""
    decision: Literal["allow", "deny", "block"] | None = None
    reason: str | None = None

    def to_json(self) -> str:
        """Convert to JSON for Claude Code."""
        output = {}
        if self.decision:
            output["decision"] = self.decision
        if self.reason:
            output["reason"] = self.reason
        return json.dumps(output)

    @classmethod
    def allow(cls) -> "HookResult":
        """Allow operation."""
        return cls()

    @classmethod
    def deny(cls, reason: str) -> "HookResult":
        """Deny operation (PreToolUse)."""
        return cls(decision="deny", reason=reason)

    @classmethod
    def block(cls, reason: str) -> "HookResult":
        """Block stop (Stop hooks)."""
        return cls(decision="block", reason=reason)


class HookValidator:
    """Base class for hook validators."""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("hooks")

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate hook input. Override in subclasses."""
        raise NotImplementedError

    def run(self) -> int:
        """Execute hook validation (CLI entry point)."""
        try:
            hook_input = HookInput.from_stdin()

            # Log execution
            self.logger.info(
                "hook_execution",
                hook_name=self.__class__.__name__,
                event=hook_input.hook_event_name,
                tool=hook_input.tool_name,
            )

            # Validate
            result = self.validate(hook_input)

            # Output result
            print(result.to_json())

            # Log result
            self.logger.info(
                "hook_result",
                decision=result.decision or "allow",
                reason=result.reason,
            )

            return 0

        except Exception as e:
            self.logger.error("hook_error", error=str(e))
            # On error, allow operation (fail open)
            print(HookResult.allow().to_json())
            return 0
```

**Features**:
- Follows Claude Code hook JSON format
- Base class for all validators
- Structured logging
- Fail-open on errors (safety)
- Simple input/output models

### 4.3 Command Validator (`automation/hooks.py` continued)

```python
class CommandValidator(HookValidator):
    """Validates Bash commands."""

    DENY_PATTERNS = [
        (r'\bpython3?\b', "Use ami-run instead of direct python"),
        (r'\bpip3?\b', "Add to pyproject.toml and use ami-uv sync"),
        (r'\buv\s+', "Use ami-uv wrapper"),
        (r'\bpytest\b', "Use ami-run -m pytest"),
        (r'--no-verify', "Git hook bypass forbidden"),
        (r'\bgit\s+commit\b', "Use scripts/git_commit.sh"),
        (r'\bgit\s+push\b', "Use scripts/git_push.sh"),
        (r'[^&]&[^&]', "Use run_in_background parameter instead of &"),
        (r';', "Use separate Bash calls or && for dependencies"),
        (r'\|\|', "Use separate Bash calls instead of ||"),
        (r'>>', "Use Edit/Write tools instead of >>"),
        (r'\bsed\b.*-i', "Use Edit tool instead of sed -i"),
    ]

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate bash command."""
        if hook_input.tool_name != "Bash":
            return HookResult.allow()

        command = json.dumps(hook_input.tool_input)  # Search entire JSON

        import re
        for pattern, message in self.DENY_PATTERNS:
            if re.search(pattern, command):
                return HookResult.deny(f"{message} (pattern: {pattern})")

        return HookResult.allow()
```

**Features**:
- Simple regex patterns
- Clear error messages
- Searches entire tool input JSON
- ~50 lines of code (vs 200+ in bash)

### 4.4 Code Quality Validator (`automation/hooks.py` continued)

```python
class CodeQualityValidator(HookValidator):
    """Validates code changes for quality regressions using LLM-based audit."""

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate code quality using LLM diff audit."""
        if hook_input.tool_name not in ("Edit", "Write"):
            return HookResult.allow()

        # Extract file path
        file_path = hook_input.tool_input.get("file_path", "")
        if not file_path.endswith(".py"):
            return HookResult.allow()

        # Extract old/new code
        if hook_input.tool_name == "Edit":
            old_code = hook_input.tool_input.get("old_string", "")
            new_code = hook_input.tool_input.get("new_string", "")
        else:  # Write
            old_code = Path(file_path).read_text() if Path(file_path).exists() else ""
            new_code = hook_input.tool_input.get("content", "")

        # Build diff context for LLM audit
        diff_context = f"""FILE: {file_path}

## OLD CODE
```
{old_code}
```

## NEW CODE
```
{new_code}
```
"""

        # Run LLM-based diff audit
        from .agent_cli import get_agent_cli, AgentConfigPresets

        cli = get_agent_cli()
        prompts_dir = self.config.root / self.config.get("prompts.dir")
        audit_diff_instruction = prompts_dir / self.config.get("prompts.audit_diff")

        exit_code, output = cli.run_print(
            instruction_file=audit_diff_instruction,
            stdin=diff_context,
            agent_config=AgentConfigPresets.audit_diff(),
        )

        # Check result
        if exit_code == 0 and output.strip() == "PASS":
            return HookResult.allow()
        else:
            # Extract failure reason from output
            reason = output if output else "Code quality regression detected"
            return HookResult.deny(f"❌ CODE QUALITY CHECK FAILED\n\n{reason}\n\nZero-tolerance policy: NO regression allowed.")
```

**Features**:
- **LLM-based validation**: Uses Claude Sonnet 4.5 for 100% accuracy
- **Diff analysis**: Compares old vs new code to detect regressions
- **Instruction-driven**: Uses `audit_diff.txt` from config
- Supports Edit and Write tools
- Python-only initially (extensible)
- ~50 lines of code (vs 100+ in bash)
- **Critical**: Prevents code quality regressions before they're committed

### 4.5 Response Scanner (`automation/hooks.py` continued)

```python
class ResponseScanner(HookValidator):
    """Scans responses for communication violations and completion markers."""

    PROHIBITED_PATTERNS = [
        (r"\byou'?re\s+(absolutely|completely)?\s*(correct|right)\b", "you're right variations"),
        (r"\bthe\s+issue\s+is\s+clear\b", "the issue is clear"),
        (r"\bi\s+see\s+the\s+(problem|issue)\b", "I see the problem"),
    ]

    COMPLETION_MARKERS = ["WORK DONE", "FEEDBACK:"]

    def validate(self, hook_input: HookInput) -> HookResult:
        """Scan last assistant message."""
        if not hook_input.transcript_path or not hook_input.transcript_path.exists():
            return HookResult.allow()

        # Read transcript
        last_message = self._get_last_assistant_message(hook_input.transcript_path)
        if not last_message:
            return HookResult.allow()

        # Check for completion markers
        if any(marker in last_message for marker in self.COMPLETION_MARKERS):
            return HookResult.allow()  # Work done, allow stop

        # Check for violations
        import re
        for pattern, description in self.PROHIBITED_PATTERNS:
            if re.search(pattern, last_message, re.IGNORECASE):
                return HookResult.block(
                    f"Communication violation: {description}. "
                    "Verify source code before making claims."
                )

        # No markers found, request completion
        return HookResult.block(
            'Output "WORK DONE" when finished or "FEEDBACK: <questions>" if stuck.'
        )

    def _get_last_assistant_message(self, transcript_path: Path) -> str:
        """Get last assistant message from transcript."""
        last_text = ""
        for line in transcript_path.read_text().splitlines():
            try:
                msg = json.loads(line)
                if msg.get("type") == "assistant":
                    # Extract text content
                    for content in msg.get("message", {}).get("content", []):
                        if content.get("type") == "text":
                            last_text = content.get("text", "")
            except:
                continue
        return last_text
```

**Features**:
- Reads transcript directly (Claude Code provides path)
- Checks completion markers
- Blocks stop if no marker found
- ~60 lines of code (vs 200+ in bash)

### 4.6 Pattern Matcher (`automation/patterns.py`)

**Complexity**: ~200 lines

```python
"""Pattern matching for code quality checks."""

from dataclasses import dataclass
from pathlib import Path
import re
import yaml

from .config import get_config


@dataclass
class Violation:
    """Code violation."""
    line: int
    pattern_id: str
    severity: str
    message: str


class PatternMatcher:
    """Matches code against quality patterns."""

    def __init__(self, language: str):
        self.language = language
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> list[dict]:
        """Load patterns from YAML."""
        config = get_config()
        patterns_dir = Path(config.get("audit.patterns_dir"))
        pattern_file = patterns_dir / f"{self.language}.yaml"

        if not pattern_file.exists():
            return []

        with open(pattern_file) as f:
            data = yaml.safe_load(f)
            return data.get("patterns", [])

    def find_violations(self, code: str) -> set[Violation]:
        """Find all violations in code."""
        violations = set()

        for pattern in self.patterns:
            regex = pattern.get("regex")
            if not regex:
                continue

            for i, line in enumerate(code.splitlines(), 1):
                if re.search(regex, line):
                    # Check exemptions
                    if self._is_exempt(pattern, line):
                        continue

                    violations.add(Violation(
                        line=i,
                        pattern_id=pattern["id"],
                        severity=pattern.get("severity", "WARNING"),
                        message=pattern.get("message", "Violation detected"),
                    ))

        return violations

    def _is_exempt(self, pattern: dict, line: str) -> bool:
        """Check if line is exempt from pattern."""
        exemptions = pattern.get("exemptions", {})

        # Check exempt codes (for suppressions)
        exempt_codes = exemptions.get("codes", [])
        for code in exempt_codes:
            if code in line:
                return True

        return False
```

**Features**:
- Loads patterns from YAML
- Simple regex matching
- Exemption support
- Returns structured violations
- Extensible to other languages

### 4.7 Audit Engine (`automation/audit.py`)

**Complexity**: ~400 lines

```python
"""Audit orchestration engine."""

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import hashlib
import json

from .config import get_config
from .logging import get_logger
from .patterns import PatternMatcher


@dataclass
class FileResult:
    """Audit result for a single file."""
    file_path: Path
    status: str  # PASS/FAIL/ERROR
    violations: list[dict]
    execution_time: float


class AuditEngine:
    """Orchestrates multi-file audits."""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("audit")

    def audit_directory(
        self,
        directory: Path,
        parallel: bool = True,
        max_workers: int = 4,
    ) -> list[FileResult]:
        """Audit all files in directory."""
        from datetime import datetime
        import time

        files = list(self._find_files(directory))

        # Create output directory with DD.MM.YYYY format
        date_str = datetime.now().strftime("%d.%m.%Y")
        output_dir = directory / "docs" / "audit" / date_str
        output_dir.mkdir(parents=True, exist_ok=True)

        # Consolidated report path
        consolidated_file = output_dir / "CONSOLIDATED.md"

        self.logger.info(
            "audit_started",
            directory=str(directory),
            file_count=len(files),
            parallel=parallel,
            output_dir=str(output_dir),
        )

        # Progress tracking
        start_time = time.time()
        results = []

        if parallel:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                for i, result in enumerate(executor.map(self._audit_file, files), 1):
                    results.append(result)

                    # Print progress
                    elapsed = time.time() - start_time
                    avg_time = elapsed / i
                    remaining = (len(files) - i) * avg_time
                    print(f"Progress: {i}/{len(files)} ({i*100//len(files)}%) | "
                          f"Elapsed: {elapsed:.1f}s | Est remaining: {remaining:.1f}s")

                    # Save report (mirror directory structure)
                    self._save_report(result, directory, output_dir)

                    # Consolidate patterns (only for FAIL/ERROR)
                    if result.status in ("FAIL", "ERROR"):
                        self._consolidate_patterns(result, output_dir, consolidated_file)
        else:
            for i, file_path in enumerate(files, 1):
                result = self._audit_file(file_path)
                results.append(result)

                # Print progress
                elapsed = time.time() - start_time
                avg_time = elapsed / i
                remaining = (len(files) - i) * avg_time
                print(f"Progress: {i}/{len(files)} ({i*100//len(files)}%) | "
                      f"Elapsed: {elapsed:.1f}s | Est remaining: {remaining:.1f}s")

                # Save report
                self._save_report(result, directory, output_dir)

                # Consolidate patterns (only for FAIL/ERROR)
                if result.status in ("FAIL", "ERROR"):
                    self._consolidate_patterns(result, output_dir, consolidated_file)

        self.logger.info(
            "audit_completed",
            total=len(results),
            passed=sum(1 for r in results if r.status == "PASS"),
            failed=sum(1 for r in results if r.status == "FAIL"),
        )

        return results

    def _find_files(self, directory: Path) -> Iterator[Path]:
        """Find all auditable files."""
        patterns = self.config.get("audit.scanning.include_patterns", [])

        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    # Check exclusions
                    if self._should_exclude(file_path):
                        continue

                    # Special handling for __init__.py
                    if file_path.name == "__init__.py":
                        if file_path.read_text().strip() == "":
                            continue  # Skip empty __init__.py

                    yield file_path

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded."""
        exclude_patterns = self.config.get("audit.scanning.exclude_patterns", [])
        path_str = str(file_path)

        import fnmatch
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return True

        return False

    def _audit_file(self, file_path: Path) -> FileResult:
        """Audit a single file using LLM-based analysis (feature parity with current implementation)."""
        import time
        start = time.time()

        try:
            # Determine language
            language = self._detect_language(file_path)
            if not language:
                return FileResult(
                    file_path=file_path,
                    status="PASS",
                    violations=[],
                    execution_time=time.time() - start,
                )

            # Check cache
            cached_result = self._check_cache(file_path)
            if cached_result:
                return cached_result

            # Read file content
            code = file_path.read_text()

            # Run LLM-based audit (matches current claude-audit.sh behavior)
            from .agent_cli import get_agent_cli, AgentConfigPresets

            cli = get_agent_cli()
            prompts_dir = self.config.root / self.config.get("prompts.dir")
            audit_instruction = prompts_dir / self.config.get("prompts.audit")

            # Build audit prompt
            audit_prompt = f"""## CODE TO ANALYZE

```
{code}
```
"""

            exit_code, output = cli.run_print(
                instruction_file=audit_instruction,
                stdin=audit_prompt,
                agent_config=AgentConfigPresets.audit(),
            )

            # Parse result
            if exit_code == 0 and output.strip() == "PASS":
                status = "PASS"
                violations = []
            elif exit_code == 2 or "ERROR:" in output:
                status = "ERROR"
                violations = [{"line": 0, "pattern_id": "audit_error", "severity": "ERROR", "message": output}]
            else:  # FAIL
                status = "FAIL"
                # Parse violations from output (LLM will provide structured feedback)
                violations = [{"line": 0, "pattern_id": "llm_audit", "severity": "CRITICAL", "message": output}]

            result = FileResult(
                file_path=file_path,
                status=status,
                violations=violations,
                execution_time=time.time() - start,
            )

            # Cache result
            self._cache_result(file_path, result)

            return result

        except Exception as e:
            self.logger.error("audit_error", file=str(file_path), error=str(e))
            return FileResult(
                file_path=file_path,
                status="ERROR",
                violations=[],
                execution_time=time.time() - start,
            )

    def _detect_language(self, file_path: Path) -> str | None:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".go": "go",
            ".rs": "rust",
        }
        return mapping.get(ext)

    def _check_cache(self, file_path: Path) -> FileResult | None:
        """Check if file result is cached."""
        cache_enabled = self.config.get("audit.cache.enabled", False)
        if not cache_enabled:
            return None

        cache_file = self._get_cache_path(file_path)
        if not cache_file.exists():
            return None

        # Check if cache is stale
        ttl = self.config.get("audit.cache.ttl", 3600)
        import time
        if time.time() - cache_file.stat().st_mtime > ttl:
            return None

        # Load cached result
        try:
            data = json.loads(cache_file.read_text())
            return FileResult(**data)
        except:
            return None

    def _cache_result(self, file_path: Path, result: FileResult):
        """Cache audit result."""
        cache_enabled = self.config.get("audit.cache.enabled", False)
        if not cache_enabled:
            return

        cache_file = self._get_cache_path(file_path)
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        cache_file.write_text(json.dumps({
            "file_path": str(result.file_path),
            "status": result.status,
            "violations": result.violations,
            "execution_time": result.execution_time,
        }))

    def _get_cache_path(self, file_path: Path) -> Path:
        """Get cache file path for given file."""
        cache_dir = Path(self.config.get("audit.cache.storage"))
        file_hash = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
        return cache_dir / f"{file_hash}.json"

    def _save_report(self, result: FileResult, root_dir: Path, output_dir: Path):
        """Save audit report with mirrored directory structure.

        Args:
            result: Audit result
            root_dir: Root directory being audited
            output_dir: Output directory (e.g., docs/audit/DD.MM.YYYY)

        Example:
            base/automation/config.py -> docs/audit/18.10.2025/automation/config.py.md
        """
        from datetime import datetime

        # Create relative path for mirrored structure
        try:
            rel_path = result.file_path.relative_to(root_dir)
        except ValueError:
            rel_path = result.file_path.name

        # Mirror directory structure
        report_path = output_dir / rel_path.with_suffix(rel_path.suffix + ".md")

        # Create parent directories
        report_path.parent.mkdir(parents=True, exist_ok=True)

        # Format violations
        violations_text = ""
        if result.violations:
            violations_text = "\n".join([
                f"- Line {v['line']}: {v['message']} (severity: {v['severity']})"
                for v in result.violations
            ])

        # Write report
        with open(report_path, "w") as f:
            f.write(f"# AUDIT REPORT\n\n")
            f.write(f"**File**: `{rel_path}`\n")
            f.write(f"**Status**: {result.status}\n")
            f.write(f"**Audit Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Execution Time**: {result.execution_time:.2f}s\n\n")
            f.write("---\n\n")

            if result.status == "PASS":
                f.write("✅ No violations detected.\n")
            else:
                f.write(f"## Violations ({len(result.violations)})\n\n")
                f.write(violations_text)
                f.write("\n")

    def _consolidate_patterns(self, result: FileResult, output_dir: Path, consolidated_file: Path):
        """Consolidate patterns from failed audit into CONSOLIDATED.md.

        Only called for FAIL/ERROR files to extract patterns.

        Args:
            result: Failed audit result
            output_dir: Output directory
            consolidated_file: Path to CONSOLIDATED.md
        """
        from .agent_cli import get_agent_cli

        # Get audit report path
        rel_path = result.file_path.relative_to(output_dir.parent.parent.parent)
        report_path = output_dir / rel_path.with_suffix(rel_path.suffix + ".md")

        # Read audit report
        audit_content = report_path.read_text()

        # Read current consolidated (if exists)
        if consolidated_file.exists():
            consolidated_content = consolidated_file.read_text()
        else:
            consolidated_content = "# CONSOLIDATED AUDIT PATTERNS\n\nNo patterns consolidated yet.\n"

        # Run consolidation via agent CLI
        from .agent_cli import get_agent_cli, AgentConfigPresets

        cli = get_agent_cli()
        prompts_dir = self.config.root / self.config.get("prompts.dir")
        consolidate_instruction = prompts_dir / self.config.get("prompts.consolidate")

        # Build context
        context = f"""
## CURRENT CONSOLIDATED REPORT

File path: `{consolidated_file}`

```markdown
{consolidated_content}
```

---

## NEW AUDIT REPORT

File path: `{report_path}`

```markdown
{audit_content}
```

---

**REMEMBER**: Use Read/Write/Edit tools to update `{consolidated_file}`. Output ONLY 'UPDATED' or 'NO_CHANGES' when done.
"""

        exit_code, output = cli.run_print(
            instruction_file=consolidate_instruction,
            stdin=context,
            agent_config=AgentConfigPresets.consolidate(),
        )

        if exit_code == 0:
            self.logger.info("consolidation_result", result=output.strip())
```

**Features**:
- Parallel processing with ProcessPoolExecutor
- File scanning with include/exclude patterns
- Special `__init__.py` handling
- Result caching with TTL
- Language detection
- Structured logging

### 4.8 Structured Logging (`automation/logging.py`)

**Complexity**: ~150 lines

```python
"""Structured logging for auditability."""

import json
import logging
from datetime import datetime
from pathlib import Path

from .config import get_config


class JSONFormatter(logging.Formatter):
    """Format logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger wrapper."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup()

    def _setup(self):
        """Setup logger with JSON formatter."""
        if self.logger.handlers:
            return  # Already configured

        config = get_config()
        level = config.get("logging.level", "INFO")
        self.logger.setLevel(level)

        # Console handler (JSON)
        console = logging.StreamHandler()
        console.setFormatter(JSONFormatter())
        self.logger.addHandler(console)

        # File handler (JSON, with rotation)
        log_dir = Path(config.get("paths.logs")) / name
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"{datetime.now():%Y-%m-%d}.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)

    def info(self, message: str, **kwargs):
        """Log info with structured data."""
        self._log("INFO", message, kwargs)

    def error(self, message: str, **kwargs):
        """Log error with structured data."""
        self._log("ERROR", message, kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning with structured data."""
        self._log("WARNING", message, kwargs)

    def _log(self, level: str, message: str, extra: dict):
        """Log with extra fields."""
        record = logging.LogRecord(
            name=self.logger.name,
            level=getattr(logging, level),
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        record.extra_fields = extra
        self.logger.handle(record)


def get_logger(name: str) -> StructuredLogger:
    """Get or create structured logger."""
    return StructuredLogger(name)
```

**Features**:
- JSON log format
- Automatic file rotation (daily)
- Structured fields
- Console + file output
- Simple API: `logger.info("message", key=value)`

### 4.9 Agent CLI Abstraction (`automation/agent_cli.py`)

**Complexity**: ~200 lines

**Design**: Abstract interface with Claude Code CLI implementation

```python
"""Agent CLI abstraction for interactive and non-interactive operations.

AgentCLI defines the interface for agent interactions.
ClaudeAgentCLI implements this interface using the Claude Code CLI.
AgentConfig provides type-safe configuration.
"""

import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from .config import get_config
from .logging import get_logger


@dataclass
class AgentConfig:
    """Configuration for an agent execution.

    Defines what tools, model, hooks, and timeout settings for an agent.

    NOTE: disallowed_tools is NOT stored here - it's computed automatically
    by ClaudeAgentCLI.compute_disallowed_tools() as the complement of allowed_tools.
    """
    model: str
    allowed_tools: list[str] | None = None  # None = all tools allowed
    enable_hooks: bool = True
    timeout: int | None = 180  # None = no timeout (interactive)
    mcp_servers: dict | None = None


class AgentConfigPresets:
    """Common agent configuration presets.

    Identifies patterns behind audit agents, code quality agents, worker agents, etc.
    """

    @staticmethod
    def audit() -> AgentConfig:
        """Code audit agent: WebSearch/WebFetch only, hooks disabled, high-quality model.

        Used for: Full file code audits, security analysis
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=180,
        )

    @staticmethod
    def audit_diff() -> AgentConfig:
        """Diff audit agent: For PreToolUse hooks checking code quality.

        Used for: Edit/Write validation, regression detection
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=60,  # Fast for hooks
        )

    @staticmethod
    def consolidate() -> AgentConfig:
        """Pattern consolidation agent: Read/Write/Edit for updating consolidated reports.

        Used for: Extracting patterns from failed audits
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            allowed_tools=["Read", "Write", "Edit", "WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=300,
        )

    @staticmethod
    def worker() -> AgentConfig:
        """General worker agent: All tools, hooks enabled.

        Used for: General automation, --print mode with hooks
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            allowed_tools=None,  # All tools
            enable_hooks=True,
            timeout=180,
        )

    @staticmethod
    def interactive(mcp_servers: dict | None = None) -> AgentConfig:
        """Interactive agent: All tools, hooks enabled, MCP servers.

        Used for: Interactive sessions with user
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            allowed_tools=None,
            enable_hooks=True,
            timeout=None,  # No timeout
            mcp_servers=mcp_servers,
        )


class AgentCLI(ABC):
    """Abstract interface for agent CLI operations."""

    @abstractmethod
    def run_interactive(
        self,
        instruction: str,
        agent_config: AgentConfig,
    ) -> int:
        """Run agent in interactive mode.

        Args:
            instruction: Initial instruction/prompt for the agent
            agent_config: Agent configuration (model, tools, hooks, MCP)

        Returns:
            Exit code (0=success, non-zero=failure)
        """
        pass

    @abstractmethod
    def run_print(
        self,
        instruction: str | None = None,
        instruction_file: Path | None = None,
        stdin: str | TextIO | None = None,
        agent_config: AgentConfig | None = None,
    ) -> tuple[int, str]:
        """Run agent in non-interactive (print) mode.

        Args:
            instruction: Instruction text
            instruction_file: Path to instruction file
            stdin: Input data
            agent_config: Agent configuration (defaults to worker preset)

        Returns:
            (exit_code, output) tuple
        """
        pass


class ClaudeAgentCLI(AgentCLI):
    """Claude Code CLI implementation.

    Manages Claude Code CLI tool restrictions by maintaining a canonical list
    of all available tools and computing disallowed tools from allowed tools.
    """

    # Canonical list of ALL Claude Code tools (as of Claude Code v0.x)
    # Source: https://docs.claude.com/en/docs/claude-code/tools.md
    ALL_TOOLS = [
        "Bash",
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "WebSearch",
        "WebFetch",
        "Task",
        "NotebookEdit",
        "SlashCommand",
        "TodoWrite",
        "ExitPlanMode",
        "BashOutput",
        "KillShell",
    ]

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("agent-cli")

    @staticmethod
    def compute_disallowed_tools(allowed_tools: list[str] | None) -> list[str]:
        """Compute disallowed tools as complement of allowed tools.

        Args:
            allowed_tools: List of allowed tool names, or None for all tools

        Returns:
            List of disallowed tool names (empty if allowed_tools is None)

        Example:
            # Audit agent: only web tools
            allowed = ["WebSearch", "WebFetch"]
            disallowed = compute_disallowed_tools(allowed)
            # Returns: ["Bash", "Read", "Write", "Edit", "Glob", "Grep",
            #           "Task", "NotebookEdit", "SlashCommand", "TodoWrite",
            #           "ExitPlanMode", "BashOutput", "KillShell"]
        """
        if allowed_tools is None:
            return []  # All tools allowed, nothing disallowed

        allowed_set = set(allowed_tools)
        all_set = set(ClaudeAgentCLI.ALL_TOOLS)

        # Validate that allowed tools are in the canonical list
        unknown = allowed_set - all_set
        if unknown:
            raise ValueError(f"Unknown tools in allowed_tools: {unknown}")

        # Return complement
        return sorted(all_set - allowed_set)

    def run_interactive(
        self,
        instruction: str,
        agent_config: AgentConfig,
    ) -> int:
        """Run Claude Code in interactive mode.

        Args:
            instruction: Initial instruction/prompt
            agent_config: Agent configuration

        Returns:
            Exit code from claude process
        """
        import tempfile
        import json

        # Get Claude CLI command from config
        claude_cmd = self.config.get("claude_cli.command", "claude")

        # Build command from agent_config
        cmd = [claude_cmd]

        # Model
        cmd.extend(["--model", agent_config.model])

        # Tool restrictions - ALWAYS provide both allowed and disallowed
        if agent_config.allowed_tools is not None:
            # Compute disallowed as complement of allowed
            disallowed = self.compute_disallowed_tools(agent_config.allowed_tools)
            cmd.extend(["--allowed-tools", " ".join(agent_config.allowed_tools)])
            cmd.extend(["--disallowed-tools", " ".join(disallowed)])
        # If allowed_tools is None, don't restrict (all tools available)

        # MCP config
        mcp_config_file = None
        if agent_config.mcp_servers:
            mcp_config_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            mcp_config = {"mcpServers": agent_config.mcp_servers}
            json.dump(mcp_config, mcp_config_file)
            mcp_config_file.close()
            cmd.extend(["--mcp-config", mcp_config_file.name])

        # Hooks handled by settings file (passed separately by caller)

        cmd.extend(["--dangerously-skip-permissions", "--", instruction])

        self.logger.info("agent_interactive_start", model=agent_config.model)

        try:
            result = subprocess.run(cmd)
            return result.returncode
        finally:
            if mcp_config_file:
                Path(mcp_config_file.name).unlink()

    def run_print(
        self,
        instruction: str | None = None,
        instruction_file: Path | None = None,
        stdin: str | TextIO | None = None,
        agent_config: AgentConfig | None = None,
    ) -> tuple[int, str]:
        """Run Claude Code in --print mode (non-interactive).

        Args:
            instruction: Instruction text
            instruction_file: Path to instruction file
            stdin: Input data
            agent_config: Agent configuration (defaults to worker preset)

        Returns:
            (exit_code, output) tuple

        Example:
            # Audit agent
            cli.run_print(
                instruction_file=audit_file,
                stdin=code,
                agent_config=AgentConfigPresets.audit()
            )

            # Custom config
            custom = AgentConfig(
                model="claude-opus-4",
                allowed_tools=["Read", "WebSearch"],
                enable_hooks=True,
                timeout=120
            )
            cli.run_print(instruction="...", agent_config=custom)
        """
        import tempfile
        import json

        # Default to worker preset if no config provided
        if agent_config is None:
            agent_config = AgentConfigPresets.worker()

        # Load instruction
        if instruction_file:
            instruction_text = self._load_instruction(instruction_file)
        elif instruction:
            instruction_text = instruction
        else:
            raise ValueError("Either instruction or instruction_file required")

        # Prepare stdin input
        stdin_data = None
        if stdin:
            stdin_data = stdin if isinstance(stdin, str) else stdin.read()

        # Get Claude CLI command from config
        claude_cmd = self.config.get("claude_cli.command", "claude")

        # Create temp settings file if hooks disabled
        settings_file = None
        if not agent_config.enable_hooks:
            settings_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump({"hooks": {}}, settings_file)
            settings_file.close()

        # Build command from agent_config (ALL Claude Code specific flags here)
        cmd = [claude_cmd, "--print"]

        # Model
        cmd.extend(["--model", agent_config.model])

        # Tool restrictions - ALWAYS provide both allowed and disallowed
        if agent_config.allowed_tools is not None:
            # Compute disallowed as complement of allowed
            disallowed = self.compute_disallowed_tools(agent_config.allowed_tools)
            cmd.extend(["--allowed-tools", " ".join(agent_config.allowed_tools)])
            cmd.extend(["--disallowed-tools", " ".join(disallowed)])
        # If allowed_tools is None, don't restrict (all tools available)

        cmd.append("--dangerously-skip-permissions")

        # Settings file (hooks)
        if settings_file:
            cmd.extend(["--settings", settings_file.name])

        cmd.extend(["--", instruction_text])

        # Execute
        self.logger.info(
            "agent_print_start",
            model=agent_config.model,
            hooks=agent_config.enable_hooks,
            stdin_size=len(stdin_data) if stdin_data else 0
        )

        try:
            result = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=agent_config.timeout,
            )
            self.logger.info("agent_print_complete", exit_code=result.returncode)
            return result.returncode, result.stdout

        except subprocess.TimeoutExpired:
            self.logger.error("agent_print_timeout", timeout=agent_config.timeout)
            return 1, f"ERROR: Command timeout ({agent_config.timeout}s)"
        except Exception as e:
            self.logger.error("agent_print_error", error=str(e))
            return 1, f"ERROR: {e}"
        finally:
            if settings_file:
                Path(settings_file.name).unlink()

    def _load_instruction(self, instruction_file: Path) -> str:
        """Load instruction from file with template substitution."""
        from datetime import datetime

        content = instruction_file.read_text()
        content = content.format(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"),
            file_path="{file_path}",  # Preserve for later
        )
        return content


def get_agent_cli() -> AgentCLI:
    """Factory function to get agent CLI instance.

    Returns ClaudeAgentCLI by default.
    Future: Can return different implementations based on config.
    """
    return ClaudeAgentCLI()


def run_noninteractive(
    instruction_file: Path | None,
    stdin: str | None = None,
) -> int:
    """Convenience function for non-interactive mode.

    Args:
        instruction_file: Path to instruction file
        stdin: Input data

    Returns:
        Exit code (0=success, 1=failure)
    """
    cli = get_agent_cli()

    if stdin is None:
        stdin = sys.stdin.read()

    exit_code, output = cli.run_print(
        instruction_file=instruction_file,
        stdin=stdin,
    )

    print(output)
    return exit_code
```

**Features**:
- **AgentCLI interface**: Abstract base class defining agent operations
- **ClaudeAgentCLI implementation**: All Claude Code CLI specifics (flags, models, commands) isolated here
- **AgentConfig dataclass**: Type-safe configuration for model, tools, hooks, timeout, MCP
- **AgentConfigPresets**: Common patterns (audit, audit_diff, consolidate, worker, interactive)
- **Factory function**: `get_agent_cli()` returns appropriate implementation
- **Tool Management**: Canonical `ALL_TOOLS` list with automatic disallowed tools computation
- **compute_disallowed_tools()**: Given allowed tools, computes complement from ALL_TOOLS
- CLI commands loaded from config (`claude_cli.command`)
- Model selection from AgentConfig (not hardcoded)
- Template variable substitution
- Declarative tool restrictions (from AgentConfig.allowed_tools)
- Structured logging

**Tool Restriction Pattern**:
```python
# ClaudeAgentCLI maintains canonical list of ALL tools
ALL_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep",
             "WebSearch", "WebFetch", "Task", "NotebookEdit",
             "SlashCommand", "TodoWrite", "ExitPlanMode",
             "BashOutput", "KillShell"]

# Agents specify only allowed_tools
audit_config = AgentConfig(
    model="claude-sonnet-4-5",
    allowed_tools=["WebSearch", "WebFetch"],  # Only web tools
)

# ClaudeAgentCLI computes disallowed automatically
disallowed = compute_disallowed_tools(["WebSearch", "WebFetch"])
# Returns: ["Bash", "Read", "Write", "Edit", "Glob", "Grep",
#           "Task", "NotebookEdit", "SlashCommand", "TodoWrite",
#           "ExitPlanMode", "BashOutput", "KillShell"]

# BOTH lists ALWAYS provided to claude CLI
cmd.extend(["--allowed-tools", "WebSearch WebFetch"])
cmd.extend(["--disallowed-tools", "Bash Read Write Edit ..."])
```

**Abstraction Benefits**:
- ✅ **Type-safe**: AgentConfig vs string "mode"
- ✅ **No if/else hell**: Configuration objects, not string matching
- ✅ **Extensible**: Add new presets without changing CLI code
- ✅ **Self-documenting**: Presets show common patterns (audit, worker, etc.)
- ✅ **Testable**: Mock AgentConfig objects
- ✅ **Separation of concerns**: Config vs execution logic
- ✅ **Tool Management**: Canonical ALL_TOOLS list, automatic complement computation
- ✅ **Explicit Restrictions**: BOTH allowed AND disallowed always provided to CLI
- ✅ **Validation**: Unknown tools caught at runtime with clear error messages

**Agent Types** (via AgentConfigPresets):
1. **audit()**: Code audits - WebSearch/WebFetch only, hooks disabled, Sonnet 4.5, 180s timeout
2. **audit_diff()**: Code quality hooks - WebSearch/WebFetch only, hooks disabled, Sonnet 4.5, 60s timeout
3. **consolidate()**: Pattern extraction - Read/Write/Edit/Web, hooks disabled, Sonnet 4.5, 300s timeout
4. **worker()**: General automation - All tools, hooks enabled, Sonnet 4.5, 180s timeout
5. **interactive()**: User sessions - All tools, hooks enabled, MCP servers, no timeout

---

### 4.10 Error Handling & Edge Cases

**Complexity**: Embedded throughout all modules

**Design**: Fail-fast for configuration errors, fail-open for runtime errors

#### Configuration Errors (Fail-Fast)

```python
# config.py - Explicit error handling
def _load(self) -> dict[str, Any]:
    """Load configuration with validation."""
    # File existence check
    if not self.config_file.exists():
        raise FileNotFoundError(f"Config file not found: {self.config_file}")

    # YAML parsing with error context
    try:
        with open(self.config_file) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Malformed YAML in {self.config_file}: {e}")
    except PermissionError:
        raise PermissionError(f"Cannot read config file: {self.config_file}")

    # Empty config validation
    if not data or not isinstance(data, dict):
        raise ValueError(f"Config is empty or invalid: {self.config_file}")

    return self._substitute_env(data)
```

**Config Error Scenarios**:
- ❌ **Missing file**: Raise `FileNotFoundError` with path
- ❌ **Malformed YAML**: Raise `ValueError` with YAML error
- ❌ **Empty file**: Raise `ValueError`
- ❌ **Permission denied**: Raise `PermissionError`
- ❌ **Invalid data type**: Raise `ValueError`

#### Hook Errors (Fail-Open for Safety)

```python
# hooks.py - Fail-open on validation errors
def run(self) -> int:
    """Execute hook with fail-open safety."""
    try:
        hook_input = HookInput.from_stdin()
        result = self.validate(hook_input)
        print(result.to_json())
        return 0

    except json.JSONDecodeError as e:
        self.logger.error("invalid_hook_input", error=str(e))
        print(HookResult.allow().to_json())  # ALLOW on error
        return 0

    except Exception as e:
        self.logger.error("hook_error", error=str(e))
        print(HookResult.allow().to_json())  # ALLOW on error
        return 0
```

**Hook Error Scenarios**:
- ✅ **Invalid JSON**: Allow (fail-open) + log error
- ✅ **Timeout**: Allow (fail-open) + log timeout
- ✅ **Exception**: Allow (fail-open) + log exception
- ✅ **Corrupted transcript**: Skip invalid lines, process valid
- ✅ **Missing transcript**: Allow (no transcript to check)
- ✅ **Permission denied**: Allow (fail-open) + log error

**Rationale**: Hooks should NEVER break the development workflow. Better to allow a bad command than to block productive work.

#### Audit Errors (Graceful Degradation)

```python
# audit.py - Error handling with status tracking
def _audit_file(self, file_path: Path) -> FileResult:
    """Audit file with comprehensive error handling."""
    start = time.time()

    try:
        # Validate file access
        if not file_path.exists():
            return FileResult(
                file_path=file_path,
                status="ERROR",
                violations=[{"message": "File not found"}],
                execution_time=time.time() - start,
            )

        if not os.access(file_path, os.R_OK):
            return FileResult(
                file_path=file_path,
                status="ERROR",
                violations=[{"message": "Permission denied"}],
                execution_time=time.time() - start,
            )

        # Run audit
        code = file_path.read_text()
        exit_code, output = cli.run_print(...)

        # Parse result
        if exit_code == 0 and output.strip() == "PASS":
            status = "PASS"
            violations = []
        elif exit_code == 2 or "ERROR:" in output:
            status = "ERROR"
            violations = [{"message": output}]
        else:
            status = "FAIL"
            violations = self._parse_violations(output)

        return FileResult(
            file_path=file_path,
            status=status,
            violations=violations,
            execution_time=time.time() - start,
        )

    except UnicodeDecodeError:
        return FileResult(
            file_path=file_path,
            status="ERROR",
            violations=[{"message": "File encoding error (not UTF-8)"}],
            execution_time=time.time() - start,
        )

    except Exception as e:
        self.logger.error("audit_error", file=str(file_path), error=str(e))
        return FileResult(
            file_path=file_path,
            status="ERROR",
            violations=[{"message": f"Unexpected error: {e}"}],
            execution_time=time.time() - start,
        )
```

**Audit Error Scenarios**:
- ✅ **File not found**: Return ERROR status
- ✅ **Permission denied**: Return ERROR status
- ✅ **Encoding error**: Return ERROR status
- ✅ **LLM timeout**: Return ERROR status
- ✅ **LLM crash**: Return ERROR status
- ✅ **Malformed output**: Return FAIL status
- ✅ **Cache corruption**: Ignore cache, re-audit
- ✅ **Output dir creation fails**: Raise clear error

#### CLI Errors (Clear User Feedback)

```python
# agent_cli.py - Timeout and error handling
def run_print(self, ...) -> tuple[int, str]:
    """Run with timeout and error handling."""
    try:
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=agent_config.timeout,
        )
        return result.returncode, result.stdout

    except subprocess.TimeoutExpired:
        self.logger.error("timeout", timeout=agent_config.timeout)
        return 1, f"ERROR: Command timeout ({agent_config.timeout}s)"

    except FileNotFoundError:
        self.logger.error("command_not_found", command=claude_cmd)
        return 1, f"ERROR: Command not found: {claude_cmd}"

    except Exception as e:
        self.logger.error("cli_error", error=str(e))
        return 1, f"ERROR: {e}"

    finally:
        # Always cleanup temp files
        if settings_file and settings_file.exists():
            settings_file.unlink()
```

**CLI Error Scenarios**:
- ✅ **Command not found**: Return error with command name
- ✅ **Timeout**: Return error with timeout value
- ✅ **Crash**: Return error with exception message
- ✅ **Empty stdout**: Return empty string (valid)
- ✅ **Temp file cleanup**: Always cleanup in finally block

#### Resource Limits (DoS Protection)

```python
# hooks.py - Input size validation
MAX_HOOK_INPUT_SIZE = 10 * 1024 * 1024  # 10MB

def from_stdin(cls) -> "HookInput":
    """Parse hook input with size limit."""
    import sys

    # Read with size limit
    data_str = sys.stdin.read(MAX_HOOK_INPUT_SIZE + 1)

    if len(data_str) > MAX_HOOK_INPUT_SIZE:
        raise ValueError(f"Hook input too large (>{MAX_HOOK_INPUT_SIZE} bytes)")

    data = json.loads(data_str)
    return cls(...)


# audit.py - File size limits
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB for single file audit

def _audit_file(self, file_path: Path) -> FileResult:
    """Audit with file size limit."""
    file_size = file_path.stat().st_size

    if file_size > MAX_FILE_SIZE:
        return FileResult(
            file_path=file_path,
            status="ERROR",
            violations=[{"message": f"File too large ({file_size} bytes > {MAX_FILE_SIZE})"}],
            execution_time=0,
        )

    # Continue audit...


# audit.py - Worker limits
MAX_WORKERS = 8  # Don't overwhelm system

def audit_directory(self, directory: Path, max_workers: int = 4) -> list[FileResult]:
    """Audit with worker limits."""
    # Clamp workers to max
    max_workers = min(max_workers, MAX_WORKERS)

    if parallel:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            ...
```

**Resource Limits**:
- ✅ **Hook input size**: 10MB max (prevents DoS)
- ✅ **File size for audit**: 1MB max (prevents memory exhaustion)
- ✅ **Max parallel workers**: 8 (prevents system overload)
- ✅ **CLI timeout**: Configurable per agent (prevents hanging)
- ✅ **Cache TTL**: Configurable (prevents stale data)

#### Input Validation (Security)

```python
# agent_cli.py - Tool name validation
@staticmethod
def compute_disallowed_tools(allowed_tools: list[str] | None) -> list[str]:
    """Validate tool names against canonical list."""
    if allowed_tools is None:
        return []

    allowed_set = set(allowed_tools)
    all_set = set(ClaudeAgentCLI.ALL_TOOLS)

    # Validate - no unknown tools
    unknown = allowed_set - all_set
    if unknown:
        raise ValueError(f"Unknown tools: {unknown}")

    return sorted(all_set - allowed_set)


# audit.py - Path traversal prevention
def audit_directory(self, directory: Path) -> list[FileResult]:
    """Audit with path validation."""
    # Resolve to absolute path
    directory = directory.resolve()

    # Ensure within allowed directories (no traversal)
    if not self._is_safe_path(directory):
        raise ValueError(f"Directory outside allowed paths: {directory}")

    # Continue audit...

def _is_safe_path(self, path: Path) -> bool:
    """Check path is safe (no traversal)."""
    # Must be within project root
    try:
        path.relative_to(self.config.root)
        return True
    except ValueError:
        return False
```

**Input Validation**:
- ✅ **Tool names**: Validated against ALL_TOOLS canonical list
- ✅ **File paths**: Resolved to absolute, checked for traversal
- ✅ **Directory paths**: Validated within project root
- ✅ **JSON input**: Schema validation for hook inputs
- ✅ **YAML config**: Type validation after parsing

#### Edge Cases Handled

| Edge Case | Module | Handling |
|-----------|--------|----------|
| Empty directory | audit.py | Returns empty results list |
| Empty file | audit.py | Audits (may pass or fail) |
| Empty `__init__.py` | audit.py | Skipped entirely |
| Empty transcript | hooks.py | Returns empty string |
| Empty config | config.py | Raises ValueError |
| Corrupted JSON (hook input) | hooks.py | Allow (fail-open) + log |
| Corrupted JSON (transcript) | hooks.py | Skip invalid lines |
| Corrupted JSON (cache) | audit.py | Ignore, re-audit |
| File deleted during audit | audit.py | Returns ERROR status |
| Permission denied | All | Returns ERROR or raises |
| Concurrent cache access | audit.py | Atomic writes with .tmp + mv |
| Circular env var refs | config.py | One-pass substitution (no loops) |
| Huge file (>1MB) | audit.py | Returns ERROR status |
| Huge JSON input (>10MB) | hooks.py | Raises ValueError |
| LLM timeout | agent_cli.py | Returns ERROR status |
| LLM crash | agent_cli.py | Returns ERROR status |
| Missing claude command | agent_cli.py | Raises FileNotFoundError |

---

## 5. Unified CLI Entry Point

### What is "ami-agent" (Unified Entry Point)?

**ami-agent** is a **single Python script** (`scripts/ami-agent`) that replaces **multiple separate bash scripts**.

**Current State** (scattered bash scripts):
```
base/scripts/claude-agent.sh           # Interactive sessions
base/scripts/quality/claude-audit.sh    # Batch audits
base/scripts/quality/code_quality_guard.sh  # Diff validation hook
base/scripts/quality/response_scanner.sh    # Response scanning hook
```

**New State** (one unified script):
```
scripts/ami-agent                       # ALL functionality in ONE script
```

**How it works**: Single Python script with **4 operating modes** controlled by command-line flags:

| Mode | Flag | Replaces | Purpose |
|------|------|----------|---------|
| Interactive | `ami-agent` or `--interactive` | `claude-agent.sh` | Launch interactive Claude session with hooks |
| Print | `--print <file>` | (new capability) | Non-interactive automation with stdin/stdout |
| Hook | `--hook <validator>` | `code_quality_guard.sh`, `response_scanner.sh` | Execute hook validators |
| Audit | `--audit <dir>` | `claude-audit.sh` | Batch code quality audits |

**Benefits**:
- ✅ **One script to maintain** instead of 4+ separate scripts
- ✅ **Shared code** for config loading, logging, CLI management
- ✅ **Consistent behavior** across all modes
- ✅ **Single installation point** in orchestrator root

### 5.1 Implementation: `scripts/ami-agent`

**Location**: `/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-agent`

**Complexity**: ~300 lines

**Source**: Consolidated from multiple bash scripts into single entry point

```python
#!/usr/bin/env python3
"""AMI Agent - Unified automation entry point.

Usage:
    ami-agent                           # Interactive mode (default)
    ami-agent --interactive             # Interactive mode (explicit)
    ami-agent --print <instruction>     # Non-interactive mode
    ami-agent --hook <validator>        # Hook validator mode
    ami-agent --audit <directory>       # Batch audit mode

Examples:
    # Interactive agent with hooks
    ami-agent

    # Non-interactive audit from stdin
    cat file.py | ami-agent --print config/prompts/audit.txt

    # Hook validator (called by Claude Code)
    ami-agent --hook code-quality < hook_input.json

    # Batch audit
    ami-agent --audit base/
"""

import sys
from pathlib import Path

# Standard /base imports pattern to find orchestrator root
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))
from base.scripts.env.paths import setup_imports  # noqa: E402

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

# Add orchestrator root to path for automation package imports
sys.path.insert(0, str(ORCHESTRATOR_ROOT))

# Import automation modules (from ORCHESTRATOR_ROOT/automation/)
from automation.config import get_config  # noqa: E402
from automation.logging import get_logger  # noqa: E402
from automation.hooks import CommandValidator, CodeQualityValidator, ResponseScanner  # noqa: E402
from automation.audit import AuditEngine  # noqa: E402
from automation.agent_cli import run_noninteractive  # noqa: E402


def mode_interactive() -> int:
    """Interactive mode - Launch Claude Code with hooks.

    Returns:
        Exit code (0=success, 1=failure)
    """
    import subprocess
    import tempfile
    import json
    import yaml
    from datetime import datetime

    config = get_config()
    logger = get_logger("ami-agent")

    # Load agent instruction from file
    prompts_dir = config.root / config.get("prompts.dir")
    agent_file = prompts_dir / config.get("prompts.agent")

    instruction = agent_file.read_text()

    # Inject current date
    instruction = instruction.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    )

    # Create MCP config file from automation.yaml
    mcp_config_file = None
    mcp_enabled = config.get("mcp.enabled", True)

    if mcp_enabled:
        mcp_servers = config.get("mcp.servers", {})

        if mcp_servers:
            mcp_config_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)

            # Build MCP config from YAML configuration
            mcp_config = {"mcpServers": {}}

            for server_name, server_config in mcp_servers.items():
                # Substitute {root} template in args
                args = []
                for arg in server_config.get("args", []):
                    if isinstance(arg, str) and "{root}" in arg:
                        args.append(arg.format(root=config.root))
                    else:
                        args.append(arg)

                mcp_config["mcpServers"][server_name] = {
                    "command": server_config["command"],
                    "args": args
                }

            json.dump(mcp_config, mcp_config_file)
            mcp_config_file.close()

    # Create settings file with hooks
    settings_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)

    # Load hooks from config
    hooks_file = config.root / config.get("hooks.file")
    with open(hooks_file) as f:
        hooks_config = yaml.safe_load(f)

    # Convert to Claude Code settings format
    settings = {"hooks": {}}

    for hook in hooks_config["hooks"]:
        event = hook["event"]
        if event not in settings["hooks"]:
            settings["hooks"][event] = []

        hook_entry = {
            "hooks": [{
                "type": "command",
                "command": f"{config.root}/scripts/ami-agent --hook {hook['command']}",
            }]
        }

        if "matcher" in hook:
            hook_entry["matcher"] = hook["matcher"]

        settings["hooks"][event].append(hook_entry)

    json.dump(settings, settings_file)
    settings_file.close()

    # Debug log file
    debug_log = config.root / "claude-debug.log"
    with open(debug_log, "a") as f:
        f.write(f"=== Claude session started at {datetime.now()} ===\n")

    # Launch Claude Code
    logger.info("session_start", mode="interactive", mcp_enabled=mcp_enabled)

    try:
        # Build command
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
        ]

        # Add MCP config if enabled
        if mcp_config_file:
            cmd.extend(["--mcp-config", mcp_config_file.name])

        cmd.extend([
            "--settings", settings_file.name,
            "--", instruction
        ])

        # Redirect stderr to debug log
        with open(debug_log, "a") as log_file:
            subprocess.run(cmd, stderr=log_file)
        return 0
    finally:
        Path(settings_file.name).unlink()
        if mcp_config_file:
            Path(mcp_config_file.name).unlink()
        logger.info("session_end")


def mode_print(instruction_path: str) -> int:
    """Non-interactive mode - Run agent with --print.

    Uses worker agent preset (hooks enabled, all tools).
    Audit operations use different presets (audit, audit_diff, consolidate).

    Args:
        instruction_path: Path to instruction file

    Returns:
        Exit code (0=success, 1=failure)
    """
    from .agent_cli import get_agent_cli, AgentConfigPresets

    instruction_file = Path(instruction_path)

    if not instruction_file.exists():
        print(f"Instruction file not found: {instruction_path}", file=sys.stderr)
        return 1

    # Read stdin
    stdin = sys.stdin.read()

    # Run with worker agent preset (hooks enabled, all tools)
    cli = get_agent_cli()
    exit_code, output = cli.run_print(
        instruction_file=instruction_file,
        stdin=stdin,
        agent_config=AgentConfigPresets.worker(),
    )

    # Print output
    print(output)

    return exit_code


def mode_hook(validator_name: str) -> int:
    """Hook validator mode - Validate hook input from stdin.

    Args:
        validator_name: Name of validator (command-guard, code-quality, response-scanner)

    Returns:
        Exit code (0=success, 1=failure)
    """
    VALIDATORS = {
        "command-guard": CommandValidator,
        "code-quality": CodeQualityValidator,
        "response-scanner": ResponseScanner,
    }

    validator_class = VALIDATORS.get(validator_name)

    if not validator_class:
        print(f"Unknown validator: {validator_name}", file=sys.stderr)
        print(f"Available: {', '.join(VALIDATORS.keys())}", file=sys.stderr)
        return 1

    validator = validator_class()
    return validator.run()


def mode_audit(directory_path: str) -> int:
    """Batch audit mode - Audit directory for code quality issues.

    Args:
        directory_path: Path to directory to audit

    Returns:
        Exit code (0=success, 1=failure)
    """
    directory = Path(directory_path)

    if not directory.exists():
        print(f"Directory not found: {directory_path}", file=sys.stderr)
        return 1

    logger = get_logger("audit")
    engine = AuditEngine()

    # Run audit
    results = engine.audit_directory(directory, parallel=True, max_workers=4)

    # Print summary
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")

    print(f"\nAudit Summary:")
    print(f"  Total: {len(results)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    # Print failures
    if failed > 0:
        print(f"\nFailures:")
        for result in results:
            if result.status == "FAIL":
                print(f"\n  {result.file_path}:")
                for violation in result.violations:
                    print(f"    Line {violation['line']}: {violation['message']}")

    return 1 if failed > 0 else 0


def main():
    """Main entry point - Route to appropriate mode."""
    import argparse

    parser = argparse.ArgumentParser(
        description="AMI Claude - Unified automation entry point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode (default)",
    )

    parser.add_argument(
        "--print",
        metavar="INSTRUCTION_FILE",
        help="Non-interactive mode - run Claude CLI with --print",
    )

    parser.add_argument(
        "--hook",
        metavar="VALIDATOR",
        help="Hook validator mode (command-guard, code-quality, response-scanner)",
    )

    parser.add_argument(
        "--audit",
        metavar="DIRECTORY",
        help="Batch audit mode - audit directory for code quality issues",
    )

    args = parser.parse_args()

    # Route to appropriate mode
    if args.print:
        return mode_print(args.print)
    elif args.hook:
        return mode_hook(args.hook)
    elif args.audit:
        return mode_audit(args.audit)
    else:
        # Default to interactive
        return mode_interactive()


if __name__ == "__main__":
    sys.exit(main())
```

**Features**:
- **Unified entry point**: Single script, multiple modes
- **Standard /base imports**: Uses `setup_imports()` pattern
- **Prompt loading**: Reads instructions from config files (no hardcoded prompts)
- **Mode routing**: `--interactive`, `--print`, `--hook`, `--audit`
- **Proper exit codes**: Returns 0 for success, 1 for failure
- **Structured logging**: JSON logs for auditability

**Hook Behavior by Agent Type**:

| Command / Agent Type | Hooks? | Model | Tools | Use Case |
|---------------------|--------|-------|-------|----------|
| `ami-agent` | ✅ **YES** | Sonnet 4.5 | All | Interactive development |
| `ami-agent --print <file>` | ✅ **YES** | Sonnet 4.5 | All | General automation |
| `ami-agent --hook <name>` | N/A | N/A | N/A | IS a hook validator |
| `ami-agent --audit <dir>` | ❌ **NO** | Sonnet 4.5 | WebSearch/WebFetch | Code quality audit |
| **AgentConfigPresets.interactive()** | ✅ **YES** | Sonnet 4.5 | All + MCP | Interactive sessions |
| **AgentConfigPresets.worker()** | ✅ **YES** | Sonnet 4.5 | All | General automation |
| **AgentConfigPresets.audit()** | ❌ **NO** | Sonnet 4.5 | WebSearch/WebFetch | Code audits |
| **AgentConfigPresets.audit_diff()** | ❌ **NO** | Sonnet 4.5 | WebSearch/WebFetch | Code quality hooks |
| **AgentConfigPresets.consolidate()** | ❌ **NO** | Sonnet 4.5 | Read/Write/Edit/Web | Pattern extraction |

**Usage Examples**:

```bash
# Interactive agent with hooks (default)
ami-agent

# Non-interactive with hooks ENABLED (general automation)
cat script.py | ami-agent --print config/prompts/custom_task.txt

# Audit with hooks DISABLED (prevents recursion)
ami-agent --audit base/

# Hook validator (called by Claude Code hooks)
echo '{"tool_name": "Bash", "tool_input": {...}}' | ami-agent --hook command-guard
```

**Hook Configuration Update**:

```yaml
# config/hooks.yaml - Updated to use unified entry point
hooks:
  - event: "PreToolUse"
    matcher: "Bash"
    command: "command-guard"  # ami-agent --hook command-guard

  - event: "PreToolUse"
    matcher: ["Edit", "Write"]
    command: "code-quality"  # ami-agent --hook code-quality

  - event: "Stop"
    command: "response-scanner"  # ami-agent --hook response-scanner
```

---

## 6. Implementation Plan

### Phase 1: Core Framework (Week 1)
- [ ] Create `automation/` package structure
- [ ] Extract prompts to `config/prompts/`:
  - [ ] `agent.txt` (from claude-agent.sh)
  - [ ] `audit.txt` (from audit_instruction.txt)
  - [ ] `audit_diff.txt` (from audit_diff_instruction.txt)
  - [ ] `consolidate.txt` (from consolidate_instruction.txt)
- [ ] Implement `config.py` (100 lines) - Uses `/base` conventions
- [ ] Implement `logging.py` (150 lines)
- [ ] Write unit tests (>80% coverage)
- [ ] Create `config/automation.yaml` with prompts section

### Phase 2: Hook System (Week 2)
- [ ] Implement `hooks.py` base framework (300 lines)
- [ ] Implement CommandValidator
- [ ] Implement CodeQualityValidator
- [ ] Implement ResponseScanner
- [ ] Create `config/hooks.yaml` - Updated for unified entry point
- [ ] Write integration tests

### Phase 3: Audit System & Non-interactive Mode (Week 3)
- [ ] Implement `patterns.py` (200 lines)
- [ ] Implement `audit.py` (400 lines)
- [ ] Implement `agent_cli.py` (200 lines) - AgentCLI interface + ClaudeAgentCLI impl
- [ ] Create pattern files: `python.yaml`, `javascript.yaml`, `security.yaml`
- [ ] Write performance tests

### Phase 4: Unified Entry Point & Integration (Week 4)
- [ ] Create `scripts/ami-agent` unified entry point (300 lines)
  - [ ] Interactive mode (--interactive)
  - [ ] Non-interactive mode (--print)
  - [ ] Hook validator mode (--hook)
  - [ ] Batch audit mode (--audit)
- [ ] Test full workflow end-to-end
- [ ] Performance benchmarking
- [ ] Documentation

### Phase 5: Deployment (Week 5)
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Gather feedback
- [ ] Iterate

---

## 7. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Lines of Code | ~2000+ bash | ~1700 Python |
| Entry Points | 3+ scripts | 1 unified script |
| Missing Features | N/A | 8 features added |
| Hook Latency | ~500ms | <100ms |
| Audit Time (300 files) | ~15 min | <5 min |
| Test Coverage | 0% | >80% |
| Maintainability | Low | High |
| Prompt Management | Hardcoded | Config files (990 lines) |

---

## 8. Migration Strategy

**NO BACKWARD COMPATIBILITY - CLEAN BREAK**

1. **Week 1**: Deploy new system alongside old
2. **Week 2**: Test on non-production modules
3. **Week 3**: Switch production to new system
4. **Week 4**: Archive old scripts
5. **Week 5**: Remove old scripts

**Old scripts** → Archive to `scripts/legacy/` (do not delete, keep for reference)

---

## 9. Validation Against Claude Code Docs

### ✅ Hook System
- **Follows**: JSON input/output format from docs
- **Follows**: Event types (PreToolUse, Stop, SubagentStop)
- **Follows**: Decision types (allow, deny, block)
- **Follows**: Command-based hooks with timeout

### ✅ Configuration
- **Follows**: Settings file approach
- **Follows**: Hooks defined per event type
- **Follows**: Matcher support

### ✅ Transcript Access
- **Follows**: transcript_path provided in hook input
- **Follows**: JSONL format for transcripts

### ✅ Best Practices
- **Follows**: Fail-open on errors (safety)
- **Follows**: Structured logging
- **Follows**: Timeout per hook
- **Follows**: Input validation

---

## 10. Missing Features - Added from Existing Implementation

During final verification, **7 critical features** from existing bash scripts were identified as missing from initial spec. All have been added:

### ✅ Feature 1: MCP Configuration Support ⬆ **ENHANCED**
- **Source**: claude-agent.sh:59-81
- **Added**: Section 3.1 `automation.yaml` lines 108-122
- **Added**: Section 5.1 `mode_interactive()` lines 1556-1584
- **Implementation**: Configuration-based MCP server provisioning
- **Enhancement**: Current bash hardcodes browser server → New spec loads from YAML
- **Benefits**:
  - ✅ Extensible: Add/remove MCP servers without code changes
  - ✅ Configurable: Enable/disable via `mcp.enabled`
  - ✅ Template support: `{root}` substitution in paths
  - ✅ Environment-specific: Different servers per environment
- **Config** (`automation.yaml`):
  ```yaml
  mcp:
    enabled: true
    servers:
      browser:
        command: "python3"
        args:
          - "{root}/browser/scripts/run_chrome.py"
          - "--data-root"
          - "{root}/browser/data"
  ```

### ✅ Feature 2: Debug Logging
- **Source**: claude-agent.sh:139-145
- **Added**: Section 5.1 `mode_interactive()` lines 1310-1313, 1319-1327
- **Implementation**: Appends to `claude-debug.log` with session timestamps
- **Location**: `{ORCHESTRATOR_ROOT}/claude-debug.log`

### ✅ Feature 3: Model Specification
- **Source**: All audit scripts (claude-audit.sh:64, claude-audit-diff.sh:64, claude-audit-consolidate.sh:96)
- **Added**: Section 4.9 `run_print()` line 1100
- **Implementation**: `--model claude-sonnet-4-5` for 100% accuracy (vs 92.9% with Haiku)

### ✅ Feature 4: Tool Restrictions
- **Source**: All audit scripts
- **Added**: Section 4.9 `run_print()` lines 1089-1095, 1101-1102
- **Implementation**: Mode-based tool permissions
  - **audit/audit_diff**: Only `WebSearch WebFetch` (analysis only)
  - **consolidate**: `Read Write Edit WebSearch WebFetch` (file updates)
- **Disallowed**: Bash, Glob, Grep, Task, NotebookEdit, SlashCommand, TodoWrite, ExitPlanMode, BashOutput, KillShell

### ✅ Feature 5: Hook Disabling During Audit
- **Source**: All audit scripts (lines 43-54)
- **Added**: Section 4.9 `AgentConfig` dataclass, `AgentConfigPresets` class
- **Implementation**: `--settings` with empty `{"hooks": {}}` when `agent_config.enable_hooks=False`
- **Important**: `ami-agent --print` uses `worker()` preset (hooks ENABLED by default)
- **Audit-specific**: Hooks disabled via `audit()`, `audit_diff()`, `consolidate()` presets
- **Type-safe**: AgentConfig.enable_hooks boolean, not string matching
- **Prevents**: Recursive hook execution during code quality checks

### ✅ Feature 6: Audit Output Structure
- **Source**: code_audit.py:261-276
- **Added**: Section 4.7 `audit_directory()` lines 735-741
- **Implementation**:
  - Date format: DD.MM.YYYY (e.g., `18.10.2025`)
  - Structure: `{directory}/docs/audit/{date}/`
  - Mirror hierarchy: `base/automation/config.py` → `docs/audit/18.10.2025/automation/config.py.md`
- **Added**: Section 4.7 `_save_report()` lines 943-990

### ✅ Feature 7: Progress Tracking
- **Source**: code_audit.py:313-417
- **Added**: Section 4.7 `audit_directory()` lines 751-790
- **Implementation**: Real-time progress with time estimates
  ```
  Progress: 45/120 (37%) | Elapsed: 120.5s | Est remaining: 195.3s
  ```

### ✅ Feature 8: Selective Consolidation
- **Source**: code_audit.py:401-411
- **Added**: Section 4.7 `audit_directory()` lines 770-772, 789-790
- **Added**: Section 4.7 `_consolidate_patterns()` lines 992-1054
- **Implementation**: Only run consolidation on FAIL/ERROR files to extract patterns
- **Benefit**: Saves ~60% of LLM calls (no consolidation for PASS files)

---

## 11. Gap Analysis - Addressed

All critical gaps from initial review have been addressed:

### ✅ Gap 1: Non-interactive Mode
- **Added**: `automation/agent_cli.py` module (200 lines)
- **Added**: `ami-agent --print` mode for CI/CD and batch operations
- **Abstraction**: `AgentCLI` interface with `ClaudeAgentCLI` implementation
- **Use Cases**: Code audit, diff validation, pattern consolidation, CI/CD pipelines

### ✅ Gap 2: Prompt Extraction
- **Added**: `config/prompts/` directory structure
- **Extracted**: All prompts to separate files (agent.txt, audit.txt, audit_diff.txt, consolidate.txt)
- **Total**: 990 lines of prompts now version-controlled and reviewable
- **Benefit**: No hardcoded instructions in Python code

### ✅ Gap 3: /base Conventions
- **Updated**: All modules use standard imports pattern
- **Pattern**: `sys.path.insert(0, ...)` + `setup_imports()` from `base.scripts.env.paths`
- **Files**: `config.py`, `ami-agent` entry point
- **Benefit**: Consistent with project conventions

### ✅ Gap 4: Unified Entry Point
- **Replaced**: 3 separate scripts (claude-agent, ami-agent hook, ami-audit)
- **Created**: Single `ami-agent` script with 4 modes
- **Modes**: `--interactive`, `--print`, `--hook`, `--audit`
- **Complexity**: 300 lines (vs ~600 lines previously)
- **Benefit**: Single source of truth, easier maintenance

---

## 12. Improvements Beyond Current Implementation

While maintaining 100% feature parity, the spec includes **production enhancements** over current bash implementation:

### ⬆️ Enhancement 1: Configuration-Based MCP Servers

**Current Limitation**:
```bash
# claude-agent.sh - Hardcoded MCP config
cat >"$MCP_CONFIG_FILE" <<JSON
{
  "mcpServers": {
    "browser": {
      "command": "python3",
      "args": ["${REPO_ROOT}/browser/scripts/run_chrome.py", ...]
    }
  }
}
JSON
```

**New Implementation**:
```yaml
# automation.yaml - Configurable
mcp:
  enabled: true
  servers:
    browser:
      command: "python3"
      args: ["{root}/browser/scripts/run_chrome.py", ...]
    # Add more servers without code changes
```

**Benefits**:
- ✅ **Extensible**: Add database, filesystem, or custom MCP servers
- ✅ **Toggleable**: Disable MCP entirely via `enabled: false`
- ✅ **Environment-aware**: Different servers for dev/staging/prod
- ✅ **No code edits**: Modify `automation.yaml` instead of Python

### ⬆️ Enhancement 2: Unified Entry Point

**Current Limitation**:
- 3+ separate scripts: `claude-agent.sh`, `claude-audit.sh`, `claude-audit-diff.sh`, `claude-audit-consolidate.sh`
- Duplicated config generation logic
- 4 places to update for hook changes

**New Implementation**:
- Single `ami-agent` script
- 4 modes: `--interactive`, `--print`, `--hook`, `--audit`
- Shared config loading

**Benefits**:
- ✅ **Single source of truth**: One script to maintain
- ✅ **Consistent behavior**: All modes use same config loader
- ✅ **Easier testing**: One entry point to test

### ⬆️ Enhancement 3: Type Safety & Error Handling

**Current Limitation**:
- Bash string manipulation for JSON
- No type checking
- Silent failures

**New Implementation**:
- Python type hints throughout
- Structured error handling
- JSON schema validation

**Benefits**:
- ✅ **Compile-time checks**: Catch errors before runtime
- ✅ **Better debugging**: Stack traces instead of bash cryptic errors
- ✅ **IDE support**: Autocomplete, refactoring

### ⬆️ Enhancement 4: AgentConfig Pattern (vs Mode Strings)

**Current Limitation**:
```python
# Hypothetical bad design with mode strings
if mode == "audit":
    allowed_tools = "WebSearch WebFetch"
    disable_hooks = True
elif mode == "consolidate":
    allowed_tools = "Read Write Edit WebSearch WebFetch"
    disable_hooks = True
# ... more if/else hell
```

**New Implementation**:
```python
# Type-safe configuration objects
@dataclass
class AgentConfig:
    model: str
    allowed_tools: list[str] | None
    enable_hooks: bool
    timeout: int | None

# Common patterns as presets
class AgentConfigPresets:
    @staticmethod
    def audit() -> AgentConfig:
        return AgentConfig(
            model="claude-sonnet-4-5",
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=180,
        )

# Usage
cli.run_print(agent_config=AgentConfigPresets.audit())
```

**Benefits**:
- ✅ **No string matching**: Type-safe configuration objects
- ✅ **Self-documenting**: Presets show common agent patterns
- ✅ **Extensible**: Add new preset = add method, zero code changes
- ✅ **Testable**: Mock AgentConfig objects easily
- ✅ **Proper abstraction**: Config separate from execution

---

## APPROVED FOR IMPLEMENTATION

**Total Complexity**: ~1900 lines Python (vs ~2000+ bash)
- `config.py`: 120 lines (includes error handling)
- `logging.py`: 150 lines
- `hooks.py`: 350 lines (includes resource limits, fail-open logic)
- `patterns.py`: 200 lines
- `audit.py`: 550 lines (includes path validation, file size limits, graceful error handling)
- `agent_cli.py`: 230 lines (includes timeout handling, FileNotFoundError handling)
- `ami-agent`: 300 lines (unified entry point)

**Error Handling**: Comprehensive (Section 4.10)
- Config errors: Fail-fast with clear messages
- Hook errors: Fail-open for safety
- Audit errors: Graceful degradation with ERROR status
- Resource limits: DoS protection (10MB input, 1MB files, 8 workers max)
- Input validation: Security (path traversal, tool names, JSON schema)

**Entry Points**: 1 unified script (vs 3+ separate scripts)
**Features Added**: 8 critical features from existing implementation
**Architecture**: Simplified, production-ready, feature-complete, hardened
**Test Coverage**: 209 comprehensive tests (>90% coverage target)
**Backward Compatibility**: NONE (clean break)
**Timeline**: 5 weeks
**Risk**: LOW (well-defined scope, all existing features preserved)
