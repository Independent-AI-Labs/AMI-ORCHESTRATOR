"""Unit tests for QwenAgentCLI."""

import tempfile
from pathlib import Path

import pytest

from scripts.agents.cli.config import AgentConfig
from scripts.agents.cli.provider_type import ProviderType
from scripts.agents.cli.qwen_cli import QwenAgentCLI
from scripts.agents.cli.streaming_utils import load_instruction_with_replacements


class TestQwenAgentCLI:
    """Unit tests for QwenAgentCLI."""

    def test_all_tools_list_complete(self):
        """ALL_TOOLS contains all Qwen Code tools."""
        # Should have the main tools
        assert len(QwenAgentCLI.ALL_TOOLS) > 0
        assert "read_file" in QwenAgentCLI.ALL_TOOLS
        assert "write_file" in QwenAgentCLI.ALL_TOOLS
        assert "edit" in QwenAgentCLI.ALL_TOOLS
        assert "run_shell_command" in QwenAgentCLI.ALL_TOOLS

    def test_compute_disallowed_tools_none(self):
        """compute_disallowed_tools(None) returns []."""
        result = QwenAgentCLI.compute_disallowed_tools(None)

        assert result == []

    def test_compute_disallowed_tools_complement(self):
        """compute_disallowed_tools() returns complement."""
        allowed = ["read_file", "write_file"]
        result = QwenAgentCLI.compute_disallowed_tools(allowed)

        # Should not contain allowed tools
        assert "read_file" not in result
        assert "write_file" not in result
        # Should contain other tools
        assert "edit" in result or "run_shell_command" in result

    def test_compute_disallowed_tools_unknown_tool(self):
        """compute_disallowed_tools() raises on unknown tool."""
        with pytest.raises(ValueError) as exc_info:
            QwenAgentCLI.compute_disallowed_tools(["UnknownTool"])

        assert "unknown" in str(exc_info.value).lower()

    def test_compute_disallowed_tools_sorted(self):
        """compute_disallowed_tools() returns sorted list."""
        result = QwenAgentCLI.compute_disallowed_tools(["edit"])

        # Should be sorted
        assert result == sorted(result)

    def test_get_default_config(self):
        """_get_default_config() returns proper default config."""
        cli = QwenAgentCLI()
        config = cli._get_default_config()

        assert config.model == "qwen-coder"
        assert config.provider == ProviderType.QWEN
        assert config.allowed_tools is None
        assert config.enable_hooks is True
        assert config.timeout == 180

    def test_build_command_basic(self):
        """_build_command() creates basic command correctly."""
        cli = QwenAgentCLI()
        config = AgentConfig(model="qwen-coder", session_id="test-session", provider=ProviderType.QWEN)

        cmd = cli._build_command("test instruction", None, config)

        # Should start with qwen command
        assert len(cmd) > 0
        # The exact command depends on the config, but it should have model and instruction
        assert "--model" in cmd
        assert "qwen-coder" in cmd

    def test_load_instruction_from_file(self):
        """load_instruction_with_replacements() reads file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test instruction")
            temp_path = Path(f.name)

        try:
            result = load_instruction_with_replacements(temp_path)

            assert "Test instruction" in result
        finally:
            if temp_path.exists():
                temp_path.unlink()
