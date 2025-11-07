# Multi-CLI Provider Support

**Version**: 2.1.0
**Last Updated**: 2025-11-07

## Overview

AMI-ORCHESTRATOR now supports multiple AI CLI providers (Claude Code CLI and Gemini CLI) with a unified abstraction layer. This enables:

1. **Provider Selection**: Choose between Claude or Gemini for any agent task
2. **Mixed Workflows**: Use different providers for worker and moderator agents
3. **Tool Name Mapping**: Automatic translation between Claude (PascalCase) and Gemini (snake_case) tool names
4. **Backward Compatibility**: Existing code continues to work with no changes
5. **Automatic Installation**: Both CLIs auto-install on first run via `scripts/ami-agent`
6. **Automatic Authentication**: gcloud auth flow triggers automatically for Gemini

## Installation & Authentication

### Automatic Installation

The `scripts/ami-agent` wrapper automatically installs and configures everything needed:

**On first run:**
1. Installs Claude CLI (`@anthropic-ai/claude-code@2.0.10`) to `.venv/node_modules/`
2. Installs Gemini CLI (`@google/gemini-cli@0.11.3`) to `.venv/node_modules/`
3. Installs gcloud CLI to `.gcloud/google-cloud-sdk/` (local, not system-wide)
4. Triggers `gcloud auth application-default login` for Vertex AI authentication
5. Sets required environment variables (`GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_LOCATION=us-central1`)

**First run example:**

```bash
scripts/ami-agent

# Output:
# Claude CLI not found in venv, installing version 2.0.10...
# ✓ Successfully installed Claude CLI 2.0.10 to .venv/node_modules/
#
# Gemini CLI not found in venv, installing version 0.11.3...
# ✓ Successfully installed Gemini CLI 0.11.3 to .venv/node_modules/
#
# gcloud CLI not found, installing to .gcloud/...
# ✓ Successfully installed gcloud CLI
#
# ========================================
# Google Cloud Authentication Required
# ========================================
#
# Gemini CLI requires Google Cloud credentials.
# You will be directed to a web page to authenticate.
#
# Starting authentication flow...
#
# Go to the following link in your browser:
#   https://accounts.google.com/o/oauth2/auth?...
#
# ✓ Successfully authenticated with Google Cloud
#
# Warning: GOOGLE_CLOUD_PROJECT not set in environment
# Gemini CLI may fail without a project ID
# Set it in .env: GOOGLE_CLOUD_PROJECT=your-project-id
```

After authentication, credentials are cached at `~/.config/gcloud/application_default_credentials.json`. Subsequent runs skip the auth flow.

### Required Configuration

Add your Google Cloud project ID to `.env`:

```bash
# Google Cloud Configuration (required for Gemini CLI with Vertex AI)
GOOGLE_CLOUD_PROJECT=your-project-id  # Your GCP project ID
GOOGLE_CLOUD_LOCATION=us-central1     # Optional, defaults to us-central1
```

### What Gets Installed

All installations are local to AMI-ORCHESTRATOR (gitignored):

- **Claude CLI**: `.venv/node_modules/@anthropic-ai/claude-code/`
- **Gemini CLI**: `.venv/node_modules/@google/gemini-cli/`
- **gcloud SDK**: `.gcloud/google-cloud-sdk/`
- **Auth credentials**: `~/.config/gcloud/application_default_credentials.json` (user-wide)

No system-wide installations. Everything self-contained.

## Architecture

### Core Components

```
scripts/automation/agent_cli.py (1523 lines)
├── CLIProvider (enum)                    # CLAUDE, GEMINI
├── ClaudeModels (enum)                   # SONNET_4_5, SONNET_3_5, OPUS_4, HAIKU_3_5
├── GeminiModels (enum)                   # PRO_2_5, FLASH_2_5, PRO_2_0, FLASH_2_0
├── AgentConfig (dataclass)               # provider: CLIProvider (required)
├── AgentConfigPresets (static methods)   # All presets default to Claude
├── AgentCLI (abstract base)              # Interface for CLI operations
├── ClaudeAgentCLI (implementation)       # Claude Code CLI backend
├── GeminiAgentCLI (implementation)       # Gemini CLI backend
└── get_agent_cli() (factory)             # Returns appropriate CLI instance
```

### Provider Selection Priority

The `get_agent_cli()` factory selects providers in this order:

1. **Explicit provider parameter** (deprecated, kept for backward compat)
2. **agent_config.provider field** (primary method)
3. **Global config fallback** (`agent.provider` in automation.yaml)
4. **Default to Claude**

## Usage

### Basic Usage - Explicit Provider

```python
from scripts.automation.agent_cli import (
    AgentConfig,
    CLIProvider,
    ClaudeModels,
    GeminiModels,
    get_agent_cli,
)

# Create Claude agent
claude_config = AgentConfig(
    provider=CLIProvider.CLAUDE,
    model=ClaudeModels.SONNET_4_5.value,
    session_id="worker-123",
)
claude_cli = get_agent_cli(claude_config)

# Create Gemini agent
gemini_config = AgentConfig(
    provider=CLIProvider.GEMINI,
    model=GeminiModels.PRO_2_5.value,
    session_id="moderator-456",
)
gemini_cli = get_agent_cli(gemini_config)
```

### Using AgentConfigPresets

All presets default to Claude:

```python
from scripts.automation.agent_cli import AgentConfigPresets, get_agent_cli

# Use preset (defaults to Claude)
config = AgentConfigPresets.audit("audit-session-789")
cli = get_agent_cli(config)

# Override to use Gemini
config.provider = CLIProvider.GEMINI
config.model = GeminiModels.FLASH_2_5.value
cli = get_agent_cli(config)
```

### Mixed Provider Workflow

Use different providers for different roles:

```python
# Worker uses Claude for code generation
worker_config = AgentConfig(
    provider=CLIProvider.CLAUDE,
    model=ClaudeModels.SONNET_4_5.value,
    session_id="worker"
)
worker_cli = get_agent_cli(worker_config)

# Moderator uses Gemini for validation (faster)
moderator_config = AgentConfig(
    provider=CLIProvider.GEMINI,
    model=GeminiModels.FLASH_2_5.value,
    session_id="moderator"
)
moderator_cli = get_agent_cli(moderator_config)

# Execute workflow
worker_output, _ = worker_cli.run_print(instruction="...", agent_config=worker_config)
moderator_output, _ = moderator_cli.run_print(instruction="...", agent_config=moderator_config)
```

### Configurable Worker/Moderator Defaults

**NEW in v2.1**: Worker and moderator providers/models are now configurable via environment variables or `automation.yaml`.

#### Configuration via Environment Variables

```bash
# Use Gemini for moderators (faster validation), Claude for workers
export AMI_AGENT_MODERATOR_PROVIDER=gemini
export AMI_AGENT_MODERATOR_MODEL=gemini-2.5-flash

# Use Haiku for workers (cheaper)
export AMI_AGENT_WORKER_PROVIDER=claude
export AMI_AGENT_WORKER_MODEL=claude-haiku-3-5

# Run automation - moderators now use Gemini Flash, workers use Haiku
scripts/ami-run.sh scripts/automation/tasks.py
```

#### Configuration via automation.yaml

```yaml
agent:
  # Worker defaults (for task execution, code generation)
  worker:
    provider: "claude"  # claude or gemini
    model: "claude-sonnet-4-5"  # Empty = use provider's model_default

  # Moderator defaults (for validation, verification)
  moderator:
    provider: "gemini"  # claude or gemini
    model: "gemini-2.5-flash"  # Empty = use provider's model_default
```

#### Affected Presets

**Worker presets** (use `agent.worker` config):
- `AgentConfigPresets.worker()` - General worker agent
- `AgentConfigPresets.task_worker()` - Task execution worker
- `AgentConfigPresets.sync_worker()` - Git sync worker

**Moderator presets** (use `agent.moderator` config):
- `AgentConfigPresets.task_moderator()` - Task validation moderator
- `AgentConfigPresets.sync_moderator()` - Git sync moderator
- `AgentConfigPresets.completion_moderator()` - Completion validation moderator

**Other presets** (unaffected - use explicit defaults):
- `AgentConfigPresets.audit()` - Always uses Claude Sonnet 4.5
- `AgentConfigPresets.audit_diff()` - Always uses Claude Sonnet 4.5
- `AgentConfigPresets.consolidate()` - Always uses Claude Sonnet 4.5
- `AgentConfigPresets.interactive()` - Always uses Claude Sonnet 4.5

### Tool Name Mapping

Canonical tool names (Claude-style) are automatically mapped to provider-specific names:

```python
claude_cli = get_agent_cli(AgentConfigPresets.worker("test"))
gemini_cli = get_agent_cli(AgentConfig(
    provider=CLIProvider.GEMINI,
    model=GeminiModels.PRO_2_5.value,
    session_id="test"
))

# Claude uses canonical names (PascalCase)
assert claude_cli.map_tool_name("Read") == "Read"
assert claude_cli.map_tool_name("Write") == "Write"
assert claude_cli.map_tool_name("Bash") == "Bash"

# Gemini maps to snake_case
assert gemini_cli.map_tool_name("Read") == "read_file"
assert gemini_cli.map_tool_name("Write") == "write_file"
assert gemini_cli.map_tool_name("Bash") == "run_shell_command"
```

### Model Validation

Each provider has its own model enum with validation:

```python
from scripts.automation.agent_cli import ClaudeModels, GeminiModels

# Claude models
assert ClaudeModels.is_valid("claude-sonnet-4-5")
assert ClaudeModels.is_valid("claude-sonnet-3-5")
assert not ClaudeModels.is_valid("gemini-2.5-pro")

# Gemini models
assert GeminiModels.is_valid("gemini-2.5-pro")
assert GeminiModels.is_valid("gemini-2.5-flash")
assert not GeminiModels.is_valid("claude-sonnet-4-5")

# Get defaults from config
claude_default = ClaudeModels.get_default()  # "claude-sonnet-4-5"
gemini_default = GeminiModels.get_default()  # "gemini-2.5-pro"
```

## Configuration

Configuration is in `scripts/config/automation.yaml`:

```yaml
# Agent CLI settings (multi-provider support)
agent:
  provider: "claude"  # Default provider: claude or gemini

  # Claude Code CLI settings
  claude:
    command: "{root}/.venv/node_modules/.bin/claude"
    model_default: "claude-sonnet-4-5"
    model_audit: "claude-sonnet-4-5"

  # Gemini CLI settings
  gemini:
    command: "gemini"
    model_default: "gemini-2.5-pro"
    model_audit: "gemini-2.5-flash"
```

## Backward Compatibility

All existing code continues to work:

```python
# Old code (still works)
cli = get_agent_cli()  # Defaults to Claude via config

# All 11 existing call sites use this pattern:
# - validators.py: get_agent_cli()
# - hooks.py (3 locations): get_agent_cli()
# - docs.py: get_agent_cli()
# - sync.py: get_agent_cli()
# - agent_main.py (2 locations): get_agent_cli()
# - tasks.py: get_agent_cli()
# - audit.py (2 locations): get_agent_cli()
```

## Tool Name Mappings

| Canonical (Claude) | Gemini           | Description                    |
|--------------------|------------------|--------------------------------|
| `Read`             | `read_file`      | Read file contents             |
| `Write`            | `write_file`     | Write file contents            |
| `Edit`             | `edit`           | Edit file with find/replace    |
| `Bash`             | `run_shell_command` | Execute shell command       |
| `Grep`             | `search_file_content` | Search file contents       |
| `Glob`             | `glob`           | Find files by pattern          |
| `WebSearch`        | `google_web_search` | Web search                  |
| `WebFetch`         | `web_fetch`      | Fetch web page                 |
| `TodoWrite`        | `write_todos`    | Write todo list                |

## Testing

### Unit Tests

```bash
# Run model enum tests
scripts/ami-run.sh -m pytest tests/unit/test_agent_cli.py::TestClaudeModels -xvs
scripts/ami-run.sh -m pytest tests/unit/test_agent_cli.py::TestGeminiModels -xvs

# Run multi-provider factory tests
scripts/ami-run.sh -m pytest tests/unit/test_agent_cli.py::TestMultiProviderFactory -xvs

# Run GeminiAgentCLI tests
scripts/ami-run.sh -m pytest tests/unit/test_agent_cli.py::TestGeminiAgentCLI -xvs
```

### Integration Tests

```bash
# Run full multi-provider workflow tests
scripts/ami-run.sh -m pytest tests/integration/test_multi_provider_e2e.py -xvs
```

## Implementation Details

### AgentConfig Structure

```python
@dataclass
class AgentConfig:
    provider: CLIProvider          # Required - determines CLI backend
    model: str                      # Model name (must be valid for provider)
    session_id: str                 # Session ID for logging
    allowed_tools: list[str] | None = None
    enable_hooks: bool = True
    enable_streaming: bool = False
    timeout: int | None = 180
    mcp_servers: dict[str, Any] | None = None
```

### Provider-Specific Implementation Details

**Claude Code CLI** (`ClaudeAgentCLI`):
- Command: `claude --print --model {model} -- {instruction}`
- Tool names: PascalCase (canonical)
- Output format: Plain text or streaming JSON
- Streaming: `--output-format stream-json --verbose`

**Gemini CLI** (`GeminiAgentCLI`):
- Command: `gemini --prompt {instruction} --model {model} --output-format json --yolo`
- Tool names: snake_case
- Output format: JSON with response and stats
- Streaming: Not yet implemented

## Migration Guide

### Existing Code (No Changes Required)

```python
# This continues to work unchanged
cli = get_agent_cli()
config = AgentConfigPresets.worker("session-123")
output, metadata = cli.run_print(instruction="...", agent_config=config)
```

### Opt-In to Multi-Provider

To use Gemini for specific tasks:

```python
# Create Gemini config
config = AgentConfig(
    provider=CLIProvider.GEMINI,
    model=GeminiModels.PRO_2_5.value,
    session_id="gemini-session"
)

# Get Gemini CLI
cli = get_agent_cli(config)

# Run task
output, metadata = cli.run_print(instruction="...", agent_config=config)
```

## See Also

- **Unit Tests**: `tests/unit/test_agent_cli.py` (444 lines, 35+ tests)
- **Integration Tests**: `tests/integration/test_multi_provider_e2e.py` (12 tests)
- **Configuration**: `scripts/config/automation.yaml`
- **Implementation**: `scripts/automation/agent_cli.py` (1523 lines)
