"""Tests for scripts/automation/validators.py shared validation logic."""

from scripts.automation.validators import (
    parse_code_fence_output,
    validate_python_patterns,
)

PARENT_PATTERN = ".parent" + ".parent"


class TestParseCodeFenceOutput:
    """Tests for code fence output parsing."""

    def test_parse_simple_text(self):
        """Test parsing plain text without code fences."""
        output = "PASS"
        result = parse_code_fence_output(output)
        assert result == "PASS"

    def test_parse_with_code_fence(self):
        """Test parsing text with code fences."""
        output = "```\nPASS\n```"
        result = parse_code_fence_output(output)
        assert result == "PASS"

    def test_parse_with_language_code_fence(self):
        """Test parsing text with language-specific code fences."""
        output = "```python\nPASS\n```"
        result = parse_code_fence_output(output)
        assert result == "PASS"

    def test_parse_multiline_with_fence(self):
        """Test parsing multiline text with code fences."""
        output = "```\nLine 1\nLine 2\n```"
        result = parse_code_fence_output(output)
        assert result == "Line 1\nLine 2"


class TestValidatePythonPatterns:
    """Tests for Python pattern validation."""

    def test_valid_code(self):
        """Test that valid Python code passes."""
        code = "def foo():\n    return None"
        is_valid, reason = validate_python_patterns("test.py", code)
        assert is_valid is True
        assert reason == ""

    def test_non_empty_init_py(self):
        """Test that non-empty __init__.py is rejected."""
        code = "# some comment"
        is_valid, reason = validate_python_patterns("__init__.py", code)
        assert is_valid is False
        assert "NON-EMPTY __init__.py" in reason

    def test_empty_init_py(self):
        """Test that empty __init__.py is allowed."""
        code = ""
        is_valid, reason = validate_python_patterns("__init__.py", code)
        assert is_valid is True
        assert reason == ""

    def test_parent_parent_pattern(self):
        """Test that forbidden path pattern is rejected."""
        code = f"path = Path(__file__){PARENT_PATTERN}"
        is_valid, reason = validate_python_patterns("test.py", code)
        assert is_valid is False
        assert "FORBIDDEN CODE PATTERN" in reason
        assert "parent" in reason.lower()

    def test_valid_single_parent(self):
        """Test that single .parent is allowed."""
        code = "path = Path(__file__).parent"
        is_valid, reason = validate_python_patterns("test.py", code)
        assert is_valid is True
        assert reason == ""
