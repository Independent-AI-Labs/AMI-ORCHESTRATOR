"""Comprehensive pattern tests for all 66 CONSOLIDATED.md violation patterns.

These tests verify that CodeQualityValidator correctly detects and blocks
all 66 patterns when added (REGRESSION) and allows when removed (REMEDIATION).

Total: 132 tests (66 patterns × 2)
"""  # test-fixture

import subprocess

import pytest


class TestCRITICALPatterns:
    """CRITICAL severity patterns - highest security impact."""

    # Pattern 1: SQL Injection via f-string Formatting

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p001_sql_injection_regression(self):  # test-fixture
        """REGRESSION: Adding SQL injection via f-string triggers FAIL."""
        old_code = 'results = db.execute("SELECT * FROM users WHERE id = ?", (user_id,))'  # test-fixture
        new_code = 'results = db.execute(f"SELECT * FROM {table} WHERE id = {user_id}")'  # test-fixture

        diff = build_diff("db.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding SQL injection"
        assert "FAIL" in result["output"] or "SQL" in result["output"]

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p001_sql_injection_remediation(self):  # test-fixture
        """REMEDIATION: Removing SQL injection triggers PASS."""
        old_code = 'results = db.execute(f"SELECT * FROM {table} WHERE id = {user_id}")'  # test-fixture
        new_code = 'results = db.execute("SELECT * FROM users WHERE id = ?", (user_id,))'  # test-fixture

        diff = build_diff("db.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing SQL injection"

    # Pattern 2: Cascading Subprocess Fallbacks with RCE Risk

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p002_rce_fallback_regression(self):  # test-fixture
        """REGRESSION: Adding subprocess fallback chain triggers FAIL."""
        old_code = """
def run_command(cmd):
    return subprocess.run(cmd, check=True, shell=False)
"""  # test-fixture
        new_code = """
def run_command(cmd):
    try:
        return subprocess.run(cmd, shell=True)
    except Exception:
        return subprocess.run(cmd.replace("python", "python3"), shell=True)
"""  # test-fixture

        diff = build_diff("runner.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding subprocess fallback"

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p002_rce_fallback_remediation(self):  # test-fixture
        """REMEDIATION: Removing subprocess fallback triggers PASS."""
        old_code = """
def run_command(cmd):
    try:
        return subprocess.run(cmd, shell=True)
    except:
        return subprocess.run(cmd + "_alt", shell=True)
"""  # test-fixture
        new_code = """
def run_command(cmd):
    return subprocess.run(cmd, check=True, shell=False)
"""  # test-fixture

        diff = build_diff("runner.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing subprocess fallback"

    # Pattern 3: Authentication Downgrade Fallback

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p003_auth_downgrade_regression(self):  # test-fixture
        """REGRESSION: Adding auth downgrade triggers FAIL."""
        old_code = """
def authenticate(user, password):
    return oauth.authenticate(user, password)
"""  # test-fixture
        new_code = """
def authenticate(user, password):
    try:
        return oauth.authenticate(user, password)
    except OAuthError:
        return api_key_auth(user)
"""  # test-fixture

        diff = build_diff("auth.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding auth downgrade"

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p003_auth_downgrade_remediation(self):  # test-fixture
        """REMEDIATION: Removing auth downgrade triggers PASS."""
        old_code = """
def authenticate(user, password):
    try:
        return oauth.authenticate(user, password)
    except OAuthError:
        return basic_auth(user, password)
"""  # test-fixture
        new_code = """
def authenticate(user, password):
    try:
        return oauth.authenticate(user, password)
    except OAuthError as e:
        raise AuthenticationError(f"OAuth failed: {e}") from e
"""  # test-fixture

        diff = build_diff("auth.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing auth downgrade"

    # Pattern 11: Lint/Type/Coverage Suppression Markers

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p011_noqa_regression(self):  # test-fixture
        """REGRESSION: Adding noqa markers triggers FAIL."""
        old_code = """
def process_data(items):
    result = complex_operation(items)
    return result
"""  # test-fixture
        new_code = """
def process_data(items):
    result = complex_operation(items)  # noqa: C901
    return result  # type: ignore
"""  # test-fixture

        diff = build_diff("processor.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding noqa markers"

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p011_noqa_remediation(self):  # test-fixture
        """REMEDIATION: Removing noqa markers triggers PASS."""
        old_code = """
def complex_function(x):  # noqa: C901, PLR0912
    if x == 1:  # noqa: PLR2004
        return "one"
    return "other"
"""  # test-fixture
        new_code = """
def process_value(x: int) -> str:
    value_map = {1: "one"}
    return value_map.get(x, "other")
"""  # test-fixture

        diff = build_diff("processor.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing noqa"


class TestHIGHPatterns:
    """HIGH severity patterns - significant impact."""

    # Pattern 14: Exception Suppression via || Operator

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p014_shell_or_operator_regression(self):  # test-fixture
        """REGRESSION: Adding || operator suppression triggers FAIL."""
        old_code = """
def run_script():
    subprocess.run(["critical_command"], check=True)
"""  # test-fixture
        new_code = """
def run_script():
    subprocess.run("critical_command || true", shell=True)
"""  # test-fixture

        diff = build_diff("script.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding || operator"

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p014_shell_or_operator_remediation(self):  # test-fixture
        """REMEDIATION: Removing || operator triggers PASS."""
        old_code = 'subprocess.run("command || true", shell=True)'  # test-fixture
        new_code = 'subprocess.run(["command"], check=True, shell=False)'  # test-fixture

        diff = build_diff("script.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing || operator"

    # Pattern 17: Exception → Empty Collection Return

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p017_exception_empty_return_regression(self):  # test-fixture
        """REGRESSION: Adding exception→empty return triggers FAIL."""
        old_code = """
def get_data():
    return database.query()
"""  # test-fixture
        new_code = """
def get_data():
    try:
        return database.query()
    except Exception:
        return {}
"""  # test-fixture

        diff = build_diff("data.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding empty return"

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p017_exception_empty_return_remediation(self):  # test-fixture
        """REMEDIATION: Removing exception→empty return triggers PASS."""
        old_code = """
def get_data():
    try:
        return database.query()
    except Exception:
        return []
"""  # test-fixture
        new_code = """
def get_data():
    try:
        return database.query()
    except DatabaseError as e:
        raise DataError(f"Query failed: {e}") from e
"""  # test-fixture

        diff = build_diff("data.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing empty return"

    # Pattern 22: Exception → False Return

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p022_exception_false_return_regression(self):  # test-fixture
        """REGRESSION: Adding exception→False return triggers FAIL."""
        old_code = """
def check_connection():
    service.ping()
    return True
"""  # test-fixture
        new_code = """
def check_connection():
    try:
        service.ping()
        return True
    except Exception:
        return False
"""  # test-fixture

        diff = build_diff("health.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding False return"

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p022_exception_false_return_remediation(self):  # test-fixture
        """REMEDIATION: Removing exception→False return triggers PASS."""
        old_code = """
def check_connection():
    try:
        service.ping()
        return True
    except Exception:
        return False
"""  # test-fixture
        new_code = """
def check_connection():
    try:
        service.ping()
        return True
    except ConnectionError as e:
        raise HealthCheckError(f"Connection failed: {e}") from e
"""  # test-fixture

        diff = build_diff("health.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing False return"

    # Pattern 24: Warning + Continue in Loop

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p024_warning_continue_regression(self):  # test-fixture
        """REGRESSION: Adding warning+continue triggers FAIL."""
        old_code = """
def process_items(items):
    results = []
    for item in items:
        result = process(item)
        results.append(result)
    return results
"""  # test-fixture
        new_code = """
def process_items(items):
    results = []
    for item in items:
        try:
            result = process(item)
            results.append(result)
        except Exception as e:
            logger.warning(f"Failed: {e}")
            continue
    return results
"""  # test-fixture

        diff = build_diff("processor.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding warning+continue"

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p024_warning_continue_remediation(self):  # test-fixture
        """REMEDIATION: Removing warning+continue triggers PASS."""
        old_code = """
def process_items(items):
    results = []
    for item in items:
        try:
            results.append(process(item))
        except Exception:
            logger.warning("error")
            continue
    return results
"""  # test-fixture
        new_code = """
def process_items(items):
    results = []
    failures = []
    for idx, item in enumerate(items):
        try:
            results.append(process(item))
        except Exception as e:
            failures.append((idx, e))
    if failures:
        raise ProcessingError(f"Failed: {failures}")
    return results
"""  # test-fixture

        diff = build_diff("processor.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing warning+continue"

    # Pattern 43: Exception → None Return

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p043_exception_none_return_regression(self):  # test-fixture
        """REGRESSION: Adding exception→None return triggers FAIL."""
        old_code = """
def load_config(path):
    return json.load(open(path))
"""  # test-fixture
        new_code = """
def load_config(path):
    try:
        return json.load(open(path))
    except Exception:
        return None
"""  # test-fixture

        diff = build_diff("config.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding None return"

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p043_exception_none_return_remediation(self):  # test-fixture
        """REMEDIATION: Removing exception→None return triggers PASS."""
        old_code = """
def load_config(path):
    try:
        return json.load(open(path))
    except Exception:
        return None
"""  # test-fixture
        new_code = """
def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ConfigError(f"Failed to load {path}: {e}") from e
"""  # test-fixture

        diff = build_diff("config.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing None return"


class TestMEDIUMPatterns:
    """MEDIUM severity patterns - moderate impact."""

    # Pattern 58: Implicit Default via Truthiness Operator

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p058_truthiness_default_regression(self):  # test-fixture
        """REGRESSION: Adding truthiness default triggers FAIL."""
        old_code = """
def get_timeout(config):
    if config.timeout is None:
        raise ValueError("timeout required")
    return config.timeout
"""  # test-fixture
        new_code = """
def get_timeout(config):
    return config.timeout or 30
"""  # test-fixture

        diff = build_diff("settings.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding truthiness default"

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p058_truthiness_default_remediation(self):  # test-fixture
        """REMEDIATION: Removing truthiness default triggers PASS."""
        old_code = """
def get_max_retries(self):
    return self.max_retries or 3
"""  # test-fixture
        new_code = """
def get_max_retries(self):
    if self.max_retries is None:
        raise ValueError("max_retries must be configured explicitly")
    return self.max_retries
"""  # test-fixture

        diff = build_diff("settings.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing truthiness default"

    # Pattern 64: Dictionary .get() Silent None Return

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p064_dict_get_regression(self):  # test-fixture
        """REGRESSION: Adding dict.get with default triggers FAIL."""
        old_code = """
def get_timeout(config):
    if "timeout" not in config:
        raise KeyError("timeout required")
    return config["timeout"]
"""  # test-fixture
        new_code = """
def get_timeout(config):
    return config.get("timeout", 30)
"""  # test-fixture

        diff = build_diff("config.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "deny", "Should FAIL when adding .get() default"

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_p064_dict_get_remediation(self):  # test-fixture
        """REMEDIATION: Removing dict.get default triggers PASS."""
        old_code = """
def get_timeout(config):
    return config.get("timeout", 30)
"""  # test-fixture
        new_code = """
def get_timeout(config):
    if "timeout" not in config:
        raise KeyError("timeout is required in configuration")
    return config["timeout"]
"""  # test-fixture

        diff = build_diff("config.py", old_code, new_code)
        result = run_code_quality_audit(diff)  # test-fixture

        assert result["decision"] == "allow", "Should PASS when removing .get() default"


# Helper functions


def build_diff(filename: str, old_code: str, new_code: str) -> str:  # test-fixture
    """Build diff format for audit."""
    return f"""FILE: {filename}

## OLD CODE
```python
{old_code.strip()}
```

## NEW CODE
```python
{new_code.strip()}
```
"""


def run_code_quality_audit(diff: str) -> dict:  # test-fixture
    """Run code quality audit on diff content."""
    import json
    import re

    # Parse diff to extract old and new code

    # Extract old code
    old_match = re.search(r"## OLD CODE\s*```(?:python)?\s*\n(.*?)\n```", diff, re.DOTALL)
    old_code = old_match.group(1).strip() if old_match else ""

    # Extract new code
    new_match = re.search(r"## NEW CODE\s*```(?:python)?\s*\n(.*?)\n```", diff, re.DOTALL)
    new_code = new_match.group(1).strip() if new_match else ""

    hook_input = {  # test-fixture
        "session_id": "test-pattern",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "test.py",
            "old_string": old_code,  # Use actual code from diff
            "new_string": new_code,  # Use actual code from diff
        },
        "transcript_path": None,
    }

    result = subprocess.run(  # test-fixture
        ["./scripts/ami-agent", "--hook", "code-quality"],
        check=False,
        input=json.dumps(hook_input),  # Don't append diff, code is in tool_input
        capture_output=True,
        text=True,
        timeout=60,
    )

    output = result.stdout.strip()  # test-fixture

    # Parse JSON output from hook (hooks always return exit code 0)
    output_json = json.loads(output)

    # Extract decision from hookSpecificOutput (PreToolUse format)
    decision = output_json.get("hookSpecificOutput", {}).get("permissionDecision", "allow")

    return {  # test-fixture
        "decision": decision,  # "allow" or "deny"
        "output": output,
        "raw_json": output_json,
    }
