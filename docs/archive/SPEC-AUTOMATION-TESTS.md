# AMI Automation System - Test Specification v2.0

> **ARCHIVED**: This specification was the original test plan for automation v2.0 (2025-10-18).
> The system evolved significantly beyond this spec with new features (task executor, docs automation,
> completion moderator, streaming support). Tests were implemented with different organization.
> See `/tests/unit/` and `/tests/integration/` directories for current test implementation.

**Version**: 2.0.0
**Created**: 2025-10-18
**Archived**: 2025-10-27
**Status**: SUPERSEDED
**Spec Reference**: SPEC-AUTOMATION-V2.md

---

## 1. Overview

This specification defines comprehensive test coverage for the AMI Automation System v2.0.

### 1.1 Test Coverage Goals

| Component | Target Coverage | Critical Paths |
|-----------|----------------|----------------|
| config.py | >90% | Env vars, path resolution, YAML parsing |
| logging.py | >85% | JSON formatting, structured fields |
| hooks.py | >95% | All validators, error handling |
| patterns.py | >90% | Pattern matching, exemptions |
| audit.py | >90% | File scanning, parallel processing, caching |
| agent_cli.py | >95% | Tool computation, config validation |
| ami-agent | >90% | Mode routing, arg parsing |
| **Overall** | **>90%** | All critical functionality |

### 1.2 Test Categories

1. **Unit Tests** - Individual functions/classes in isolation
2. **Integration Tests** - Module interactions and workflows
3. **End-to-End Tests** - Full system scenarios
4. **Performance Tests** - Scalability and latency
5. **Security Tests** - Injection, bypass, validation
6. **Regression Tests** - Feature parity with bash implementation

---

## 2. Unit Tests

### 2.1 Configuration Module (`automation/config.py`)

**Test File**: `tests/unit/test_config.py`

#### Test Cases

```python
class TestConfig:
    """Unit tests for Config class."""

    def test_load_valid_yaml(self):
        """Config loads valid YAML file."""
        # Given: Valid automation.yaml
        # When: Config()
        # Then: Loads successfully, all keys accessible

    def test_environment_variable_substitution(self):
        """Config substitutes ${VAR:default} patterns."""
        # Given: YAML with "${AMI_ENV:development}"
        # When: Config loaded
        # Then: Substitutes from os.environ or uses default

    def test_environment_variable_no_default(self):
        """Config handles ${VAR} without default."""
        # Given: YAML with "${REQUIRED_VAR}"
        # When: REQUIRED_VAR not in environment
        # Then: Returns empty string

    def test_nested_environment_substitution(self):
        """Config substitutes env vars in nested dicts."""
        # Given: Nested YAML structure with ${VAR}
        # When: Config loaded
        # Then: All levels substituted correctly

    def test_dot_notation_access(self):
        """Config.get() supports dot notation."""
        # Given: Config with nested structure
        # When: config.get("logging.level")
        # Then: Returns "INFO"

    def test_dot_notation_missing_key(self):
        """Config.get() returns default for missing keys."""
        # Given: Config loaded
        # When: config.get("missing.key", "default")
        # Then: Returns "default"

    def test_resolve_path_with_template(self):
        """Config.resolve_path() handles template substitution."""
        # Given: Path template "logs/{date}"
        # When: resolve_path("paths.logs", date="2025-10-18")
        # Then: Returns Path("{root}/logs/2025-10-18")

    def test_resolve_path_absolute(self):
        """Config.resolve_path() returns absolute paths."""
        # Given: Relative path "logs"
        # When: resolve_path("paths.logs")
        # Then: Returns {ORCHESTRATOR_ROOT}/logs

    def test_config_file_not_found(self):
        """Config raises error if file missing."""
        # Given: Non-existent config file path
        # When: Config(config_file="/bad/path.yaml")
        # Then: Raises FileNotFoundError

    def test_invalid_yaml_syntax(self):
        """Config raises error on invalid YAML."""
        # Given: Malformed YAML file
        # When: Config loaded
        # Then: Raises yaml.YAMLError

    def test_singleton_pattern(self):
        """get_config() returns same instance."""
        # Given: get_config() called twice
        # When: config1 = get_config(); config2 = get_config()
        # Then: config1 is config2

    def test_orchestrator_root_detection(self):
        """Config detects orchestrator root correctly."""
        # Given: Standard project structure
        # When: Config()
        # Then: self.root == ORCHESTRATOR_ROOT
```

**Total**: 12 unit tests

---

### 2.2 Logging Module (`automation/logging.py`)

**Test File**: `tests/unit/test_logging.py`

#### Test Cases

```python
class TestJSONFormatter:
    """Unit tests for JSONFormatter."""

    def test_format_basic_message(self):
        """JSONFormatter outputs valid JSON."""
        # Given: LogRecord with message
        # When: formatter.format(record)
        # Then: Returns valid JSON string

    def test_format_includes_timestamp(self):
        """JSON includes ISO timestamp with Z."""
        # Given: LogRecord
        # When: Formatted
        # Then: JSON contains "timestamp": "2025-10-18T12:00:00Z"

    def test_format_includes_level(self):
        """JSON includes log level."""
        # Given: LogRecord with level=INFO
        # When: Formatted
        # Then: JSON contains "level": "INFO"

    def test_format_includes_extra_fields(self):
        """JSONFormatter includes extra_fields."""
        # Given: LogRecord with extra_fields={"key": "value"}
        # When: Formatted
        # Then: JSON contains "key": "value"

class TestStructuredLogger:
    """Unit tests for StructuredLogger."""

    def test_logger_creation(self):
        """get_logger() creates logger instance."""
        # Given: get_logger("test")
        # When: Logger created
        # Then: Returns StructuredLogger instance

    def test_info_logging(self):
        """logger.info() logs with extra fields."""
        # Given: logger.info("message", key="value")
        # When: Logged
        # Then: Log entry contains message and key=value

    def test_error_logging(self):
        """logger.error() logs with ERROR level."""
        # Given: logger.error("error", code=500)
        # When: Logged
        # Then: Log entry has level=ERROR, code=500

    def test_file_handler_created(self):
        """Logger creates daily log file."""
        # Given: Logger initialized
        # When: First log entry
        # Then: Creates logs/{name}/YYYY-MM-DD.log

    def test_log_level_from_config(self):
        """Logger respects config log level."""
        # Given: Config with logging.level=WARNING
        # When: Logger created
        # Then: Only WARNING+ messages logged
```

**Total**: 9 unit tests

---

### 2.3 Hook Framework (`automation/hooks.py`)

**Test File**: `tests/unit/test_hooks.py`

#### Test Cases

```python
class TestHookInput:
    """Unit tests for HookInput."""

    def test_from_stdin_valid_json(self):
        """HookInput.from_stdin() parses valid JSON."""
        # Given: stdin with valid hook JSON
        # When: HookInput.from_stdin()
        # Then: Returns HookInput with all fields

    def test_from_stdin_missing_optional_fields(self):
        """HookInput handles missing optional fields."""
        # Given: JSON without tool_name, tool_input
        # When: Parsed
        # Then: Fields are None

    def test_from_stdin_invalid_json(self):
        """HookInput raises error on invalid JSON."""
        # Given: stdin with malformed JSON
        # When: from_stdin()
        # Then: Raises json.JSONDecodeError

class TestHookResult:
    """Unit tests for HookResult."""

    def test_allow_result(self):
        """HookResult.allow() creates allow result."""
        # Given: HookResult.allow()
        # When: to_json()
        # Then: Returns '{}'

    def test_deny_result(self):
        """HookResult.deny() creates deny result."""
        # Given: HookResult.deny("reason")
        # When: to_json()
        # Then: Returns '{"decision": "deny", "reason": "reason"}'

    def test_block_result(self):
        """HookResult.block() creates block result."""
        # Given: HookResult.block("reason")
        # When: to_json()
        # Then: Returns '{"decision": "block", "reason": "reason"}'

class TestCommandValidator:
    """Unit tests for CommandValidator."""

    def test_validate_allowed_command(self):
        """CommandValidator allows safe commands."""
        # Given: Bash tool with "ls -la"
        # When: validate()
        # Then: Returns allow()

    def test_deny_direct_python(self):
        """CommandValidator denies direct python calls."""
        # Given: Bash tool with "python3 script.py"
        # When: validate()
        # Then: Returns deny("Use ami-run instead of direct python")

    def test_deny_pip_install(self):
        """CommandValidator denies pip commands."""
        # Given: Bash tool with "pip install package"
        # When: validate()
        # Then: Returns deny("Add to pyproject.toml and use ami-uv sync")

    def test_deny_direct_uv(self):
        """CommandValidator denies direct uv."""
        # Given: Bash tool with "uv pip install"
        # When: validate()
        # Then: Returns deny("Use ami-uv wrapper")

    def test_deny_git_commit(self):
        """CommandValidator denies direct git commit."""
        # Given: Bash tool with "git commit -m 'msg'"
        # When: validate()
        # Then: Returns deny("Use scripts/git_commit.sh")

    def test_deny_git_push(self):
        """CommandValidator denies direct git push."""
        # Given: Bash tool with "git push origin main"
        # When: validate()
        # Then: Returns deny("Use scripts/git_push.sh")

    def test_deny_hook_bypass(self):
        """CommandValidator denies --no-verify."""
        # Given: Bash tool with "git commit --no-verify"
        # When: validate()
        # Then: Returns deny("Git hook bypass forbidden")

    def test_deny_background_ampersand(self):
        """CommandValidator denies & operator."""
        # Given: Bash tool with "command &"
        # When: validate()
        # Then: Returns deny("Use run_in_background parameter instead of &")

    def test_deny_semicolon(self):
        """CommandValidator denies semicolon."""
        # Given: Bash tool with "cmd1; cmd2"
        # When: validate()
        # Then: Returns deny("Use separate Bash calls or && for dependencies")

    def test_deny_or_operator(self):
        """CommandValidator denies || operator."""
        # Given: Bash tool with "cmd1 || cmd2"
        # When: validate()
        # Then: Returns deny("Use separate Bash calls instead of ||")

    def test_deny_append_redirect(self):
        """CommandValidator denies >> redirect."""
        # Given: Bash tool with "echo 'text' >> file"
        # When: validate()
        # Then: Returns deny("Use Edit/Write tools instead of >>")

    def test_deny_sed_inplace(self):
        """CommandValidator denies sed -i."""
        # Given: Bash tool with "sed -i 's/old/new/' file"
        # When: validate()
        # Then: Returns deny("Use Edit tool instead of sed -i")

    def test_allow_and_operator(self):
        """CommandValidator allows && for dependencies."""
        # Given: Bash tool with "cd dir && ls"
        # When: validate()
        # Then: Returns allow()

    def test_non_bash_tool_allowed(self):
        """CommandValidator ignores non-Bash tools."""
        # Given: Read tool
        # When: validate()
        # Then: Returns allow()

class TestCodeQualityValidator:
    """Unit tests for CodeQualityValidator."""

    def test_validate_non_edit_write_allowed(self):
        """CodeQualityValidator ignores non-Edit/Write tools."""
        # Given: Bash tool
        # When: validate()
        # Then: Returns allow()

    def test_validate_non_python_file_allowed(self):
        """CodeQualityValidator ignores non-Python files."""
        # Given: Edit tool on "file.js"
        # When: validate()
        # Then: Returns allow()

    def test_validate_edit_python_file(self):
        """CodeQualityValidator runs audit on Edit."""
        # Given: Edit tool on "file.py"
        # When: validate()
        # Then: Runs LLM audit on diff

    def test_validate_write_python_file(self):
        """CodeQualityValidator runs audit on Write."""
        # Given: Write tool on "file.py"
        # When: validate()
        # Then: Runs LLM audit on old vs new

    def test_validate_write_new_file(self):
        """CodeQualityValidator handles new files."""
        # Given: Write tool on non-existent "file.py"
        # When: validate()
        # Then: old_code = "", new_code = content

    def test_validate_pass_result(self):
        """CodeQualityValidator allows PASS audits."""
        # Given: LLM returns "PASS"
        # When: validate()
        # Then: Returns allow()

    def test_validate_fail_result(self):
        """CodeQualityValidator denies FAIL audits."""
        # Given: LLM returns failure message
        # When: validate()
        # Then: Returns deny() with reason

    def test_validate_diff_context_format(self):
        """CodeQualityValidator builds proper diff context."""
        # Given: Edit with old/new code
        # When: Build context
        # Then: Includes FILE, OLD CODE, NEW CODE sections

class TestResponseScanner:
    """Unit tests for ResponseScanner."""

    def test_scan_no_transcript_allows(self):
        """ResponseScanner allows if no transcript."""
        # Given: HookInput without transcript_path
        # When: validate()
        # Then: Returns allow()

    def test_scan_missing_transcript_allows(self):
        """ResponseScanner allows if transcript doesn't exist."""
        # Given: transcript_path points to non-existent file
        # When: validate()
        # Then: Returns allow()

    def test_scan_completion_marker_allows(self):
        """ResponseScanner allows 'WORK DONE' marker."""
        # Given: Last message contains "WORK DONE"
        # When: validate()
        # Then: Returns allow()

    def test_scan_feedback_marker_allows(self):
        """ResponseScanner allows 'FEEDBACK:' marker."""
        # Given: Last message contains "FEEDBACK: need help"
        # When: validate()
        # Then: Returns allow()

    def test_scan_violation_blocks(self):
        """ResponseScanner blocks prohibited phrases."""
        # Given: Last message contains "you're absolutely right"
        # When: validate()
        # Then: Returns block() with violation message

    def test_scan_no_marker_blocks(self):
        """ResponseScanner blocks if no completion marker."""
        # Given: Last message without markers
        # When: validate()
        # Then: Returns block() requesting marker

    def test_scan_detects_youre_right(self):
        """ResponseScanner detects "you're right" variations."""
        # Given: "you're right", "you're absolutely correct", etc.
        # When: validate()
        # Then: Returns block() with violation

    def test_scan_detects_issue_is_clear(self):
        """ResponseScanner detects "the issue is clear"."""
        # Given: Last message with "the issue is clear"
        # When: validate()
        # Then: Returns block() with violation

    def test_scan_detects_i_see_problem(self):
        """ResponseScanner detects "I see the problem"."""
        # Given: Last message with "I see the problem"
        # When: validate()
        # Then: Returns block() with violation

    def test_get_last_assistant_message(self):
        """ResponseScanner extracts last assistant text."""
        # Given: Transcript with multiple messages
        # When: _get_last_assistant_message()
        # Then: Returns last assistant text content

    def test_get_last_assistant_message_empty_transcript(self):
        """ResponseScanner handles empty transcripts."""
        # Given: Empty transcript file
        # When: _get_last_assistant_message()
        # Then: Returns ""

    def test_get_last_assistant_message_corrupted_json(self):
        """ResponseScanner handles corrupted transcript lines."""
        # Given: Transcript with invalid JSON lines
        # When: _get_last_assistant_message()
        # Then: Skips invalid lines, returns last valid message

class TestHookValidatorBase:
    """Unit tests for HookValidator base class."""

    def test_run_success(self):
        """HookValidator.run() outputs JSON result."""
        # Given: Valid hook input
        # When: run()
        # Then: Prints JSON to stdout, returns 0

    def test_run_exception_fails_open(self):
        """HookValidator.run() fails open on error."""
        # Given: validate() raises exception
        # When: run()
        # Then: Prints allow() result, returns 0

    def test_run_logs_execution(self):
        """HookValidator.run() logs execution."""
        # Given: Valid hook input
        # When: run()
        # Then: Logs hook_execution event

    def test_run_logs_result(self):
        """HookValidator.run() logs result."""
        # Given: validate() returns deny()
        # When: run()
        # Then: Logs hook_result with decision=deny
```

**Total**: 53 unit tests

---

### 2.4 Pattern Matcher (`automation/patterns.py`)

**Test File**: `tests/unit/test_patterns.py`

#### Test Cases

```python
class TestPatternMatcher:
    """Unit tests for PatternMatcher."""

    def test_load_patterns_python(self):
        """PatternMatcher loads python.yaml patterns."""
        # Given: patterns/python.yaml exists
        # When: PatternMatcher("python")
        # Then: Loads all patterns

    def test_load_patterns_missing_file(self):
        """PatternMatcher handles missing pattern file."""
        # Given: patterns/unknown.yaml doesn't exist
        # When: PatternMatcher("unknown")
        # Then: patterns = []

    def test_find_violations_match(self):
        """PatternMatcher detects matching violations."""
        # Given: Code with "except: return False"
        # When: find_violations()
        # Then: Returns Violation for exception_false_return

    def test_find_violations_no_match(self):
        """PatternMatcher returns empty set for clean code."""
        # Given: Code without violations
        # When: find_violations()
        # Then: Returns set()

    def test_exemption_files(self):
        """PatternMatcher respects file exemptions."""
        # Given: Pattern with exemptions.files=["*/env/paths.py"]
        # When: Checking env/paths.py
        # Then: Violation skipped

    def test_exemption_codes(self):
        """PatternMatcher respects code exemptions."""
        # Given: Pattern with exemptions.codes=["noqa: E402"]
        # When: Line contains "noqa: E402"
        # Then: Violation skipped

    def test_violation_line_numbers(self):
        """PatternMatcher tracks correct line numbers."""
        # Given: Violation on line 42
        # When: find_violations()
        # Then: Violation.line == 42

    def test_multiple_violations_same_pattern(self):
        """PatternMatcher detects multiple violations."""
        # Given: Code with 3 occurrences of same pattern
        # When: find_violations()
        # Then: Returns 3 Violations

    def test_violation_severity(self):
        """PatternMatcher includes severity."""
        # Given: Pattern with severity=CRITICAL
        # When: find_violations()
        # Then: Violation.severity == "CRITICAL"

    def test_violation_message(self):
        """PatternMatcher includes message."""
        # Given: Pattern with message="..."
        # When: find_violations()
        # Then: Violation.message == pattern message
```

**Total**: 10 unit tests

---

### 2.5 Audit Engine (`automation/audit.py`)

**Test File**: `tests/unit/test_audit.py`

#### Test Cases

```python
class TestAuditEngine:
    """Unit tests for AuditEngine."""

    def test_find_files_python(self):
        """AuditEngine finds Python files."""
        # Given: Directory with .py files
        # When: _find_files()
        # Then: Returns all .py files

    def test_find_files_exclude_patterns(self):
        """AuditEngine respects exclude patterns."""
        # Given: Config with exclude_patterns=["**/test_*"]
        # When: _find_files()
        # Then: Skips test_*.py files

    def test_find_files_skip_empty_init(self):
        """AuditEngine skips empty __init__.py."""
        # Given: Empty __init__.py file
        # When: _find_files()
        # Then: File skipped

    def test_find_files_include_nonempty_init(self):
        """AuditEngine includes non-empty __init__.py."""
        # Given: __init__.py with content
        # When: _find_files()
        # Then: File included

    def test_detect_language_python(self):
        """AuditEngine detects Python from .py extension."""
        # Given: file.py
        # When: _detect_language()
        # Then: Returns "python"

    def test_detect_language_javascript(self):
        """AuditEngine detects JavaScript from .js extension."""
        # Given: file.js
        # When: _detect_language()
        # Then: Returns "javascript"

    def test_detect_language_unknown(self):
        """AuditEngine returns None for unknown extensions."""
        # Given: file.txt
        # When: _detect_language()
        # Then: Returns None

    def test_audit_file_pass(self):
        """AuditEngine returns PASS for clean code."""
        # Given: Clean Python file
        # When: _audit_file()
        # Then: FileResult(status="PASS", violations=[])

    def test_audit_file_fail(self):
        """AuditEngine returns FAIL for violations."""
        # Given: Python file with violations
        # When: _audit_file()
        # Then: FileResult(status="FAIL", violations=[...])

    def test_audit_file_error(self):
        """AuditEngine returns ERROR on exception."""
        # Given: Audit raises exception
        # When: _audit_file()
        # Then: FileResult(status="ERROR")

    def test_audit_file_unknown_language(self):
        """AuditEngine skips unknown languages."""
        # Given: file.txt
        # When: _audit_file()
        # Then: FileResult(status="PASS", violations=[])

    def test_check_cache_hit(self):
        """AuditEngine uses cached results."""
        # Given: Cached result for file
        # When: _check_cache()
        # Then: Returns cached FileResult

    def test_check_cache_miss(self):
        """AuditEngine returns None on cache miss."""
        # Given: No cached result
        # When: _check_cache()
        # Then: Returns None

    def test_check_cache_stale(self):
        """AuditEngine ignores stale cache."""
        # Given: Cached result older than TTL
        # When: _check_cache()
        # Then: Returns None

    def test_cache_result(self):
        """AuditEngine caches results."""
        # Given: FileResult
        # When: _cache_result()
        # Then: Writes JSON cache file

    def test_save_report_mirrors_structure(self):
        """AuditEngine mirrors directory structure."""
        # Given: base/automation/config.py
        # When: _save_report()
        # Then: Creates docs/audit/{date}/automation/config.py.md

    def test_save_report_pass_result(self):
        """AuditEngine writes PASS report."""
        # Given: FileResult(status="PASS")
        # When: _save_report()
        # Then: Report contains "✅ No violations detected"

    def test_save_report_fail_result(self):
        """AuditEngine writes FAIL report with violations."""
        # Given: FileResult(status="FAIL", violations=[...])
        # When: _save_report()
        # Then: Report lists all violations

    def test_audit_directory_sequential(self):
        """AuditEngine audits sequentially when parallel=False."""
        # Given: Directory with 10 files, parallel=False
        # When: audit_directory()
        # Then: Audits files one by one

    def test_audit_directory_parallel(self):
        """AuditEngine audits in parallel when parallel=True."""
        # Given: Directory with 10 files, parallel=True
        # When: audit_directory()
        # Then: Uses ProcessPoolExecutor

    def test_audit_directory_progress_tracking(self):
        """AuditEngine prints progress during audit."""
        # Given: Directory with files
        # When: audit_directory()
        # Then: Prints "Progress: X/Y (Z%)" during execution

    def test_consolidate_patterns_only_failures(self):
        """AuditEngine only consolidates FAIL/ERROR files."""
        # Given: Mix of PASS/FAIL/ERROR results
        # When: audit_directory()
        # Then: consolidate() called only for FAIL/ERROR

    def test_consolidate_patterns_updates_file(self):
        """AuditEngine updates CONSOLIDATED.md."""
        # Given: Failed audit result
        # When: _consolidate_patterns()
        # Then: Runs LLM to update CONSOLIDATED.md

    def test_audit_directory_creates_output_dir(self):
        """AuditEngine creates output directory structure."""
        # Given: Directory to audit
        # When: audit_directory()
        # Then: Creates docs/audit/DD.MM.YYYY/
```

**Total**: 25 unit tests

---

### 2.6 Agent CLI (`automation/agent_cli.py`)

**Test File**: `tests/unit/test_agent_cli.py`

#### Test Cases

```python
class TestAgentConfig:
    """Unit tests for AgentConfig dataclass."""

    def test_create_basic_config(self):
        """AgentConfig creates with required fields."""
        # Given: AgentConfig(model="...")
        # When: Created
        # Then: All fields initialized

    def test_default_allowed_tools(self):
        """AgentConfig defaults allowed_tools to None."""
        # Given: AgentConfig(model="...")
        # When: No allowed_tools specified
        # Then: allowed_tools == None (all tools allowed)

    def test_default_enable_hooks(self):
        """AgentConfig defaults enable_hooks to True."""
        # Given: AgentConfig(model="...")
        # When: No enable_hooks specified
        # Then: enable_hooks == True

    def test_default_timeout(self):
        """AgentConfig defaults timeout to 180."""
        # Given: AgentConfig(model="...")
        # When: No timeout specified
        # Then: timeout == 180

class TestAgentConfigPresets:
    """Unit tests for AgentConfigPresets."""

    def test_audit_preset(self):
        """audit() preset has correct config."""
        # Given: AgentConfigPresets.audit()
        # When: Created
        # Then: model=Sonnet 4.5, allowed_tools=[WebSearch, WebFetch],
        #       enable_hooks=False, timeout=180

    def test_audit_diff_preset(self):
        """audit_diff() preset has correct config."""
        # Given: AgentConfigPresets.audit_diff()
        # When: Created
        # Then: model=Sonnet 4.5, allowed_tools=[WebSearch, WebFetch],
        #       enable_hooks=False, timeout=60

    def test_consolidate_preset(self):
        """consolidate() preset has correct config."""
        # Given: AgentConfigPresets.consolidate()
        # When: Created
        # Then: model=Sonnet 4.5, allowed_tools=[Read, Write, Edit, Web],
        #       enable_hooks=False, timeout=300

    def test_worker_preset(self):
        """worker() preset has correct config."""
        # Given: AgentConfigPresets.worker()
        # When: Created
        # Then: model=Sonnet 4.5, allowed_tools=None,
        #       enable_hooks=True, timeout=180

    def test_interactive_preset(self):
        """interactive() preset has correct config."""
        # Given: AgentConfigPresets.interactive()
        # When: Created
        # Then: model=Sonnet 4.5, allowed_tools=None,
        #       enable_hooks=True, timeout=None, mcp_servers=...

class TestClaudeAgentCLI:
    """Unit tests for ClaudeAgentCLI."""

    def test_all_tools_list_complete(self):
        """ALL_TOOLS contains all Claude Code tools."""
        # Given: ClaudeAgentCLI.ALL_TOOLS
        # When: Checked against Claude Code docs
        # Then: Contains all 15 tools

    def test_compute_disallowed_tools_none(self):
        """compute_disallowed_tools(None) returns []."""
        # Given: allowed_tools = None
        # When: compute_disallowed_tools(None)
        # Then: Returns []

    def test_compute_disallowed_tools_complement(self):
        """compute_disallowed_tools() returns complement."""
        # Given: allowed_tools = ["WebSearch", "WebFetch"]
        # When: compute_disallowed_tools()
        # Then: Returns [all other tools]

    def test_compute_disallowed_tools_unknown_tool(self):
        """compute_disallowed_tools() raises on unknown tool."""
        # Given: allowed_tools = ["UnknownTool"]
        # When: compute_disallowed_tools()
        # Then: Raises ValueError

    def test_compute_disallowed_tools_sorted(self):
        """compute_disallowed_tools() returns sorted list."""
        # Given: allowed_tools = ["Bash"]
        # When: compute_disallowed_tools()
        # Then: Returns sorted list

    def test_run_interactive_builds_command(self):
        """run_interactive() builds correct command."""
        # Given: AgentConfig with settings
        # When: run_interactive()
        # Then: Command includes --model, --allowed-tools, --disallowed-tools

    def test_run_interactive_mcp_config(self):
        """run_interactive() creates MCP config file."""
        # Given: AgentConfig with mcp_servers
        # When: run_interactive()
        # Then: Creates temp JSON file, adds --mcp-config

    def test_run_interactive_no_mcp(self):
        """run_interactive() skips MCP if not configured."""
        # Given: AgentConfig with mcp_servers=None
        # When: run_interactive()
        # Then: No --mcp-config in command

    def test_run_interactive_cleans_up_mcp_file(self):
        """run_interactive() deletes temp MCP file."""
        # Given: Interactive session with MCP
        # When: Session ends
        # Then: Temp MCP file deleted

    def test_run_print_builds_command(self):
        """run_print() builds correct command."""
        # Given: Instruction and config
        # When: run_print()
        # Then: Command includes --print, --model, tools

    def test_run_print_disables_hooks(self):
        """run_print() disables hooks when config.enable_hooks=False."""
        # Given: AgentConfig(enable_hooks=False)
        # When: run_print()
        # Then: Creates temp settings file with hooks={}

    def test_run_print_enables_hooks(self):
        """run_print() enables hooks when config.enable_hooks=True."""
        # Given: AgentConfig(enable_hooks=True)
        # When: run_print()
        # Then: No --settings flag (uses default)

    def test_run_print_stdin_string(self):
        """run_print() passes string stdin to process."""
        # Given: stdin="test input"
        # When: run_print()
        # Then: Subprocess receives stdin

    def test_run_print_stdin_file(self):
        """run_print() reads stdin from file."""
        # Given: stdin=open("file.txt")
        # When: run_print()
        # Then: Reads file, passes to subprocess

    def test_run_print_timeout(self):
        """run_print() respects timeout."""
        # Given: AgentConfig(timeout=10)
        # When: Process takes >10s
        # Then: Raises subprocess.TimeoutExpired

    def test_run_print_timeout_error_handling(self):
        """run_print() returns error on timeout."""
        # Given: Timeout occurs
        # When: run_print()
        # Then: Returns (1, "ERROR: Command timeout (Xs)")

    def test_run_print_exception_handling(self):
        """run_print() returns error on exception."""
        # Given: Subprocess raises exception
        # When: run_print()
        # Then: Returns (1, "ERROR: ...")

    def test_run_print_cleans_up_settings_file(self):
        """run_print() deletes temp settings file."""
        # Given: run_print() with hooks disabled
        # When: Execution finishes
        # Then: Temp settings file deleted

    def test_load_instruction_from_file(self):
        """_load_instruction() reads file."""
        # Given: Instruction file path
        # When: _load_instruction()
        # Then: Returns file content

    def test_load_instruction_template_substitution(self):
        """_load_instruction() substitutes {date}."""
        # Given: Instruction with "{date}"
        # When: _load_instruction()
        # Then: {date} replaced with current date

    def test_load_instruction_preserves_placeholders(self):
        """_load_instruction() preserves {file_path} for later."""
        # Given: Instruction with "{file_path}"
        # When: _load_instruction()
        # Then: {file_path} still present

    def test_get_agent_cli_returns_claude(self):
        """get_agent_cli() returns ClaudeAgentCLI."""
        # Given: get_agent_cli()
        # When: Called
        # Then: Returns ClaudeAgentCLI instance

    def test_run_noninteractive_convenience(self):
        """run_noninteractive() convenience function works."""
        # Given: Instruction file and stdin
        # When: run_noninteractive()
        # Then: Prints output, returns exit code
```

**Total**: 36 unit tests

---

### 2.7 Unified Entry Point (`scripts/ami-agent`)

**Test File**: `tests/unit/test_ami_agent.py`

#### Test Cases

```python
class TestModeInteractive:
    """Unit tests for mode_interactive()."""

    def test_loads_agent_instruction(self):
        """mode_interactive() loads agent.txt."""
        # Given: config/prompts/agent.txt exists
        # When: mode_interactive()
        # Then: Loads instruction from file

    def test_substitutes_date_in_instruction(self):
        """mode_interactive() substitutes {date}."""
        # Given: Instruction with {date}
        # When: mode_interactive()
        # Then: {date} replaced with current timestamp

    def test_creates_mcp_config_when_enabled(self):
        """mode_interactive() creates MCP config."""
        # Given: mcp.enabled=true in config
        # When: mode_interactive()
        # Then: Creates temp MCP config file

    def test_substitutes_root_in_mcp_args(self):
        """mode_interactive() substitutes {root} in MCP args."""
        # Given: MCP server args with {root}
        # When: mode_interactive()
        # Then: {root} replaced with ORCHESTRATOR_ROOT

    def test_skips_mcp_when_disabled(self):
        """mode_interactive() skips MCP when disabled."""
        # Given: mcp.enabled=false
        # When: mode_interactive()
        # Then: No MCP config created

    def test_creates_settings_file_with_hooks(self):
        """mode_interactive() creates settings file."""
        # Given: config/hooks.yaml with hooks
        # When: mode_interactive()
        # Then: Creates temp settings file with hooks

    def test_converts_hooks_to_claude_format(self):
        """mode_interactive() converts hooks to Claude Code format."""
        # Given: YAML hooks config
        # When: Converted to settings
        # Then: Matches Claude Code JSON settings format

    def test_writes_debug_log(self):
        """mode_interactive() writes to claude-debug.log."""
        # Given: Session started
        # When: mode_interactive()
        # Then: Appends session start to debug log

    def test_launches_claude_cli(self):
        """mode_interactive() launches claude command."""
        # Given: All setup complete
        # When: mode_interactive()
        # Then: Runs subprocess with claude CLI

    def test_cleans_up_temp_files(self):
        """mode_interactive() deletes temp files."""
        # Given: Session ends
        # When: mode_interactive() finishes
        # Then: Deletes temp settings and MCP files

class TestModePrint:
    """Unit tests for mode_print()."""

    def test_loads_instruction_file(self):
        """mode_print() loads instruction from file."""
        # Given: Instruction file path
        # When: mode_print()
        # Then: Loads file content

    def test_instruction_file_not_found(self):
        """mode_print() returns error if file missing."""
        # Given: Non-existent instruction file
        # When: mode_print()
        # Then: Returns 1, prints error

    def test_reads_stdin(self):
        """mode_print() reads input from stdin."""
        # Given: Data on stdin
        # When: mode_print()
        # Then: Passes stdin to agent CLI

    def test_uses_worker_preset(self):
        """mode_print() uses worker agent preset."""
        # Given: mode_print() called
        # When: Agent config created
        # Then: Uses AgentConfigPresets.worker()

    def test_prints_output(self):
        """mode_print() prints agent output."""
        # Given: Agent returns output
        # When: mode_print()
        # Then: Prints output to stdout

    def test_returns_exit_code(self):
        """mode_print() returns agent exit code."""
        # Given: Agent exits with code X
        # When: mode_print()
        # Then: Returns X

class TestModeHook:
    """Unit tests for mode_hook()."""

    def test_command_guard_validator(self):
        """mode_hook('command-guard') uses CommandValidator."""
        # Given: validator_name='command-guard'
        # When: mode_hook()
        # Then: Creates CommandValidator, calls run()

    def test_code_quality_validator(self):
        """mode_hook('code-quality') uses CodeQualityValidator."""
        # Given: validator_name='code-quality'
        # When: mode_hook()
        # Then: Creates CodeQualityValidator, calls run()

    def test_response_scanner_validator(self):
        """mode_hook('response-scanner') uses ResponseScanner."""
        # Given: validator_name='response-scanner'
        # When: mode_hook()
        # Then: Creates ResponseScanner, calls run()

    def test_unknown_validator_error(self):
        """mode_hook() returns error for unknown validator."""
        # Given: validator_name='unknown'
        # When: mode_hook()
        # Then: Returns 1, prints error

class TestModeAudit:
    """Unit tests for mode_audit()."""

    def test_audits_directory(self):
        """mode_audit() runs audit engine."""
        # Given: Directory path
        # When: mode_audit()
        # Then: Creates AuditEngine, runs audit_directory()

    def test_directory_not_found(self):
        """mode_audit() returns error if directory missing."""
        # Given: Non-existent directory
        # When: mode_audit()
        # Then: Returns 1, prints error

    def test_prints_summary(self):
        """mode_audit() prints audit summary."""
        # Given: Audit complete
        # When: mode_audit()
        # Then: Prints total/passed/failed counts

    def test_prints_failures(self):
        """mode_audit() prints failure details."""
        # Given: Audit with failures
        # When: mode_audit()
        # Then: Prints failed files and violations

    def test_returns_zero_on_success(self):
        """mode_audit() returns 0 if all pass."""
        # Given: All files pass
        # When: mode_audit()
        # Then: Returns 0

    def test_returns_one_on_failures(self):
        """mode_audit() returns 1 if any fail."""
        # Given: At least one failure
        # When: mode_audit()
        # Then: Returns 1

class TestMain:
    """Unit tests for main() argument routing."""

    def test_routes_to_interactive_default(self):
        """main() defaults to interactive mode."""
        # Given: No arguments
        # When: main()
        # Then: Calls mode_interactive()

    def test_routes_to_print(self):
        """main() routes --print to mode_print()."""
        # Given: --print <file>
        # When: main()
        # Then: Calls mode_print()

    def test_routes_to_hook(self):
        """main() routes --hook to mode_hook()."""
        # Given: --hook <validator>
        # When: main()
        # Then: Calls mode_hook()

    def test_routes_to_audit(self):
        """main() routes --audit to mode_audit()."""
        # Given: --audit <dir>
        # When: main()
        # Then: Calls mode_audit()

    def test_explicit_interactive_flag(self):
        """main() routes --interactive to mode_interactive()."""
        # Given: --interactive
        # When: main()
        # Then: Calls mode_interactive()

    def test_returns_mode_exit_code(self):
        """main() returns mode exit code."""
        # Given: Mode function returns X
        # When: main()
        # Then: Returns X
```

**Total**: 38 unit tests

---

## 3. Integration Tests

**Test File**: `tests/integration/test_workflows.py`

### Test Cases

```python
class TestEndToEndHooks:
    """Integration tests for hook execution."""

    def test_command_guard_denies_bad_command(self):
        """E2E: CommandValidator denies prohibited command."""
        # Given: Hook input with "python3 script.py"
        # When: ami-agent --hook command-guard
        # Then: Outputs deny decision

    def test_code_quality_runs_llm_audit(self):
        """E2E: CodeQualityValidator runs LLM audit."""
        # Given: Edit hook input with code change
        # When: ami-agent --hook code-quality
        # Then: Runs claude --print with audit_diff.txt

    def test_response_scanner_blocks_violation(self):
        """E2E: ResponseScanner blocks prohibited phrase."""
        # Given: Transcript with "you're right"
        # When: ami-agent --hook response-scanner
        # Then: Outputs block decision

class TestEndToEndAudit:
    """Integration tests for audit workflow."""

    def test_audit_small_directory(self):
        """E2E: Audit completes on small directory."""
        # Given: Directory with 10 Python files
        # When: ami-agent --audit <dir>
        # Then: Audits all files, creates reports

    def test_audit_creates_output_structure(self):
        """E2E: Audit creates mirrored directory structure."""
        # Given: Directory structure
        # When: Audit runs
        # Then: Creates docs/audit/{date}/ with mirrored structure

    def test_audit_parallel_processing(self):
        """E2E: Audit uses parallel processing."""
        # Given: Directory with 50 files
        # When: Audit with parallel=True
        # Then: Completes faster than sequential

    def test_audit_cache_reuse(self):
        """E2E: Audit reuses cached results."""
        # Given: Directory audited once
        # When: Re-run audit
        # Then: Uses cache, completes much faster

    def test_audit_consolidation(self):
        """E2E: Audit consolidates patterns from failures."""
        # Given: Audit with failures
        # When: Audit completes
        # Then: CONSOLIDATED.md updated

class TestEndToEndPrintMode:
    """Integration tests for print mode."""

    def test_print_mode_with_stdin(self):
        """E2E: Print mode processes stdin."""
        # Given: Instruction file and stdin data
        # When: cat data | ami-agent --print instruction.txt
        # Then: Agent processes, returns output

    def test_print_mode_with_hooks_enabled(self):
        """E2E: Print mode executes with hooks."""
        # Given: Print mode with worker preset
        # When: Agent makes Edit
        # Then: Hooks execute

class TestEndToEndInteractive:
    """Integration tests for interactive mode."""

    @pytest.mark.manual  # Requires manual testing
    def test_interactive_launches_claude(self):
        """E2E: Interactive mode launches Claude Code."""
        # Given: ami-agent (no args)
        # When: Launched
        # Then: Claude Code starts with hooks and MCP

class TestConfigurationLoading:
    """Integration tests for configuration system."""

    def test_load_all_configs(self):
        """E2E: All configs load successfully."""
        # Given: Standard config files
        # When: get_config()
        # Then: Loads automation.yaml, hooks.yaml, patterns

    def test_mcp_server_provisioning(self):
        """E2E: MCP servers provision from config."""
        # Given: MCP servers in automation.yaml
        # When: Interactive mode
        # Then: MCP config created with all servers
```

**Total**: 13 integration tests

---

## 4. Edge Cases and Error Handling

**Test File**: `tests/edge_cases/test_error_handling.py`

### Test Cases

```python
class TestConfigEdgeCases:
    """Edge case tests for configuration."""

    def test_config_file_empty(self):
        """Config handles empty YAML file."""
        # Given: Empty automation.yaml
        # When: Config()
        # Then: Raises error or returns empty dict

    def test_config_circular_env_var(self):
        """Config handles circular env var references."""
        # Given: ${A} -> ${B} -> ${A}
        # When: Config loaded
        # Then: Handles gracefully (no infinite loop)

    def test_config_malformed_yaml(self):
        """Config raises error on malformed YAML."""
        # Given: Invalid YAML syntax
        # When: Config()
        # Then: Raises yaml.YAMLError

    def test_config_missing_required_keys(self):
        """Config handles missing required keys."""
        # Given: YAML without required sections
        # When: config.get("missing.key")
        # Then: Returns None or default

class TestHookEdgeCases:
    """Edge case tests for hooks."""

    def test_hook_input_empty_json(self):
        """Hook handles empty JSON input."""
        # Given: stdin with "{}"
        # When: HookInput.from_stdin()
        # Then: Creates HookInput with None fields

    def test_hook_input_huge_json(self):
        """Hook handles very large JSON input."""
        # Given: stdin with 10MB JSON
        # When: HookInput.from_stdin()
        # Then: Parses successfully or raises clear error

    def test_hook_timeout_during_validation(self):
        """Hook handles timeout during validation."""
        # Given: Validation takes >timeout
        # When: run()
        # Then: Returns allow() (fail open)

    def test_hook_corrupted_transcript(self):
        """ResponseScanner handles corrupted transcript."""
        # Given: Transcript with invalid JSON lines
        # When: validate()
        # Then: Skips invalid lines, processes valid ones

    def test_hook_transcript_permission_denied(self):
        """ResponseScanner handles unreadable transcript."""
        # Given: Transcript file not readable
        # When: validate()
        # Then: Returns allow() (fail open)

class TestAuditEdgeCases:
    """Edge case tests for audit engine."""

    def test_audit_empty_directory(self):
        """Audit handles empty directory."""
        # Given: Directory with no files
        # When: audit_directory()
        # Then: Returns empty results list

    def test_audit_file_disappears_during_scan(self):
        """Audit handles file deletion during scan."""
        # Given: File deleted between find and audit
        # When: _audit_file()
        # Then: Returns ERROR status

    def test_audit_file_unreadable(self):
        """Audit handles permission denied on file."""
        # Given: File without read permission
        # When: _audit_file()
        # Then: Returns ERROR status

    def test_audit_llm_returns_malformed_output(self):
        """Audit handles unexpected LLM output."""
        # Given: LLM returns neither PASS nor expected format
        # When: _audit_file()
        # Then: Handles gracefully, marks as FAIL or ERROR

    def test_audit_cache_corrupted(self):
        """Audit handles corrupted cache file."""
        # Given: Cache file with invalid JSON
        # When: _check_cache()
        # Then: Returns None, re-audits file

    def test_audit_output_dir_permission_denied(self):
        """Audit handles unable to create output dir."""
        # Given: No write permission for output
        # When: audit_directory()
        # Then: Raises clear error

class TestAgentCLIEdgeCases:
    """Edge case tests for agent CLI."""

    def test_agent_cli_claude_not_installed(self):
        """Agent CLI handles missing claude command."""
        # Given: claude not in PATH
        # When: run_interactive()
        # Then: Raises FileNotFoundError

    def test_agent_cli_claude_crashes(self):
        """Agent CLI handles claude crash."""
        # Given: Claude exits with non-zero
        # When: run_print()
        # Then: Returns non-zero exit code

    def test_agent_cli_empty_stdout(self):
        """Agent CLI handles empty stdout."""
        # Given: Claude produces no output
        # When: run_print()
        # Then: Returns empty string

    def test_agent_cli_huge_stdout(self):
        """Agent CLI handles very large output."""
        # Given: Claude outputs 100MB
        # When: run_print()
        # Then: Captures all output or handles error

class TestAmiAgentEdgeCases:
    """Edge case tests for ami-agent entry point."""

    def test_ami_agent_conflicting_args(self):
        """ami-agent handles conflicting arguments."""
        # Given: --print and --hook both specified
        # When: main()
        # Then: Prefers first mode or raises error

    def test_ami_agent_missing_instruction_file(self):
        """ami-agent handles missing instruction file in print mode."""
        # Given: --print with non-existent file
        # When: mode_print()
        # Then: Returns 1, prints error

    def test_ami_agent_missing_directory(self):
        """ami-agent handles missing directory in audit mode."""
        # Given: --audit with non-existent directory
        # When: mode_audit()
        # Then: Returns 1, prints error
```

**Total**: 22 edge case tests

---

## 5. Performance Tests

**Test File**: `tests/performance/test_performance.py`

### Test Cases

```python
class TestAuditPerformance:
    """Performance tests for audit engine."""

    def test_audit_100_files_sequential(self):
        """Baseline: Audit 100 files sequentially."""
        # Given: 100 Python files
        # When: audit_directory(parallel=False)
        # Then: Completes, record time
        # Target: <10 minutes

    def test_audit_100_files_parallel_4_workers(self):
        """Parallel: Audit 100 files with 4 workers."""
        # Given: 100 Python files
        # When: audit_directory(parallel=True, max_workers=4)
        # Then: Completes faster than sequential
        # Target: <3 minutes

    def test_audit_cache_effectiveness(self):
        """Cache: Second audit uses cache."""
        # Given: 100 files audited once
        # When: Re-run audit with cache enabled
        # Then: >95% cache hit rate, <10s total time

    def test_hook_latency_command_guard(self):
        """Hook Latency: CommandValidator executes quickly."""
        # Given: 100 hook executions
        # When: Measure average latency
        # Then: <10ms average latency

    def test_hook_latency_code_quality(self):
        """Hook Latency: CodeQualityValidator with LLM."""
        # Given: 10 code quality hooks
        # When: Measure average latency
        # Then: <5s average latency (LLM call)

    def test_hook_latency_response_scanner(self):
        """Hook Latency: ResponseScanner reads transcript."""
        # Given: 100 hook executions
        # When: Measure average latency
        # Then: <50ms average latency

    def test_config_loading_time(self):
        """Config Loading: Loads quickly."""
        # Given: Standard config files
        # When: 100 Config() calls
        # Then: <1ms average per load

    def test_pattern_matching_large_file(self):
        """Pattern Matching: Handles large files."""
        # Given: 10,000 line Python file
        # When: PatternMatcher.find_violations()
        # Then: <100ms execution time
```

**Total**: 8 performance tests

---

## 6. Security Tests

**Test File**: `tests/security/test_security.py`

### Test Cases

```python
class TestCommandInjection:
    """Security tests for command injection prevention."""

    def test_command_validator_blocks_injection(self):
        """CommandValidator blocks shell injection attempts."""
        # Given: Bash tool with "ls; rm -rf /"
        # When: validate()
        # Then: Denies due to semicolon

    def test_command_validator_blocks_backticks(self):
        """CommandValidator blocks backtick command substitution."""
        # Given: Bash tool with "`malicious`"
        # When: validate()
        # Then: Denies or sanitizes

    def test_command_validator_blocks_dollar_subshell(self):
        """CommandValidator blocks $(malicious)."""
        # Given: Bash tool with "$(rm -rf /)"
        # When: validate()
        # Then: Denies or sanitizes

class TestPathTraversal:
    """Security tests for path traversal prevention."""

    def test_audit_rejects_path_traversal(self):
        """Audit rejects ../../../etc/passwd."""
        # Given: audit_directory("../../../etc")
        # When: _find_files()
        # Then: Rejects or sanitizes path

    def test_config_rejects_path_traversal_in_template(self):
        """Config rejects {root}/../../../etc."""
        # Given: Path template with traversal
        # When: resolve_path()
        # Then: Rejects or sanitizes

class TestInputValidation:
    """Security tests for input validation."""

    def test_hook_input_rejects_huge_json(self):
        """Hook rejects extremely large JSON (DoS)."""
        # Given: stdin with 1GB JSON
        # When: HookInput.from_stdin()
        # Then: Raises error or limits size

    def test_pattern_matcher_rejects_regex_bomb(self):
        """PatternMatcher rejects catastrophic backtracking regex."""
        # Given: Pattern with (a+)+b
        # When: find_violations()
        # Then: Rejects or limits execution time

    def test_agent_cli_sanitizes_instruction_file_path(self):
        """Agent CLI validates instruction file path."""
        # Given: instruction_file="../../etc/passwd"
        # When: run_print()
        # Then: Rejects or sanitizes path
```

**Total**: 8 security tests

---

## 7. Regression Tests (Feature Parity)

**Test File**: `tests/regression/test_feature_parity.py`

### Test Cases

```python
class TestMCPFeatureParity:
    """Regression: MCP configuration matches bash implementation."""

    def test_mcp_browser_server_provisioned(self):
        """Browser MCP server provisioned like bash."""
        # Given: automation.yaml with browser server
        # When: mode_interactive()
        # Then: MCP config includes browser with correct args

    def test_mcp_root_substitution(self):
        """MCP {root} substitution matches bash ${REPO_ROOT}."""
        # Given: MCP args with {root}
        # When: Config substituted
        # Then: Matches bash REPO_ROOT value

class TestModelSpecificationParity:
    """Regression: Model selection matches bash."""

    def test_audit_uses_sonnet_45(self):
        """Audit uses claude-sonnet-4-5 like bash."""
        # Given: Audit agent
        # When: run_print()
        # Then: Uses --model claude-sonnet-4-5

    def test_interactive_uses_sonnet_45(self):
        """Interactive uses claude-sonnet-4-5 like bash."""
        # Given: Interactive mode
        # When: mode_interactive()
        # Then: Uses --model claude-sonnet-4-5

class TestToolRestrictionsParity:
    """Regression: Tool restrictions match bash."""

    def test_audit_restricts_to_web_tools(self):
        """Audit restricts to WebSearch/WebFetch like bash."""
        # Given: Audit agent
        # When: run_print()
        # Then: allowed_tools=[WebSearch, WebFetch]

    def test_consolidate_allows_file_tools(self):
        """Consolidate allows Read/Write/Edit like bash."""
        # Given: Consolidate agent
        # When: run_print()
        # Then: allowed_tools includes Read, Write, Edit

class TestHookDisablingParity:
    """Regression: Hook disabling matches bash."""

    def test_audit_disables_hooks(self):
        """Audit disables hooks like bash."""
        # Given: Audit agent
        # When: run_print()
        # Then: Creates settings file with hooks={}

    def test_worker_enables_hooks(self):
        """Worker enables hooks like bash."""
        # Given: Worker agent
        # When: run_print()
        # Then: Hooks enabled (no empty settings)

class TestAuditOutputParity:
    """Regression: Audit output structure matches bash."""

    def test_audit_date_format_ddmmyyyy(self):
        """Audit uses DD.MM.YYYY format like bash."""
        # Given: Audit run on 18.10.2025
        # When: audit_directory()
        # Then: Creates docs/audit/18.10.2025/

    def test_audit_mirrors_directory_structure(self):
        """Audit mirrors structure like bash."""
        # Given: base/automation/config.py
        # When: Audited
        # Then: Creates docs/audit/{date}/automation/config.py.md

class TestProgressTrackingParity:
    """Regression: Progress tracking matches bash."""

    def test_audit_shows_progress(self):
        """Audit prints progress like bash."""
        # Given: Directory audit
        # When: Running
        # Then: Prints "Progress: X/Y (Z%)"

    def test_audit_shows_time_estimates(self):
        """Audit shows time estimates like bash."""
        # Given: Directory audit
        # When: Running
        # Then: Prints elapsed and remaining time

class TestSelectiveConsolidationParity:
    """Regression: Consolidation matches bash."""

    def test_consolidate_only_failures(self):
        """Consolidation only on FAIL/ERROR like bash."""
        # Given: Mix of PASS/FAIL results
        # When: audit_directory()
        # Then: consolidate() called only for FAIL/ERROR
```

**Total**: 12 regression tests

---

## 8. Test Execution Plan

### 8.1 Test Pyramid

```
                    /\
                   /  \
                  / E2E \         5% - 13 tests
                 /------\
                /        \
               / Integration\     10% - 13 tests
              /------------\
             /              \
            /  Unit Tests    \    85% - 183 tests
           /------------------\
          /____________________\
```

**Total Tests**: 209

### 8.2 Test Execution Strategy

#### Phase 1: Unit Tests (Week 1-2)
- Run during development
- Must pass before commit
- Target: >90% coverage

#### Phase 2: Integration Tests (Week 3)
- Run daily
- Must pass before merge to main
- Slower, more complex setup

#### Phase 3: E2E Tests (Week 4)
- Run before release
- Some manual testing required
- Full system validation

#### Phase 4: Performance & Security (Week 5)
- Run before deployment
- Benchmark against targets
- Security audit

### 8.3 Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=automation --cov-report=term

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: pytest tests/integration/ -v

  edge-cases:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v2
      - name: Run edge case tests
        run: pytest tests/edge_cases/ -v

  performance:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    steps:
      - uses: actions/checkout@v2
      - name: Run performance tests
        run: pytest tests/performance/ -v --benchmark

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run security tests
        run: pytest tests/security/ -v
```

---

## 9. Test Data Fixtures

### 9.1 Configuration Fixtures

**File**: `tests/fixtures/configs/valid_automation.yaml`
```yaml
version: "2.0.0"
environment: "test"
paths:
  logs: "test_logs"
  config: "test_config"
logging:
  level: "DEBUG"
claude_cli:
  command: "mock_claude"
mcp:
  enabled: true
  servers:
    browser:
      command: "python3"
      args: ["{root}/browser/test.py"]
```

**File**: `tests/fixtures/configs/invalid_automation.yaml`
```yaml
# Malformed YAML for error testing
version: "2.0.0
  missing_quote: true
```

### 9.2 Hook Input Fixtures

**File**: `tests/fixtures/hooks/bash_tool_input.json`
```json
{
  "session_id": "test-session-123",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "ls -la"
  },
  "transcript_path": "/path/to/transcript.jsonl"
}
```

**File**: `tests/fixtures/hooks/edit_tool_input.json`
```json
{
  "session_id": "test-session-123",
  "hook_event_name": "PreToolUse",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "test.py",
    "old_string": "def foo(): pass",
    "new_string": "def foo():\n    return 42"
  }
}
```

### 9.3 Transcript Fixtures

**File**: `tests/fixtures/transcripts/clean_response.jsonl`
```jsonl
{"type": "assistant", "uuid": "uuid-1", "message": {"content": [{"type": "text", "text": "I'll help you with that task. WORK DONE"}]}}
```

**File**: `tests/fixtures/transcripts/violation_response.jsonl`
```jsonl
{"type": "assistant", "uuid": "uuid-1", "message": {"content": [{"type": "text", "text": "You're absolutely right about that issue."}]}}
```

### 9.4 Code Sample Fixtures

**File**: `tests/fixtures/code/clean.py`
```python
def calculate_sum(numbers: list[int]) -> int:
    """Calculate sum of numbers."""
    return sum(numbers)
```

**File**: `tests/fixtures/code/violations.py`
```python
def process_data(data):
    try:
        return parse(data)
    except:  # noqa
        return False
```

---

## 10. Mock and Stub Strategy

### 10.1 Mocking Claude CLI

```python
# tests/mocks/mock_claude_cli.py

class MockClaudeAgent CLI:
    """Mock implementation for testing."""

    def __init__(self):
        self.calls = []
        self.return_values = {}

    def run_print(self, **kwargs):
        self.calls.append(("run_print", kwargs))
        return self.return_values.get("run_print", (0, "PASS"))

    def run_interactive(self, **kwargs):
        self.calls.append(("run_interactive", kwargs))
        return self.return_values.get("run_interactive", 0)
```

### 10.2 Mocking LLM Responses

```python
# tests/mocks/mock_llm.py

class MockLLMResponse:
    """Mock LLM responses for testing."""

    @staticmethod
    def audit_pass():
        return (0, "PASS")

    @staticmethod
    def audit_fail():
        return (1, "CRITICAL: Exception suppression detected on line 5")

    @staticmethod
    def audit_error():
        return (2, "ERROR: Unable to parse code")
```

### 10.3 Filesystem Mocking

```python
# tests/mocks/mock_filesystem.py

import tempfile
from pathlib import Path

class MockFilesystem:
    """Create temporary filesystem for testing."""

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)

    def create_file(self, path: str, content: str):
        file_path = self.root / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path

    def cleanup(self):
        import shutil
        shutil.rmtree(self.tmpdir)
```

---

## 11. Test Coverage Requirements

### 11.1 Module Coverage Targets

| Module | Lines | Target Coverage | Critical Paths |
|--------|-------|----------------|----------------|
| config.py | 100 | >90% | Env vars, path resolution, YAML parsing |
| logging.py | 150 | >85% | JSON formatting, file handlers |
| hooks.py | 300 | >95% | All validators, error handling |
| patterns.py | 200 | >90% | Pattern matching, exemptions |
| audit.py | 500 | >90% | File scanning, parallel, caching |
| agent_cli.py | 200 | >95% | Tool computation, CLI execution |
| ami-agent | 300 | >90% | Mode routing, arg parsing |

### 11.2 Uncovered Code Policy

- Document any uncovered lines with reason
- Exclude unreachable error paths if justified
- No coverage bypass without review

---

## 12. Test Maintenance

### 12.1 Test Naming Convention

```python
def test_<component>_<scenario>_<expected>():
    """Component behavior in scenario."""
```

Examples:
- `test_config_load_valid_yaml()`
- `test_command_validator_denies_pip_install()`
- `test_audit_cache_hit()`

### 12.2 Test Organization

```
tests/
├── unit/
│   ├── test_config.py
│   ├── test_logging.py
│   ├── test_hooks.py
│   ├── test_patterns.py
│   ├── test_audit.py
│   ├── test_agent_cli.py
│   └── test_ami_agent.py
├── integration/
│   └── test_workflows.py
├── edge_cases/
│   └── test_error_handling.py
├── performance/
│   └── test_performance.py
├── security/
│   └── test_security.py
├── regression/
│   └── test_feature_parity.py
├── fixtures/
│   ├── configs/
│   ├── hooks/
│   ├── transcripts/
│   └── code/
└── mocks/
    ├── mock_claude_cli.py
    ├── mock_llm.py
    └── mock_filesystem.py
```

---

## 13. Success Criteria

### 13.1 Coverage Metrics

- **Overall Coverage**: >90%
- **Critical Path Coverage**: 100%
- **All Tests Passing**: 100%

### 13.2 Performance Metrics

- **Hook Latency (CommandValidator)**: <10ms average
- **Hook Latency (ResponseScanner)**: <50ms average
- **Hook Latency (CodeQualityValidator)**: <5s average
- **Audit (100 files, parallel)**: <3 minutes
- **Cache Hit Rate**: >95% on re-audit

### 13.3 Quality Metrics

- **Zero Security Vulnerabilities**: All security tests pass
- **Zero Regressions**: All feature parity tests pass
- **Zero Flaky Tests**: Tests pass consistently

---

## APPROVED FOR IMPLEMENTATION

**Total Test Count**: 209 tests
- Unit: 183 tests
- Integration: 13 tests
- Edge Cases: 22 tests (included in unit count)
- Performance: 8 tests
- Security: 8 tests
- Regression: 12 tests (included in integration count)

**Coverage Target**: >90% overall
**Timeline**: 5 weeks (parallel with implementation)
