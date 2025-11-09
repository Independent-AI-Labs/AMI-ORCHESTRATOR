"""Unit tests for automation.agent_cli module."""

import tempfile
from pathlib import Path

import pytest

from scripts.automation.agent_cli import (
    AgentConfig,
    AgentConfigPresets,
    ClaudeAgentCLI,
    get_agent_cli,
)

# Test constants
DEFAULT_TIMEOUT = 180
AUDIT_DIFF_TIMEOUT = 60
CONSOLIDATE_TIMEOUT = 300
ALL_TOOLS_COUNT = 15
TOOLS_WITHOUT_WEB_COUNT = 13


class TestAgentConfig:
    """Unit tests for AgentConfig dataclass."""

    def test_create_basic_config(self):
        """AgentConfig creates with required fields."""
        config = AgentConfig(model="claude-sonnet-4-5", session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert config.session_id == "test-session"
        assert config.allowed_tools is None
        assert config.enable_hooks is True
        assert config.timeout == DEFAULT_TIMEOUT

    def test_default_allowed_tools(self):
        """AgentConfig defaults allowed_tools to None."""
        config = AgentConfig(model="test-model", session_id="test-session")

        assert config.allowed_tools is None  # All tools allowed

    def test_default_enable_hooks(self):
        """AgentConfig defaults enable_hooks to True."""
        config = AgentConfig(model="test-model", session_id="test-session")

        assert config.enable_hooks is True

    def test_default_timeout(self):
        """AgentConfig defaults timeout to 180."""
        config = AgentConfig(model="test-model", session_id="test-session")

        assert config.timeout == DEFAULT_TIMEOUT


class TestAgentConfigPresets:
    """Unit tests for AgentConfigPresets."""

    def test_audit_preset(self):
        """audit() preset has correct config."""
        config = AgentConfigPresets.audit(session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert "WebSearch" in config.allowed_tools
        assert "WebFetch" in config.allowed_tools
        assert config.enable_hooks is False
        assert config.timeout == DEFAULT_TIMEOUT

    def test_audit_diff_preset(self):
        """audit_diff() preset has correct config."""
        config = AgentConfigPresets.audit_diff(session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert "WebSearch" in config.allowed_tools
        assert "WebFetch" in config.allowed_tools
        assert config.enable_hooks is False
        assert config.timeout == AUDIT_DIFF_TIMEOUT

    def test_consolidate_preset(self):
        """consolidate() preset has correct config."""
        config = AgentConfigPresets.consolidate(session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert "Read" in config.allowed_tools
        assert "Write" in config.allowed_tools
        assert "Edit" in config.allowed_tools
        assert config.enable_hooks is False
        assert config.timeout == CONSOLIDATE_TIMEOUT

    def test_worker_preset(self):
        """worker() preset has correct config."""
        config = AgentConfigPresets.worker(session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert config.allowed_tools is None  # All tools allowed
        assert config.enable_hooks is True
        assert config.timeout == DEFAULT_TIMEOUT

    def test_interactive_preset(self):
        """interactive() preset has correct config."""
        config = AgentConfigPresets.interactive(session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert config.allowed_tools is None  # All tools allowed
        assert config.enable_hooks is True
        assert config.timeout is None  # No timeout


class TestClaudeAgentCLI:
    """Unit tests for ClaudeAgentCLI."""

    def test_all_tools_list_complete(self):
        """ALL_TOOLS contains all Claude Code tools."""
        # Should have 15 tools
        assert len(ClaudeAgentCLI.ALL_TOOLS) == ALL_TOOLS_COUNT
        assert "Bash" in ClaudeAgentCLI.ALL_TOOLS
        assert "Read" in ClaudeAgentCLI.ALL_TOOLS
        assert "Write" in ClaudeAgentCLI.ALL_TOOLS
        assert "WebSearch" in ClaudeAgentCLI.ALL_TOOLS

    def test_compute_disallowed_tools_none(self):
        """compute_disallowed_tools(None) returns []."""
        result = ClaudeAgentCLI.compute_disallowed_tools(None)

        assert result == []

    def test_compute_disallowed_tools_complement(self):
        """compute_disallowed_tools() returns complement."""
        allowed = ["WebSearch", "WebFetch"]
        result = ClaudeAgentCLI.compute_disallowed_tools(allowed)

        # Should have 13 tools (15 - 2)
        assert len(result) == TOOLS_WITHOUT_WEB_COUNT
        assert "WebSearch" not in result
        assert "WebFetch" not in result
        assert "Bash" in result
        assert "Read" in result

    def test_compute_disallowed_tools_unknown_tool(self):
        """compute_disallowed_tools() raises on unknown tool."""
        with pytest.raises(ValueError) as exc_info:
            ClaudeAgentCLI.compute_disallowed_tools(["UnknownTool"])

        assert "unknown" in str(exc_info.value).lower()

    def test_compute_disallowed_tools_sorted(self):
        """compute_disallowed_tools() returns sorted list."""
        result = ClaudeAgentCLI.compute_disallowed_tools(["Bash"])

        # Should be sorted
        assert result == sorted(result)

    def test_load_instruction_from_file(self):
        """_load_instruction() reads file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test instruction")
            temp_path = Path(f.name)

        try:
            cli = ClaudeAgentCLI()
            result = cli._load_instruction(temp_path)

            assert "Test instruction" in result
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_load_instruction_template_substitution(self):
        """_load_instruction() substitutes {date}."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Date: {date}")
            temp_path = Path(f.name)

        try:
            cli = ClaudeAgentCLI()
            result = cli._load_instruction(temp_path)

            # {date} should be replaced
            assert "{date}" not in result
            # Should contain actual date
            assert "Date:" in result
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_get_agent_cli_returns_claude(self):
        """get_agent_cli() returns ClaudeAgentCLI."""
        cli = get_agent_cli()

        assert isinstance(cli, ClaudeAgentCLI)
