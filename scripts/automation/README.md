# AMI Automation

Automation framework for Claude Code hooks, agents, and quality control.

## Hook Validators

The automation framework includes several hook validators that run during Claude Code operations:

### ResearchValidator

**Purpose**: Prevents hallucinated implementations by validating that the assistant performed adequate research before making code changes.

**When it runs**: PreToolUse hook on Write/Edit/NotebookEdit operations

**What it checks**:
- **Documentation research**: Did assistant read official docs (WebFetch/WebSearch) before implementing external APIs/libraries?
- **Codebase inspection**: Did assistant read existing code (Read/Grep/Glob) before making architectural changes?
- **Claim verification**: Did assistant verify assumptions with tools before implementing?

**Skip conditions**:
- Trivial changes (< 5 lines by default, configurable)
- No transcript available
- Tool is not Write/Edit/NotebookEdit

**Configuration** (in `scripts/config/automation.yaml`):
```yaml
research_validator:
  skip_threshold_lines: 5  # Skip validation for diffs < 5 lines
  lookback_messages: 30    # Check last 30 messages for research tools
```

**How to avoid blocks**:
1. **Before implementing external APIs/libraries**: Use WebFetch to read official documentation
2. **Before changing interfaces/architecture**: Use Read/Grep to understand existing code
3. **Before assuming structure**: Use tools to verify claims (Read for file contents, Grep for patterns, Bash for testing)

**Example block**:
```
RESEARCH VALIDATION FAILED

Implementing Claude Code hook feature (background_tasks) without reading hooks documentation.
No WebFetch to verify field exists in hook input. This is hallucinated implementation based on assumption.

Before making code changes:
- Read official documentation for external APIs/libraries
- Use Read/Grep/Glob to understand existing code patterns
- Verify claims with tools before implementing
```

### ResponseScanner

**Purpose**: Validates completion markers and scans for communication violations

**When it runs**: Stop and SubagentStop hooks

**What it checks**:
- Completion markers (WORK DONE, FEEDBACK:)
- Prohibited communication patterns ("you're right", "I see the issue", avoidance language)
- Incomplete tasks when claiming WORK DONE

### TodoValidatorHook

**Purpose**: Ensures todos being marked complete are actually done

**When it runs**: PreToolUse hook on TodoWrite operations

**What it checks**:
- Todos marked as completed match actual work done
- Todo content edits reflect real changes

### MaliciousBehaviorValidator

**Purpose**: Detects bypass scripts and malicious code patterns

**When it runs**: PreToolUse hook on Write/Edit/Bash operations

**What it checks**:
- Bypass script creation attempts
- Malicious patterns (credential harvesting, security bypasses)

### CommandValidator

**Purpose**: Validates Bash commands against security patterns

**When it runs**: PreToolUse hook on Bash operations

**What it checks**:
- Dangerous commands (rm -rf /, dd, mkfs, etc.)
- Credential exposure risks
- Out-of-sandbox operations

### CoreQualityValidator

**Purpose**: Checks code quality patterns across all languages

**When it runs**: PreToolUse hook on Edit/Write operations

**What it checks**:
- Banned patterns from patterns_core.txt
- Cross-language antipatterns

### PythonQualityValidator

**Purpose**: Checks Python-specific quality patterns

**When it runs**: PreToolUse hook on Edit/Write operations (Python files only)

**What it checks**:
- Banned patterns from patterns_python.txt
- Python-specific antipatterns

### ShebangValidator

**Purpose**: Validates Python file shebangs for security

**When it runs**: PreToolUse hook on Edit/Write operations (Python files only)

**What it checks**:
- Security issues (sudo, system python paths)
- Incorrect shebang formats
- Missing ami-run wrapper

## Performance Impact

- **ResearchValidator**: ~2-5 seconds for diffs > 5 lines (runs moderator LLM)
- **ResponseScanner**: ~5-10 seconds on Stop (runs completion moderator LLM)
- **TodoValidatorHook**: ~2-5 seconds on TodoWrite (runs moderator LLM)
- **Other validators**: <100ms (pattern matching only)

## Configuration Files

- **hooks.yaml**: Hook definitions (event, matcher, command, timeout)
- **automation.yaml**: Configuration for validators, agents, prompts
- **patterns/*.yaml**: Pattern definitions for quality validators

## Moderator Prompts

Located in `scripts/config/prompts/`:
- `research_validator_moderator.txt`: ResearchValidator decisions
- `completion_moderator.txt`: ResponseScanner completion validation
- `todo_validator_moderator.txt`: TodoValidatorHook decisions
- `malicious_behavior_moderator.txt`: MaliciousBehaviorValidator decisions
