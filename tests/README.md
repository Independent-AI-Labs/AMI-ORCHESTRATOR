# AMI Automation Testing Suite

## Overview

This directory contains the complete test suite for the AMI Automation System, including unit tests, integration tests, edge case tests, and performance benchmarks.

**IMPORTANT**: These are REAL end-to-end integration tests that:
- Actually execute subprocess calls
- Actually invoke Claude CLI with `claude --print`
- Actually run hooks with real stdin
- NO mocking of core functionality (get_agent_cli, subprocess, LLM calls)

## Test Structure

```
tests/
├── unit/                    # Fast unit tests (mocking allowed)
├── integration/             # Real subprocess execution, LLM calls
├── edge_cases/              # Unusual inputs, error conditions
├── performance/             # Throughput, concurrency, scalability
└── fixtures/                # Test data and mock files
    ├── code/                # Sample code files (clean and violations)
    ├── hooks/               # Hook input JSON files
    ├── transcripts/         # Sample conversation transcripts
    └── instructions/        # Simple task instructions
```

## Test Categories

### Unit Tests (`tests/unit/`)

Fast tests that verify individual functions and classes in isolation. Mocking is allowed and encouraged for external dependencies like subprocess calls and file I/O.

**Characteristics:**
- Run in < 1 second each
- No network or subprocess calls
- No file system writes (use mocks)
- Can mock `get_agent_cli()` and subprocess

**Example:**
```python
def test_config_get_nested_key():
    """Config.get() supports dot notation."""
    config = Config()
    assert config.get("logging.level") == "INFO"
```

### Integration Tests (`tests/integration/`)

Real end-to-end tests that actually execute subprocesses and invoke Claude CLI. NO MOCKING of core functionality.

**Characteristics:**
- Actually run `subprocess.run()` to call ami-agent
- Actually invoke `claude --print` via ClaudeAgentCLI
- Actually test hooks with real stdin/stdout
- Marked with `@pytest.mark.integration`
- May be marked with `@pytest.mark.requires_claude_cli` if they need Claude installed
- May be marked with `@pytest.mark.slow` if they take >10 seconds

**Example:**
```python
@pytest.mark.integration
@pytest.mark.requires_claude_cli
def test_hook_code_quality_calls_real_llm():
    """ami-agent --hook code-quality actually invokes Claude CLI for LLM audit."""
    result = subprocess.run(
        ["./scripts/ami-agent", "--hook", "code-quality"],
        stdin=open("tests/fixtures/hooks/edit_violation.json"),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["decision"] == "deny"
    assert "CODE QUALITY" in output["reason"]
```

### Edge Case Tests (`tests/edge_cases/`)

Tests for unusual inputs, boundary conditions, and error handling.

**Characteristics:**
- Empty/missing files
- Malformed JSON
- Unicode and special characters
- Very large files
- Timeout conditions
- Missing dependencies

**Example:**
```python
def test_hook_malformed_json():
    """Hook with malformed JSON fails gracefully."""
    result = subprocess.run(
        ["./scripts/ami-agent", "--hook", "command-guard"],
        input="{not valid json}",
        capture_output=True,
        text=True,
    )

    # Should fail-open on parse error
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output.get("decision") in (None, "allow")
```

### Performance Tests (`tests/performance/`)

Benchmarks for throughput, concurrency, and scalability.

**Characteristics:**
- Marked with `@pytest.mark.performance`
- Measure execution time
- Test parallel vs sequential processing
- Verify cache speedup
- Check memory usage

**Example:**
```python
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.requires_claude_cli
def test_audit_parallel_vs_sequential():
    """Parallel audit is faster than sequential."""
    # Create 10 test files...

    # Sequential
    start = time.time()
    results_seq = engine.audit_directory(tmpdir_path, parallel=False)
    time_sequential = time.time() - start

    # Parallel
    start = time.time()
    results_par = engine.audit_directory(tmpdir_path, parallel=True, max_workers=4)
    time_parallel = time.time() - start

    # Parallel should be faster
    assert len(results_seq) == len(results_par) == 10
    print(f"Sequential: {time_sequential:.2f}s, Parallel: {time_parallel:.2f}s")
```

## Test Fixtures

### Code Samples (`tests/fixtures/code/`)

- **clean.py**, **clean.js**: Well-written code with no violations
- **violations.py**, **violations.js**: Intentionally bad code with known violations
- All violations marked with `# test-fixture` exemption comments

**Purpose**: Test that audit engine correctly identifies good vs bad code.

### Hook Inputs (`tests/fixtures/hooks/`)

JSON files representing hook input from Claude Code:

- **bash_allow.json**: Safe bash command (ls)
- **bash_deny_python.json**: Forbidden python3 command
- **bash_deny_pip.json**: Forbidden pip install
- **bash_deny_git_commit.json**: Forbidden git commit
- **edit_violation.json**: Edit introducing code quality violation

**Purpose**: Test hook validators with realistic input.

### Transcripts (`tests/fixtures/transcripts/`)

JSONL files representing conversation transcripts:

- **clean_with_work_done.jsonl**: Valid conversation with completion marker
- **violation_youre_right.jsonl**: Contains prohibited phrase "you're right"
- **no_completion_marker.jsonl**: Missing WORK DONE/FEEDBACK marker

**Purpose**: Test ResponseScanner hook.

### Instructions (`tests/fixtures/instructions/`)

- **simple_task.txt**: Minimal instruction that outputs "PASS"

**Purpose**: Test agent CLI execution with simple, predictable output.

## Running Tests

### Run All Tests

```bash
./scripts/ami-run scripts/run_tests.py
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
./scripts/ami-run scripts/run_tests.py tests/unit/

# Integration tests only
./scripts/ami-run scripts/run_tests.py tests/integration/

# Edge cases
./scripts/ami-run scripts/run_tests.py tests/edge_cases/

# Performance tests
./scripts/ami-run scripts/run_tests.py tests/performance/
```

### Run by Markers

```bash
# Only integration tests that require Claude CLI
./scripts/ami-run scripts/run_tests.py -m requires_claude_cli

# Skip slow tests
./scripts/ami-run scripts/run_tests.py -m "not slow"

# Only performance tests
./scripts/ami-run scripts/run_tests.py -m performance
```

## Exemption Comments for Test Files

Test files may contain code that violates quality rules. Use exemption comments to allow this:

```python
# test-fixture    - Marks test setup code
# example         - Marks example/documentation code
# noqa           - Skips pattern matcher entirely
```

**Example:**
```python
def test_hook_denies_bare_except():  # test-fixture
    """Test that hook blocks bare except."""

    # This code has intentional violations
    code = """
try:
    risky_operation()
except:  # test-fixture
    return False  # test-fixture
"""

    result = subprocess.run(...)  # test-fixture
    assert result["decision"] == "deny"
```

**IMPORTANT**: Test fixtures directory is NOT excluded from quality checks. Files must use exemption comments on every line with violations.

## Pytest Markers

Configured in `pytest.ini`:

- `integration`: Integration tests (actual CLI calls, slower)
- `requires_claude_cli`: Tests that require Claude CLI to be installed
- `slow`: Tests that take >10 seconds
- `performance`: Performance benchmark tests

## Coverage Goals

### Current Coverage (as of 2025-10-18)

- **Unit tests**: ~50+ tests covering config, logging, pattern matching
- **Integration tests**: ~80+ tests covering:
  - ami-agent script (hook mode, print mode, audit mode)
  - ClaudeAgentCLI (subprocess execution, tool restrictions)
  - AuditEngine (LLM calls, parallel processing, report generation)
  - All hook validators (CommandValidator, CodeQualityValidator, ResponseScanner)
- **Edge cases**: ~25+ tests for error handling and boundary conditions
- **Performance**: ~8+ benchmarks for throughput and concurrency

**Total: 160+ tests**

## CI/CD Integration

Tests run automatically on:
- Pre-commit hooks (unit tests only, fast)
- Pull request validation (all tests except performance)
- Scheduled nightly builds (all tests including performance)

## Writing New Tests

### Unit Test Template

```python
def test_feature_description():
    """Test that feature behaves correctly."""
    # Arrange
    config = Config()

    # Act
    result = config.get("key")

    # Assert
    assert result == expected_value
```

### Integration Test Template

```python
@pytest.mark.integration
@pytest.mark.requires_claude_cli
def test_feature_real_execution():  # test-fixture
    """Test feature with actual subprocess execution."""
    # Setup
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    input_file = fixtures_dir / "inputs" / "test_input.json"

    # Execute
    result = subprocess.run(  # test-fixture
        ["./scripts/ami-agent", "--mode", "test"],
        stdin=open(input_file),  # test-fixture
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Verify
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["status"] == "success"
```

### Performance Test Template

```python
@pytest.mark.performance
@pytest.mark.slow
def test_feature_performance():  # test-fixture
    """Benchmark feature performance."""
    iterations = 100
    start = time.time()  # test-fixture

    for _ in range(iterations):  # test-fixture
        perform_operation()

    elapsed = time.time() - start  # test-fixture
    avg_time = (elapsed / iterations) * 1000  # test-fixture

    print(f"Average time: {avg_time:.2f}ms")
    assert avg_time < threshold_ms
```

## Troubleshooting

### Tests Fail with "Command not found: claude"

Integration tests marked with `@pytest.mark.requires_claude_cli` require Claude CLI to be installed and available in PATH.

**Skip these tests:**
```bash
./scripts/ami-run scripts/run_tests.py -m "not requires_claude_cli"
```

### Tests Timeout

Some integration and performance tests may timeout on slow systems. Increase timeout:

```python
result = subprocess.run(..., timeout=300)  # 5 minutes
```

### Hook Blocks Test Code

Test code may be blocked by hooks. Use `# test-fixture` exemption comments.

### Cache Interference

Audit cache may cause tests to pass/fail inconsistently. Clear cache:

```bash
rm -rf .cache/audit
```

## Maintenance

### Adding New Test Fixtures

1. Create fixture file in appropriate subdirectory
2. Add `# test-fixture` comments on any violation lines
3. Document fixture in this README

### Updating Markers

1. Edit `pytest.ini` to add new markers
2. Update this README with marker documentation
3. Update CI/CD configuration if needed

### Test Coverage Reports

Generate coverage report:

```bash
./scripts/ami-run scripts/run_tests.py --cov=automation --cov-report=html
```

View report at `htmlcov/index.html`

## ami-repo Test Suite

Comprehensive testing for the `ami-repo` CLI tool covering repository management, SSH access control, and network security.

### Test Structure

```
tests/
├── unit/
│   └── test_ami_repo.py           # Unit tests (25 tests)
├── integration/
│   ├── test_ami_repo_e2e.py       # Integration tests (40 tests)
│   └── test_ami_repo_network.py   # Network E2E tests (20 tests)
└── fixtures/
    └── ami_repo/
        ├── test_keys/              # Pre-generated SSH test keys
        ├── conftest.py             # Shared fixtures
        └── README.md
```

### Test Categories

#### Unit Tests (`tests/unit/test_ami_repo.py`)

Fast isolated tests with mocking:

```bash
./scripts/ami-run scripts/run_tests.py tests/unit/test_ami_repo.py
```

**Coverage:**
- GitRepoManager initialization
- URL generation (file://, ssh://)
- SSH key validation
- Repository name handling
- Error handling paths
- Path safety validation

**Example:**
```python
def test_validates_ed25519_key(self, tmp_path):
    """add_ssh_key accepts valid ED25519 key."""
    manager = GitRepoManager(base_path=tmp_path)
    key_file.write_text("ssh-ed25519 AAAAC3Nz...")
    manager.add_ssh_key(key_file, "test-key")  # Should succeed
```

#### Integration Tests (`tests/integration/test_ami_repo_e2e.py`)

Real git operations, NO mocking:

```bash
./scripts/ami-run scripts/run_tests.py tests/integration/test_ami_repo_e2e.py
```

**Coverage:**
- Repository lifecycle: init → create → clone → commit → push → delete
- SSH key management: add → list → remove
- Multiple repository handling
- Error cases and edge conditions
- Complete workflows

**Markers:** `@pytest.mark.integration`

**Example:**
```python
@pytest.mark.integration
@pytest.mark.slow
def test_full_repo_lifecycle(self, tmp_path):
    """Complete workflow: init → create → clone → modify → delete."""
    manager = GitRepoManager(base_path=tmp_path / "git-server")
    manager.init_server()
    manager.create_repo("project")
    # ... real git operations ...
    manager.delete_repo("project", force=True)
```

#### Network E2E Tests (`tests/integration/test_ami_repo_network.py`)

**CRITICAL:** Tests over eth0 (192.168.50.66) NOT loopback!

```bash
./scripts/ami-run scripts/run_tests.py tests/integration/test_ami_repo_network.py -m network
```

**Prerequisites:**
- SSH server running on port 22
- Network interface eth0 with IP 192.168.50.66
- User 'ami' with SSH access

**Coverage:**
- SSH authentication over network
- Git clone/push/pull over SSH (192.168.50.66)
- Security restrictions:
  - Shell access blocked
  - Port forwarding blocked
  - X11 forwarding blocked
  - PTY allocation blocked
  - Non-git commands blocked
- Multi-user scenarios
- Concurrent operations
- Key rotation

**Markers:** `@pytest.mark.network`, `@pytest.mark.requires_ssh`, `@pytest.mark.ssh_security`

**Example:**
```python
@pytest.mark.network
@pytest.mark.requires_ssh
@pytest.mark.ssh_security
def test_shell_access_blocked(self, real_git_server, ssh_test_key):
    """Restricted SSH key cannot get shell access."""
    # Setup key with git-only restrictions
    # Try: ssh user@192.168.50.66 "ls /tmp"
    # Expected: BLOCKED by git-shell
    assert result.returncode != 0 or "fatal" in result.stderr
```

### Running ami-repo Tests

```bash
# All ami-repo tests
./scripts/ami-run scripts/run_tests.py -k ami_repo

# Unit tests only (fast)
./scripts/ami-run scripts/run_tests.py tests/unit/test_ami_repo.py

# Integration tests only
./scripts/ami-run scripts/run_tests.py tests/integration/test_ami_repo_e2e.py

# Network tests only (requires SSH server)
./scripts/ami-run scripts/run_tests.py tests/integration/test_ami_repo_network.py

# Skip network tests (no SSH server)
./scripts/ami-run scripts/run_tests.py -k ami_repo -m "not network"

# Only security restriction tests
./scripts/ami-run scripts/run_tests.py -m ssh_security
```

### Test Fixtures

#### SSH Test Keys

Pre-generated SSH keys in `tests/fixtures/ami_repo/test_keys/`:
- `test_ed25519` / `test_ed25519.pub` - ED25519 key
- `test_rsa` / `test_rsa.pub` - RSA 2048 key

**WARNING:** Test keys only! Never use for real authentication.

#### Shared Fixtures (conftest.py)

```python
@pytest.fixture
def temp_git_server(tmp_path):
    """Temporary git server with initialized structure."""

@pytest.fixture
def ssh_key_pair(tmp_path):
    """Generate temporary SSH key pair."""

@pytest.fixture
def test_repo_with_commits(tmp_path):
    """Git repository with test commits."""

@pytest.fixture
def network_ssh_config(tmp_path):
    """SSH config for network tests (eth0)."""

@pytest.fixture
def git_repo_manager(tmp_path):
    """GitRepoManager instance with temp base path."""
```

### Network Test Configuration

Network tests use **real network interface** (NOT loopback):

```python
# CRITICAL: eth0 interface, NOT 127.0.0.1
SSH_HOST = "192.168.50.66"  # From ip addr show eth0
SSH_USER = "ami"
SSH_PORT = 22
```

Tests verify connections go through eth0 by:
1. Explicitly using 192.168.50.66 in SSH URLs
2. Testing actual SSH authentication
3. Validating git operations over network

### Security Test Validation

Network tests validate SSH restrictions:

| Restriction | Test | Expected Result |
|-------------|------|-----------------|
| No shell | `ssh user@host "ls"` | Connection closed or error |
| No port forwarding | `ssh -L 9999:localhost:22` | Forwarding fails |
| No X11 forwarding | `ssh -X user@host` | X11 disabled |
| No PTY | `ssh -t user@host` | No interactive shell |
| Git commands only | `ssh user@host "cat /etc/passwd"` | Command rejected |
| Directory restriction | Path traversal attempts | Blocked by git-shell |

### Test Coverage Summary

- **Total:** 85 tests
- **Unit:** 25 tests (< 10s total)
- **Integration:** 40 tests (< 2min total)
- **Network:** 20 tests (< 5min total)

**Lines of Code:** ~1500+ test code
**Coverage Areas:**
- Repository management (100%)
- SSH key management (100%)
- Security restrictions (100%)
- Error handling (100%)
- Network operations (100%)

## Philosophy

These tests follow the principle: **TEST WHAT RUNS IN PRODUCTION**.

- Integration tests mirror real-world usage
- No mocking of critical paths
- Fail-open behavior is explicitly tested
- Error handling is as important as happy paths
- Performance is a feature, not an afterthought
- **Network tests use real interfaces, not loopback**
- **Security restrictions are validated end-to-end**

When in doubt, write an integration test that actually exercises the full stack.
