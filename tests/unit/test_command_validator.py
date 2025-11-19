"""Unit tests for CommandValidator functionality."""

# Import the implemented hooks functionality
from scripts.agents.workflows.security_validators import CommandValidator


class TestCommandValidator:
    """Unit tests for CommandValidator."""

    def test_validate_allowed_command(self):
        """CommandValidator allows safe commands."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "ls -la"}})()

        result = validator.validate(hook_input)
        assert result.decision is None or result.decision == "allow"

    def test_deny_direct_python(self):
        """CommandValidator denies direct python calls."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "python3 script.py"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "ami-run" in result.reason.lower()

    def test_deny_pip_install(self):
        """CommandValidator denies pip commands."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "pip install package"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "pyproject.toml" in result.reason or "ami-uv" in result.reason

    def test_deny_direct_uv(self):
        """CommandValidator denies direct uv."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "uv pip install package"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "ami-uv" in result.reason.lower()

    def test_deny_git_commit(self):
        """CommandValidator denies direct git commit."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "message"'}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "git_commit.sh" in result.reason

    def test_deny_git_push(self):
        """CommandValidator denies direct git push."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "git_push.sh" in result.reason

    def test_deny_hook_bypass(self):
        """CommandValidator denies --no-verify."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": 'git commit --no-verify -m "msg"'}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "bypass" in result.reason.lower() or "forbidden" in result.reason.lower()

    def test_deny_background_ampersand(self):
        """CommandValidator denies & operator."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "long_command &"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "run_in_background" in result.reason or "&" in result.reason

    def test_deny_semicolon(self):
        """CommandValidator denies semicolon."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "cmd1; cmd2"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "separate" in result.reason.lower() or "&&" in result.reason

    def test_deny_or_operator(self):
        """CommandValidator denies || operator."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "cmd1 || cmd2"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "||" in result.reason or "separate" in result.reason.lower()

    def test_deny_append_redirect(self):
        """CommandValidator denies >> redirect."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "echo text >> file.txt"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "edit" in result.reason.lower() or "write" in result.reason.lower()

    def test_deny_sed_inplace(self):
        """CommandValidator denies sed -i."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "sed -i 's/old/new/' file.txt"}})()

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "edit" in result.reason.lower()

    def test_deny_and_operator(self):
        """CommandValidator denies && operator."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Bash", "tool_input": {"command": "echo test && ls"}})()

        result = validator.validate(hook_input)
        # Should deny && operator
        assert result.decision == "deny"
        assert "&&" in result.reason or "and" in result.reason.lower() or "separate" in result.reason.lower()

    def test_non_bash_tool_allowed(self):
        """CommandValidator ignores non-Bash tools."""
        validator = CommandValidator()

        hook_input = type("obj", (object,), {"tool_name": "Read", "tool_input": {"file_path": "/some/file.txt"}})()

        result = validator.validate(hook_input)
        assert result.decision is None or result.decision == "allow"
