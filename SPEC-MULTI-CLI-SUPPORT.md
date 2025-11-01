# Multi-CLI Support Specification

**Version:** 1.0.0
**Date:** 2025-11-01
**Status:** DRAFT

## Executive Summary

This specification defines the architecture for supporting multiple AI CLI agents (Claude CLI, Gemini CLI, and future CLIs) within the AMI-ORCHESTRATOR automation infrastructure. The goal is to enable seamless switching between CLI backends while maintaining a unified automation API.

## Current Architecture

### Components

**1. `scripts/ami-agent`** (Bash wrapper)
- Bootstraps and version-checks Claude CLI
- Finds Claude binary (env → venv → system PATH)
- Installs Claude CLI via npm if missing
- Executes `scripts/automation/agent_main.py`

**2. `scripts/automation/agent_main.py`** (Python entry point)
- Provides automation modes: `--interactive`, `--print`, `--audit`, `--tasks`, `--sync`, `--docs`
- Calls `get_agent_cli()` factory for non-interactive modes
- **HARDCODES** Claude CLI command for interactive mode (line 193)

**3. `scripts/automation/agent_cli.py`** (CLI abstraction layer)
- `AgentCLI` abstract base class
- `ClaudeAgentCLI` implementation
- `get_agent_cli()` factory (returns hardcoded `ClaudeAgentCLI()`)
- Tool restrictions, hooks, settings file management
- Streaming execution with metadata tracking

**4. `module_setup.py`** (Dependency management)
- `ensure_claude_version()` - checks/installs Claude CLI
- `bootstrap_node_in_venv()` - installs Node.js+npm via nodeenv

**5. `scripts/config/automation.yaml`** (Configuration)
- `claude_cli.command`, `claude_cli.model_default`, `claude_cli.model_audit`
- MCP server configurations
- Prompt file paths

## CLI Comparison

### Claude CLI

**Package:** `@anthropic-ai/claude-code@2.0.10`
**Command:** `claude`
**Node Requirement:** >=18.0.0

#### Headless Mode
```bash
# Text output (printed to Claude CLI)
echo "prompt" | claude

# Non-interactive with explicit instruction file
claude --print < instruction.txt
```

#### Key Features
- Settings file: `~/.claude/settings.json`
- MCP config: `--mcp-config <file>`
- Hooks: `--settings <file>` with hooks configuration
- Model selection: via API key/settings (not CLI flag)
- **NO `--output-format json` flag** - outputs plain text only
- Tool names: `Read`, `Write`, `Edit`, `Bash`, `WebFetch`, `WebSearch`, `Glob`, `Grep`, etc.

#### Settings File Format (Claude)
```json
{
  "hooks": {
    "userPromptSubmit": ["command", "arg"],
    "toolUse": ["command", "arg"]
  }
}
```

### Gemini CLI

**Package:** `@google/gemini-cli@0.11.3`
**Command:** `gemini`
**Node Requirement:** >=20.0.0

#### Headless Mode
```bash
# Text output (default)
gemini --prompt "What is 2+2?"

# JSON output
gemini --prompt "query" --output-format json

# Streaming JSON output (JSONL)
gemini --prompt "query" --output-format stream-json

# Stdin input
echo "Explain this code" | gemini
```

#### Key Features
- Settings file: `~/.gemini/settings.json`
- MCP servers: Configured in settings.json `mcpServers` section
- Model selection: `--model` or `-m` flag (e.g., `gemini-2.5-pro`, `gemini-2.5-flash`)
- Approval mode: `--approval-mode auto_edit` or `--yolo`
- Tool names: `read_file`, `write_file`, `edit`, `run_shell_command`, `web_fetch`, `google_web_search`, `save_memory`, `write_todos`, `read_many_files`, `list_directory`, `glob`, `search_file_content`

#### JSON Output Structure (Gemini)
```json
{
  "response": "string",
  "stats": {
    "models": {
      "gemini-2.5-pro": {
        "api": {"totalRequests": 2, "totalErrors": 0, "totalLatencyMs": 5053},
        "tokens": {"prompt": 24939, "candidates": 20, "total": 25113, "cached": 21263}
      }
    },
    "tools": {
      "totalCalls": 1,
      "totalSuccess": 1,
      "totalFail": 0,
      "byName": {"google_web_search": {"count": 1, "success": 1}}
    },
    "files": {
      "totalLinesAdded": 0,
      "totalLinesRemoved": 0
    }
  },
  "error": null
}
```

#### Settings File Format (Gemini)
```json
{
  "mcpServers": {
    "browser": {
      "command": "ami-run",
      "args": ["/path/to/script.py", "--data-root", "/path/to/data"]
    }
  },
  "autoAccept": false,
  "coreTools": ["read_file", "write_file", "run_shell_command(git)"],
  "excludeTools": ["run_shell_command(rm)"]
}
```

### Key Differences

| Feature | Claude CLI | Gemini CLI |
|---------|-----------|------------|
| **JSON Output** | ❌ No | ✅ Yes (`--output-format json`) |
| **Model Flag** | ❌ No (via API) | ✅ Yes (`--model`) |
| **Settings File** | `~/.claude/settings.json` | `~/.gemini/settings.json` |
| **MCP Config** | External file via `--mcp-config` | Embedded in settings.json |
| **Hooks** | Settings file `hooks` section | Not documented |
| **Tool Names** | PascalCase (`Read`, `Write`, `Bash`) | snake_case (`read_file`, `write_file`, `run_shell_command`) |
| **Approval Mode** | Via settings/prompts | `--approval-mode` or `--yolo` flags |
| **Streaming Output** | Text only | ✅ JSONL (`--output-format stream-json`) |
| **Interactive Mode** | Default | Default |

## Proposed Architecture

### 1. Enum: `CLIAgentType`

```python
from enum import Enum

class CLIAgentType(Enum):
    CLAUDE = "claude"
    GEMINI = "gemini"
```

### 2. Abstract Base Class: `AgentCLI`

**Location:** `scripts/automation/agent_cli.py`

```python
class AgentCLI(ABC):
    """Abstract base class for CLI agents."""

    ALL_TOOLS: list[str]  # Class attribute: tool names for this CLI

    @abstractmethod
    def _build_command(
        self,
        instruction_file: Path,
        agent_config: AgentConfig,
        stdin_data: str | None = None,
        cwd: Path | None = None,
    ) -> list[str]:
        """Build CLI command with all arguments."""
        pass

    @abstractmethod
    def _create_settings_file(self, agent_config: AgentConfig) -> Path:
        """Create CLI-specific settings file (hooks, MCP, etc)."""
        pass

    def run_print(
        self,
        instruction_file: Path,
        stdin: str,
        agent_config: AgentConfig,
        cwd: Path | None = None,
    ) -> tuple[str, dict | None]:
        """Execute CLI in headless mode. Returns (output, metadata)."""
        pass

    def run_interactive(
        self,
        instruction: str,
        continue_session: bool = False,
        resume: str | bool | None = None,
        fork_session: bool = False,
    ) -> int:
        """Launch CLI in interactive mode."""
        pass
```

### 3. Implementation: `ClaudeAgentCLI`

**Location:** `scripts/automation/agent_cli.py` (existing, minimal changes)

```python
class ClaudeAgentCLI(AgentCLI):
    """Claude CLI implementation."""

    ALL_TOOLS = ["Read", "Write", "Edit", "Bash", "WebFetch", "WebSearch",
                 "Glob", "Grep", "NotebookEdit", "SlashCommand", "Task",
                 "TodoWrite", "BashOutput", "KillShell"]

    def __init__(self):
        self.cli_type = CLIAgentType.CLAUDE
        self.command = get_config().get("claude_cli.command", "claude")
        self.logger = get_logger("claude-agent-cli")

    def _build_command(self, instruction_file, agent_config, stdin_data, cwd):
        """Build Claude CLI command."""
        cmd = [self.command]

        # Claude uses --print for non-interactive mode (no --output-format)
        if agent_config.enable_streaming:
            # Claude doesn't support JSON streaming - use text
            pass

        # Settings file (contains hooks)
        settings_file = self._create_settings_file(agent_config)
        cmd.extend(["--settings", str(settings_file)])

        # MCP config (external file)
        if agent_config.mcp_enabled:
            mcp_file = self._create_mcp_config_file()
            cmd.extend(["--mcp-config", str(mcp_file)])

        # Instruction passed via stdin (current behavior)
        cmd.append("--print")

        return cmd

    def _create_settings_file(self, agent_config):
        """Create ~/.claude/settings.json with hooks."""
        # Existing implementation
        pass

    def run_print(self, instruction_file, stdin, agent_config, cwd):
        """Execute Claude CLI in headless mode."""
        # Returns (text_output, None) - Claude has no metadata
        pass
```

### 4. Implementation: `GeminiAgentCLI`

**Location:** `scripts/automation/agent_cli.py` (NEW)

```python
class GeminiAgentCLI(AgentCLI):
    """Gemini CLI implementation."""

    ALL_TOOLS = ["read_file", "write_file", "edit", "list_directory", "glob",
                 "search_file_content", "run_shell_command", "web_fetch",
                 "google_web_search", "save_memory", "write_todos", "read_many_files"]

    def __init__(self):
        self.cli_type = CLIAgentType.GEMINI
        self.command = get_config().get("gemini_cli.command", "gemini")
        self.model = get_config().get("gemini_cli.model", "gemini-2.5-pro")
        self.logger = get_logger("gemini-agent-cli")

    def _build_command(self, instruction_file, agent_config, stdin_data, cwd):
        """Build Gemini CLI command."""
        cmd = [self.command]

        # Model selection
        cmd.extend(["--model", self.model])

        # JSON output for automation
        if agent_config.enable_streaming:
            cmd.extend(["--output-format", "stream-json"])
        else:
            cmd.extend(["--output-format", "json"])

        # Approval mode
        if agent_config.tool_auto_approve:
            cmd.append("--yolo")

        # Settings file (contains MCP servers, tool restrictions)
        settings_file = self._create_settings_file(agent_config)
        cmd.extend(["--settings", str(settings_file)])

        # Prompt from instruction file
        instruction_text = instruction_file.read_text()
        cmd.extend(["--prompt", instruction_text])

        return cmd

    def _create_settings_file(self, agent_config):
        """Create ~/.gemini/settings.json with MCP and tool restrictions."""
        config = get_config()
        settings = {}

        # MCP servers (embedded in settings)
        if agent_config.mcp_enabled:
            mcp_servers = config.get("mcp.servers", {})
            if mcp_servers:
                settings["mcpServers"] = {}
                for name, server_config in mcp_servers.items():
                    # Substitute {root} template
                    args = [
                        arg.format(root=config.root) if "{root}" in arg else arg
                        for arg in server_config.get("args", [])
                    ]
                    settings["mcpServers"][name] = {
                        "command": server_config["command"],
                        "args": args,
                    }

        # Tool restrictions
        if agent_config.allowed_tools:
            # Map Claude tool names to Gemini tool names
            gemini_tools = self._map_tools_to_gemini(agent_config.allowed_tools)
            settings["coreTools"] = gemini_tools

        if agent_config.blocked_tools:
            gemini_blocked = self._map_tools_to_gemini(agent_config.blocked_tools)
            settings["excludeTools"] = gemini_blocked

        # Auto-accept (YOLO mode)
        settings["autoAccept"] = agent_config.tool_auto_approve

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(settings, f, indent=2)
            return Path(f.name)

    def _map_tools_to_gemini(self, claude_tools: list[str]) -> list[str]:
        """Map Claude tool names to Gemini tool names."""
        mapping = {
            "Read": "read_file",
            "Write": "write_file",
            "Edit": "edit",
            "Bash": "run_shell_command",
            "WebFetch": "web_fetch",
            "WebSearch": "google_web_search",
            "Glob": "glob",
            "Grep": "search_file_content",
            # Add more mappings as needed
        }
        return [mapping.get(tool, tool) for tool in claude_tools]

    def run_print(self, instruction_file, stdin, agent_config, cwd):
        """Execute Gemini CLI in headless mode."""
        cmd = self._build_command(instruction_file, agent_config, stdin, cwd)

        # Execute command
        result = subprocess.run(
            cmd,
            input=stdin,
            capture_output=True,
            text=True,
            cwd=cwd,
        )

        if result.returncode != 0:
            raise AgentExecutionError(result.returncode, result.stdout, result.stderr, cmd)

        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            output = data.get("response", "")
            metadata = {
                "stats": data.get("stats", {}),
                "error": data.get("error"),
            }
            return (output, metadata)
        except json.JSONDecodeError:
            # Fallback: treat as plain text
            return (result.stdout, None)
```

### 5. Factory Function: `get_agent_cli()`

**Location:** `scripts/automation/agent_cli.py`

```python
def get_agent_cli(cli_type: CLIAgentType | None = None) -> AgentCLI:
    """Factory function to get agent CLI instance.

    Args:
        cli_type: CLI type to instantiate. If None, read from config.

    Returns:
        AgentCLI implementation (ClaudeAgentCLI or GeminiAgentCLI)
    """
    if cli_type is None:
        config = get_config()
        cli_type_str = config.get("cli_agent.type", "claude")
        cli_type = CLIAgentType(cli_type_str)

    if cli_type == CLIAgentType.CLAUDE:
        return ClaudeAgentCLI()
    elif cli_type == CLIAgentType.GEMINI:
        return GeminiAgentCLI()
    else:
        raise ValueError(f"Unknown CLI type: {cli_type}")
```

### 6. Configuration Updates

**File:** `scripts/config/automation.yaml`

```yaml
# CLI Agent Configuration
cli_agent:
  type: "claude"  # Options: "claude", "gemini"

# Claude CLI settings
claude_cli:
  command: "claude"
  model_default: "claude-sonnet-4-5"
  model_audit: "claude-sonnet-4-5"

# Gemini CLI settings
gemini_cli:
  command: "gemini"
  model: "gemini-2.5-pro"  # Options: gemini-2.5-pro, gemini-2.5-flash
  approval_mode: "auto_edit"  # Options: auto, auto_edit, manual

# MCP Servers (works with both CLIs)
mcp:
  enabled: true
  servers:
    browser:
      command: "ami-run"
      args:
        - "{root}/browser/scripts/run_chrome.py"
        - "--data-root"
        - "{root}/browser/data"
```

**File:** `.env`

```bash
# Claude CLI Configuration
CLAUDE_CLI_VERSION=2.0.10
CLAUDE_CLI_PATH=/custom/path/to/claude  # Optional override

# Gemini CLI Configuration
GEMINI_CLI_VERSION=0.11.3
GEMINI_CLI_PATH=/custom/path/to/gemini  # Optional override
```

### 7. Bootstrap Script Updates

**File:** `scripts/ami-agent`

```bash
#!/usr/bin/env bash
set -euo pipefail

# Load CLI versions from .env
CLAUDE_REQUIRED_VERSION="2.0.10"
GEMINI_REQUIRED_VERSION="0.11.3"
# ... (read from .env)

# Bootstrap Claude CLI (required - default)
find_claude_binary()
install_claude_cli()
check_claude_version()
# ... (existing logic)

# Bootstrap Gemini CLI (optional - warn only)
find_gemini_binary()
install_gemini_cli()
check_gemini_version()
# ... (warn if not found, don't exit)

# Execute Python automation
exec "$ROOT_DIR/.venv/bin/python" "$SCRIPT_DIR/automation/agent_main.py" "$@"
```

### 8. Module Setup Updates

**File:** `module_setup.py`

```python
def get_gemini_version(gemini_bin: str | None = None) -> str | None:
    """Get installed Gemini CLI version.

    Args:
        gemini_bin: Path to gemini binary. If None, uses 'gemini' from PATH.

    Returns:
        Version string (e.g., "0.11.3") or None if not found.
    """
    if gemini_bin is None:
        gemini_bin = shutil.which("gemini")

    if not gemini_bin:
        return None

    try:
        result = subprocess.run(
            [gemini_bin, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            # Extract version: "0.11.3" from output
            match = re.search(r'(\d+\.\d+\.\d+)', result.stdout)
            if match:
                return match.group(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def ensure_gemini_version(
    required_version: str,
    venv_path: Path | None = None,
    venv_npm: Path | None = None,
) -> bool:
    """Ensure Gemini CLI version is installed.

    Args:
        required_version: Required version string (e.g., "0.11.3")
        venv_path: Path to venv root (for local install)
        venv_npm: Path to venv npm binary

    Returns:
        True if version is installed, False on failure
    """
    if not check_npm(venv_npm):
        return False

    current_version = get_gemini_version()

    if current_version == required_version:
        logger.info(f"✓ Gemini CLI version {required_version} is installed")
        return True

    if current_version:
        logger.warning(f"Gemini CLI version {current_version} found, but {required_version} is required")
        logger.info(f"Updating to Gemini CLI {required_version}...")
    else:
        logger.info(f"Gemini CLI not found. Installing version {required_version}...")

    # Install to venv
    install_cmd = [str(venv_npm), "install"]
    if venv_path:
        install_cmd.extend(["--prefix", str(venv_path)])
    else:
        install_cmd.append("-g")

    install_cmd.append(f"@google/gemini-cli@{required_version}")

    try:
        subprocess.run(install_cmd, check=True, capture_output=True, text=True)
        logger.info(f"✓ Successfully installed Gemini CLI {required_version}")

        # Verify installation
        if venv_path:
            gemini_bin = venv_path / "node_modules" / ".bin" / "gemini"
            if not gemini_bin.exists():
                logger.error(f"Installation verification failed: {gemini_bin} not found")
                return False
            installed_version = get_gemini_version(str(gemini_bin))
        else:
            installed_version = get_gemini_version()

        if installed_version != required_version:
            logger.error(f"Installation verification failed: got {installed_version}, expected {required_version}")
            return False

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install Gemini CLI {required_version}")
        logger.error(f"Error: {e.stderr if e.stderr else e}")
        return False
```

### 9. Interactive Mode Fix

**File:** `scripts/automation/agent_main.py` (line ~193)

**Current (BROKEN):**
```python
# Get Claude CLI command from config
claude_cmd = config.get("claude_cli.command", "claude")

cmd = [claude_cmd, ...]
```

**Fixed:**
```python
# Get CLI implementation from factory
cli = get_agent_cli()

# Use CLI-specific interactive launch
return cli.run_interactive(
    instruction=instruction,
    continue_session=continue_session,
    resume=resume,
    fork_session=fork_session,
)
```

## Tool Name Mapping

| Logical Operation | Claude CLI | Gemini CLI |
|-------------------|-----------|------------|
| Read file | `Read` | `read_file` |
| Write file | `Write` | `write_file` |
| Edit file | `Edit` | `edit` |
| List directory | `Read` (dir) | `list_directory` |
| Find files (glob) | `Glob` | `glob` |
| Search text (grep) | `Grep` | `search_file_content` |
| Run shell command | `Bash` | `run_shell_command` |
| Fetch web content | `WebFetch` | `web_fetch` |
| Search web | `WebSearch` | `google_web_search` |
| Save memory | N/A | `save_memory` |
| Manage todos | `TodoWrite` | `write_todos` |
| Read many files | N/A | `read_many_files` |

## Implementation Plan

### Phase 1: Foundation (No Code Changes Yet)
1. ✅ Read Gemini CLI documentation
2. ✅ Write this spec document
3. ⏳ Review spec with team/user
4. ⏳ Get approval to proceed

### Phase 2: Bootstrap & Infrastructure
1. Update `.env` with `GEMINI_CLI_VERSION`
2. Update `scripts/ami-agent` with Gemini bootstrap logic
3. Add `get_gemini_version()` to `module_setup.py`
4. Add `ensure_gemini_version()` to `module_setup.py`
5. Test bootstrap: `scripts/ami-agent --help` (should bootstrap both CLIs)

### Phase 3: CLI Abstraction Layer
1. Add `CLIAgentType` enum to `agent_cli.py`
2. Implement `GeminiAgentCLI` class (500 lines)
3. Update `get_agent_cli()` factory function
4. Add tool name mapping helpers
5. Write unit tests for `GeminiAgentCLI`

### Phase 4: Configuration
1. Update `automation.yaml` with `cli_agent.type` and `gemini_cli` section
2. Update config loading in `scripts/automation/config.py`
3. Test config validation

### Phase 5: Integration
1. Fix interactive mode in `agent_main.py` to use factory
2. Test all modes with Claude CLI (ensure no regression)
3. Test all modes with Gemini CLI (set `cli_agent.type: gemini`)
4. Compare outputs and fix discrepancies

### Phase 6: Testing & Documentation
1. Write integration tests for both CLIs
2. Test audit mode with both CLIs
3. Test task execution with both CLIs
4. Test sync mode with both CLIs
5. Test docs mode with both CLIs
6. Document CLI selection in README.md
7. Document differences and limitations

### Phase 7: Rollout
1. Create feature branch
2. Run full test suite
3. Create PR with spec + implementation
4. User review & testing
5. Merge to main

## Critical Limitation: No Hooks Support in Gemini CLI

**Status:** Confirmed via web search (2025-11-01)

Gemini CLI **does not support hooks** in current versions (v0.11.3). Hooks are a **feature request only**:
- Issue #2779 (filed July 2025): Basic hooks proposal
- Issue #9070 (filed September 2025): Comprehensive hooks system v1
- Status: Priority P2 ("Important but can be addressed in a future release")
- No implementation timeline provided
- Last update: October 14, 2025 (planning phase only)

### Impact on AMI Automation

Without hooks, Gemini CLI **cannot run our critical validators**:

| Validator | Purpose | Hook Required | Impact Without Hook |
|-----------|---------|---------------|---------------------|
| **command-guard** | Block dangerous bash commands | `userPromptSubmit`, `toolUse` | ❌ Can't block `rm -rf`, `git push --force`, etc. |
| **code-quality** | Validate code changes | `toolUse` (Edit, Write) | ❌ Can't enforce code quality standards |
| **response-scanner** | Check completion markers | `modelResponse` | ❌ Can't validate task completion |

### Limited Use Cases for Gemini CLI

**✅ Can Use (Read-Only Operations):**
- `--audit` mode - Read files and report issues (no blocking needed)
- `--docs` mode - Read codebase and suggest updates (moderation workflow)
- Read-only analysis tasks

**❌ Cannot Use (Write Operations):**
- `--interactive` mode - No way to block dangerous commands
- `--tasks` mode - Can't validate task completion
- `--sync` mode - Can't enforce commit message standards
- Any workflow requiring safety validation

## Open Questions

1. **Hooks Support Workaround?** - Could we wrap Gemini CLI with a validation proxy?
   - Intercept stdin/stdout to inject validation
   - Parse tool calls from JSON output, validate, then reject if needed
   - **Risk:** Fragile, depends on output format stability

2. **Alternative: Wait for Hooks?** - Should we defer Gemini CLI support until hooks are implemented?
   - P2 priority suggests 6-12 months timeline
   - **Risk:** Long wait, uncertain delivery

2. **Streaming Metadata** - How do we parse JSONL streaming output from Gemini?
   - **Answer:** Parse each line as JSON, accumulate stats, return final metadata

3. **MCP Server Compatibility** - Do Gemini and Claude use the same MCP protocol version?
   - **Answer:** Both support MCP, but may need testing for compatibility

4. **Model Selection** - How do we handle model selection differences?
   - **Claude:** Via API key/settings (user's account)
   - **Gemini:** Via `--model` flag
   - **Answer:** Abstract via `agent_config.model` field

5. **Error Handling** - Do both CLIs return the same exit codes?
   - **Answer:** Need to test and standardize error handling

## Success Criteria

**Gemini CLI (Limited - No Hooks):**
- [ ] `ami-agent --audit` works with Gemini CLI (read-only moderation)
- [ ] `ami-agent --docs` works with Gemini CLI (read-only analysis)
- [ ] Switching CLI via `automation.yaml` changes behavior
- [ ] Tool restrictions work correctly (via settings.json)
- [ ] MCP servers work with Gemini CLI
- [ ] Metadata tracking works (JSON output parsing)

**Claude CLI (Full Support):**
- [ ] `ami-agent --interactive` works with Claude CLI (with hooks)
- [ ] `ami-agent --print` works with Claude CLI (with hooks)
- [ ] `ami-agent --audit` works with Claude CLI
- [ ] `ami-agent --tasks` works with Claude CLI (with hooks)
- [ ] `ami-agent --sync` works with Claude CLI (with hooks)
- [ ] `ami-agent --docs` works with Claude CLI
- [ ] No regression in existing functionality
- [ ] All validators (command-guard, code-quality, response-scanner) work

**General:**
- [ ] Configuration system supports both CLIs
- [ ] Bootstrap logic works for both CLIs
- [ ] Error handling is consistent
- [ ] All tests pass with both CLI backends (within their capabilities)

## Risk Mitigation

1. **Backward Compatibility:** Keep Claude CLI as default, test exhaustively
2. **Feature Parity:** Document differences, gracefully degrade unsupported features
3. **Testing:** Write comprehensive integration tests before rollout
4. **Rollback Plan:** Feature flag (`cli_agent.type`) allows instant rollback

## Recommendations

### Option 1: Limited Gemini Support (Immediate)
**Scope:** Implement Gemini CLI for read-only moderation tasks only
- `--audit` mode ✅
- `--docs` mode ✅
- Block other modes with clear error message
- Document limitation in README

**Pros:**
- Quick to implement
- Provides value for moderation workflows
- No risk to safety-critical operations

**Cons:**
- Limited utility
- User confusion (why can't I use --tasks?)

### Option 2: Wait for Hooks (Deferred)
**Timeline:** 6-12 months (estimated based on P2 priority)
- Monitor GitHub issues #2779 and #9070
- Revisit when hooks are released
- Full implementation once hooks available

**Pros:**
- Complete feature parity when ready
- No workarounds or hacks
- Clean implementation

**Cons:**
- Long wait
- Uncertain timeline
- May never happen

### Option 3: Validation Proxy (Complex)
**Architecture:** Wrap Gemini CLI with validation middleware
- Parse `--output-format stream-json` events
- Intercept tool calls before execution
- Run validators, reject if needed
- Forward approved calls to Gemini

**Pros:**
- Full functionality today
- Can support any CLI without hooks

**Cons:**
- Complex engineering (2-3 weeks)
- Fragile (depends on JSON format)
- Performance overhead
- May break on Gemini updates

### Recommended Path: Option 1 (Limited Support)

Implement Gemini CLI for moderation tasks only, clearly document the limitation, and revisit when hooks are available. This provides immediate value without compromising safety.

## Future Extensions

1. **Full Gemini Support** - When hooks are released (track issues #2779, #9070)
2. **OpenAI CLI Support** - Add `OpenAIAgentCLI` implementation (check hooks support first)
3. **Custom CLI Support** - Allow users to define custom CLI adapters
4. **Multi-CLI Ensemble** - Run same task with multiple CLIs, compare outputs
5. **CLI Performance Benchmarking** - Track speed/cost/quality metrics per CLI
6. **Automatic CLI Selection** - Choose best CLI based on task type/cost

---

**WORK DONE**
