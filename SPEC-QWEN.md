# SPEC: Add Qwen CLI Support

## Overview

Add support for Qwen Code CLI as an alternative provider to the ami-agent system, alongside existing Claude Code CLI support.

## Requirements

### 1. QwenProvider Implementation
- Create `QwenAgentCLI` class implementing the `AgentCLI` interface
- Support Qwen Code CLI commands and arguments
- Handle Qwen-specific tool mappings and command formats

### 2. Tool Name Mapping
Qwen Code CLI uses different tool names than Claude Code:
- Claude: `Read`, `Write`, `Edit`, `Bash` etc.
- Qwen: `read_file`, `write_file`, `edit`, `run_shell_command` etc.

### 3. Configuration Support
- Add Qwen provider to `CLIProvider` enum
- Add Qwen-specific configuration in `automation.yaml`
- Support model selection for Qwen provider

### 4. Factory Integration
- Update `get_agent_cli()` factory to return Qwen implementation when configured
- Support Qwen in all existing presets (audit, worker, moderator patterns)

### 5. Command Mapping
Map core commands from Claude format to Qwen format:
- `qwen [query..]` for interactive mode
- `qwen --prompt-interactive` for interactive with prompt
- `qwen --output-format stream-json` for streaming
- `qwen --yolo` for auto-approve mode

### 6. New Implementation Components

#### File: `scripts/agents/cli/qwen_cli.py`
- Implement `QwenAgentCLI` class
- Override `_build_command()` to create Qwen-specific CLI commands
- Handle Qwen-specific JSON streaming format
- Implement tool name translation logic

#### File: `scripts/agents/cli/base_provider.py`
- Add `Qwen` to `CLIProvider` enum
- Update tool mapping logic to support Qwen format

#### File: `scripts/agents/cli/config.py`
- Update `AgentConfig` and `AgentConfigPresets` to work with Qwen provider
- Add Qwen-specific model constants

#### File: `scripts/config/automation.yaml`
- Add qwen configuration section:
```yaml
agent:
  qwen:
    command: "qwen"  # Or path to binary
    model_default: "qwen-max"  # Or appropriate default
    model_audit: "qwen-plus"
```

### 7. Backward Compatibility
- All existing Claude Code functionality must remain unchanged
- Default provider should remain Claude for compatibility
- Qwen provider should be optional and configurable

### 8. Testing
- Add unit tests for QwenAgentCLI
- Test tool name translations
- Test command building with Qwen-specific options
- Test integration with existing workflows

## Implementation Strategy

### Phase 1: Core Implementation
1. Create `QwenAgentCLI` class with basic command building
2. Implement tool name translation
3. Add to factory and enum

### Phase 2: Configuration
1. Add Qwen settings to automation.yaml
2. Update presets to support Qwen
3. Test basic functionality

### Phase 3: Integration
1. Test with existing workflows (audit, tasks, sync, docs)
2. Update any Qwen-specific hooks or requirements
3. Add comprehensive tests

## Expected Benefits

- Support for alternative AI providers
- Ability to compare Claude vs Qwen performance/cost
- Increased flexibility in provider selection
- No vendor lock-in for AI services