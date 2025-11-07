"""Unit tests for automation.agent_cli module."""

import tempfile
from pathlib import Path

import pytest

# Import will fail until we implement agent_cli.py - that's expected in TDD
try:
    from scripts.automation.agent_cli import (
        ALL_TOOLS_EXCEPT_TASK,
        AgentConfig,
        AgentConfigPresets,
        ClaudeAgentCLI,
        ClaudeModels,
        CLIProvider,
        GeminiAgentCLI,
        GeminiModels,
        get_agent_cli,
    )
except ImportError:
    ALL_TOOLS_EXCEPT_TASK = None
    AgentConfig = None
    AgentConfigPresets = None
    CLIProvider = None
    ClaudeAgentCLI = None
    ClaudeModels = None
    GeminiAgentCLI = None
    GeminiModels = None
    get_agent_cli = None

# Test constants
DEFAULT_TIMEOUT = 180
AUDIT_DIFF_TIMEOUT = 60
CONSOLIDATE_TIMEOUT = 300
ALL_TOOLS_COUNT = 15
TOOLS_WITHOUT_WEB_COUNT = 13


class TestAgentConfig:
    """Unit tests for AgentConfig dataclass."""

    @pytest.mark.skipif(AgentConfig is None, reason="AgentConfig not implemented yet")
    def test_create_basic_config(self):
        """AgentConfig creates with required fields."""
        config = AgentConfig(provider=CLIProvider.CLAUDE, model="claude-sonnet-4-5", session_id="test-session")

        assert config.provider == CLIProvider.CLAUDE
        assert config.model == "claude-sonnet-4-5"
        assert config.allowed_tools is None
        assert config.enable_hooks is True
        assert config.timeout == DEFAULT_TIMEOUT

    @pytest.mark.skipif(AgentConfig is None, reason="AgentConfig not implemented yet")
    def test_default_allowed_tools(self):
        """AgentConfig defaults allowed_tools to None."""
        config = AgentConfig(provider=CLIProvider.CLAUDE, model="test-model", session_id="test-session")

        assert config.allowed_tools is None  # All tools allowed

    @pytest.mark.skipif(AgentConfig is None, reason="AgentConfig not implemented yet")
    def test_default_enable_hooks(self):
        """AgentConfig defaults enable_hooks to True."""
        config = AgentConfig(provider=CLIProvider.CLAUDE, model="test-model", session_id="test-session")

        assert config.enable_hooks is True

    @pytest.mark.skipif(AgentConfig is None, reason="AgentConfig not implemented yet")
    def test_default_timeout(self):
        """AgentConfig defaults timeout to 180."""
        config = AgentConfig(provider=CLIProvider.CLAUDE, model="test-model", session_id="test-session")

        assert config.timeout == DEFAULT_TIMEOUT


class TestAgentConfigPresets:
    """Unit tests for AgentConfigPresets."""

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_audit_preset(self):
        """audit() preset has correct config."""
        config = AgentConfigPresets.audit(session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert "WebSearch" in config.allowed_tools
        assert "WebFetch" in config.allowed_tools
        assert config.enable_hooks is False
        assert config.timeout == DEFAULT_TIMEOUT

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_audit_diff_preset(self):
        """audit_diff() preset has correct config."""
        config = AgentConfigPresets.audit_diff(session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert "WebSearch" in config.allowed_tools
        assert "WebFetch" in config.allowed_tools
        assert config.enable_hooks is False
        assert config.timeout == AUDIT_DIFF_TIMEOUT

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_consolidate_preset(self):
        """consolidate() preset has correct config."""
        config = AgentConfigPresets.consolidate(session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert "Read" in config.allowed_tools
        assert "Write" in config.allowed_tools
        assert "Edit" in config.allowed_tools
        assert config.enable_hooks is False
        assert config.timeout == CONSOLIDATE_TIMEOUT

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_worker_preset(self):
        """worker() preset has correct config."""
        config = AgentConfigPresets.worker(session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert config.allowed_tools == ALL_TOOLS_EXCEPT_TASK  # All tools except Task
        assert config.enable_hooks is True
        assert config.timeout == DEFAULT_TIMEOUT

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_interactive_preset(self):
        """interactive() preset has correct config."""
        config = AgentConfigPresets.interactive(session_id="test-session")

        assert config.model == "claude-sonnet-4-5"
        assert config.allowed_tools == ALL_TOOLS_EXCEPT_TASK  # All tools except Task
        assert config.enable_hooks is True
        assert config.timeout is None  # No timeout


class TestClaudeAgentCLI:
    """Unit tests for ClaudeAgentCLI."""

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_all_tools_list_complete(self):
        """ALL_TOOLS contains all Claude Code tools."""
        # Should have 15 tools
        assert len(ClaudeAgentCLI.ALL_TOOLS) == ALL_TOOLS_COUNT
        assert "Bash" in ClaudeAgentCLI.ALL_TOOLS
        assert "Read" in ClaudeAgentCLI.ALL_TOOLS
        assert "Write" in ClaudeAgentCLI.ALL_TOOLS
        assert "WebSearch" in ClaudeAgentCLI.ALL_TOOLS

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_compute_disallowed_tools_none(self):
        """compute_disallowed_tools(None) returns []."""
        result = ClaudeAgentCLI.compute_disallowed_tools(None)

        assert result == []

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
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

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_compute_disallowed_tools_unknown_tool(self):
        """compute_disallowed_tools() raises on unknown tool."""
        with pytest.raises(ValueError) as exc_info:
            ClaudeAgentCLI.compute_disallowed_tools(["UnknownTool"])

        assert "unknown" in str(exc_info.value).lower()

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
    def test_compute_disallowed_tools_sorted(self):
        """compute_disallowed_tools() returns sorted list."""
        result = ClaudeAgentCLI.compute_disallowed_tools(["Bash"])

        # Should be sorted
        assert result == sorted(result)

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
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

    @pytest.mark.skipif(ClaudeAgentCLI is None, reason="ClaudeAgentCLI not implemented yet")
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

    @pytest.mark.skipif(get_agent_cli is None, reason="get_agent_cli not implemented yet")
    def test_get_agent_cli_returns_claude(self):
        """get_agent_cli() returns ClaudeAgentCLI."""
        cli = get_agent_cli()

        assert isinstance(cli, ClaudeAgentCLI)


class TestCLIProvider:
    """Unit tests for CLIProvider enum."""

    @pytest.mark.skipif(CLIProvider is None, reason="CLIProvider not implemented yet")
    def test_claude_provider_value(self):
        """CLIProvider.CLAUDE has correct value."""
        assert CLIProvider.CLAUDE.value == "claude"

    @pytest.mark.skipif(CLIProvider is None, reason="CLIProvider not implemented yet")
    def test_gemini_provider_value(self):
        """CLIProvider.GEMINI has correct value."""
        assert CLIProvider.GEMINI.value == "gemini"

    @pytest.mark.skipif(CLIProvider is None, reason="CLIProvider not implemented yet")
    def test_provider_enum_has_two_values(self):
        """CLIProvider enum has exactly two providers."""
        assert len(list(CLIProvider)) == 2


class TestClaudeModels:
    """Unit tests for ClaudeModels enum."""

    @pytest.mark.skipif(ClaudeModels is None, reason="ClaudeModels not implemented yet")
    def test_sonnet_4_5_value(self):
        """ClaudeModels.SONNET_4_5 has correct value."""
        assert ClaudeModels.SONNET_4_5.value == "claude-sonnet-4-5"

    @pytest.mark.skipif(ClaudeModels is None, reason="ClaudeModels not implemented yet")
    def test_sonnet_3_5_value(self):
        """ClaudeModels.SONNET_3_5 has correct value."""
        assert ClaudeModels.SONNET_3_5.value == "claude-sonnet-3-5"

    @pytest.mark.skipif(ClaudeModels is None, reason="ClaudeModels not implemented yet")
    def test_opus_4_value(self):
        """ClaudeModels.OPUS_4 has correct value."""
        assert ClaudeModels.OPUS_4.value == "claude-opus-4"

    @pytest.mark.skipif(ClaudeModels is None, reason="ClaudeModels not implemented yet")
    def test_haiku_3_5_value(self):
        """ClaudeModels.HAIKU_3_5 has correct value."""
        assert ClaudeModels.HAIKU_3_5.value == "claude-haiku-3-5"

    @pytest.mark.skipif(ClaudeModels is None, reason="ClaudeModels not implemented yet")
    def test_is_valid_accepts_valid_model(self):
        """ClaudeModels.is_valid() returns True for valid models."""
        assert ClaudeModels.is_valid("claude-sonnet-4-5")
        assert ClaudeModels.is_valid("claude-sonnet-3-5")
        assert ClaudeModels.is_valid("claude-opus-4")
        assert ClaudeModels.is_valid("claude-haiku-3-5")

    @pytest.mark.skipif(ClaudeModels is None, reason="ClaudeModels not implemented yet")
    def test_is_valid_rejects_invalid_model(self):
        """ClaudeModels.is_valid() returns False for invalid models."""
        assert not ClaudeModels.is_valid("gemini-2.5-pro")
        assert not ClaudeModels.is_valid("claude-invalid-model")
        assert not ClaudeModels.is_valid("")

    @pytest.mark.skipif(ClaudeModels is None, reason="ClaudeModels not implemented yet")
    def test_get_default_returns_sonnet_4_5(self):
        """ClaudeModels.get_default() returns claude-sonnet-4-5."""
        default = ClaudeModels.get_default()
        assert default == "claude-sonnet-4-5"


class TestGeminiModels:
    """Unit tests for GeminiModels enum."""

    @pytest.mark.skipif(GeminiModels is None, reason="GeminiModels not implemented yet")
    def test_pro_2_5_value(self):
        """GeminiModels.PRO_2_5 has correct value."""
        assert GeminiModels.PRO_2_5.value == "gemini-2.5-pro"

    @pytest.mark.skipif(GeminiModels is None, reason="GeminiModels not implemented yet")
    def test_flash_2_5_value(self):
        """GeminiModels.FLASH_2_5 has correct value."""
        assert GeminiModels.FLASH_2_5.value == "gemini-2.5-flash"

    @pytest.mark.skipif(GeminiModels is None, reason="GeminiModels not implemented yet")
    def test_pro_2_0_value(self):
        """GeminiModels.PRO_2_0 has correct value."""
        assert GeminiModels.PRO_2_0.value == "gemini-2.0-pro"

    @pytest.mark.skipif(GeminiModels is None, reason="GeminiModels not implemented yet")
    def test_flash_2_0_value(self):
        """GeminiModels.FLASH_2_0 has correct value."""
        assert GeminiModels.FLASH_2_0.value == "gemini-2.0-flash"

    @pytest.mark.skipif(GeminiModels is None, reason="GeminiModels not implemented yet")
    def test_is_valid_accepts_valid_model(self):
        """GeminiModels.is_valid() returns True for valid models."""
        assert GeminiModels.is_valid("gemini-2.5-pro")
        assert GeminiModels.is_valid("gemini-2.5-flash")
        assert GeminiModels.is_valid("gemini-2.0-pro")
        assert GeminiModels.is_valid("gemini-2.0-flash")

    @pytest.mark.skipif(GeminiModels is None, reason="GeminiModels not implemented yet")
    def test_is_valid_rejects_invalid_model(self):
        """GeminiModels.is_valid() returns False for invalid models."""
        assert not GeminiModels.is_valid("claude-sonnet-4-5")
        assert not GeminiModels.is_valid("gemini-invalid-model")
        assert not GeminiModels.is_valid("")

    @pytest.mark.skipif(GeminiModels is None, reason="GeminiModels not implemented yet")
    def test_get_default_returns_pro_2_5(self):
        """GeminiModels.get_default() returns gemini-2.5-pro."""
        default = GeminiModels.get_default()
        assert default == "gemini-2.5-pro"


class TestMultiProviderFactory:
    """Unit tests for multi-provider get_agent_cli() factory."""

    @pytest.mark.skipif(get_agent_cli is None, reason="get_agent_cli not implemented yet")
    def test_returns_claude_for_claude_config(self):
        """get_agent_cli() returns ClaudeAgentCLI for Claude config."""
        config = AgentConfig(provider=CLIProvider.CLAUDE, model="claude-sonnet-4-5", session_id="test")
        cli = get_agent_cli(config)
        assert isinstance(cli, ClaudeAgentCLI)

    @pytest.mark.skipif(get_agent_cli is None, reason="get_agent_cli not implemented yet")
    def test_returns_gemini_for_gemini_config(self):
        """get_agent_cli() returns GeminiAgentCLI for Gemini config."""
        config = AgentConfig(provider=CLIProvider.GEMINI, model="gemini-2.5-pro", session_id="test")
        cli = get_agent_cli(config)
        assert isinstance(cli, GeminiAgentCLI)

    @pytest.mark.skipif(get_agent_cli is None, reason="get_agent_cli not implemented yet")
    def test_defaults_to_claude_when_no_config(self):
        """get_agent_cli() defaults to Claude when no config provided."""
        cli = get_agent_cli()
        assert isinstance(cli, ClaudeAgentCLI)

    @pytest.mark.skipif(get_agent_cli is None, reason="get_agent_cli not implemented yet")
    def test_explicit_provider_parameter_overrides_config(self):
        """get_agent_cli() explicit provider param overrides config provider."""
        config = AgentConfig(provider=CLIProvider.CLAUDE, model="claude-sonnet-4-5", session_id="test")
        cli = get_agent_cli(config, provider=CLIProvider.GEMINI)
        assert isinstance(cli, GeminiAgentCLI)


class TestAgentConfigWithProvider:
    """Unit tests for AgentConfig with provider field."""

    @pytest.mark.skipif(AgentConfig is None, reason="AgentConfig not implemented yet")
    def test_config_requires_provider_field(self):
        """AgentConfig requires provider as first field."""
        config = AgentConfig(provider=CLIProvider.CLAUDE, model="claude-sonnet-4-5", session_id="test")
        assert config.provider == CLIProvider.CLAUDE
        assert config.model == "claude-sonnet-4-5"
        assert config.session_id == "test"

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_presets_include_provider(self):
        """AgentConfigPresets include provider=CLIProvider.CLAUDE."""
        presets = [
            AgentConfigPresets.audit("test"),
            AgentConfigPresets.audit_diff("test"),
            AgentConfigPresets.worker("test"),
            AgentConfigPresets.task_worker("test"),
        ]
        for preset in presets:
            assert preset.provider == CLIProvider.CLAUDE


class TestGeminiAgentCLI:
    """Unit tests for GeminiAgentCLI implementation."""

    @pytest.mark.skipif(GeminiAgentCLI is None, reason="GeminiAgentCLI not implemented yet")
    def test_get_provider_returns_gemini(self):
        """GeminiAgentCLI.get_provider() returns CLIProvider.GEMINI."""
        cli = GeminiAgentCLI()
        assert cli.get_provider() == CLIProvider.GEMINI

    @pytest.mark.skipif(GeminiAgentCLI is None, reason="GeminiAgentCLI not implemented yet")
    def test_get_all_tools_returns_gemini_tools(self):
        """GeminiAgentCLI.get_all_tools() returns Gemini tool names."""
        cli = GeminiAgentCLI()
        tools = cli.get_all_tools()
        assert "read_file" in tools
        assert "write_file" in tools
        assert "run_shell_command" in tools

    @pytest.mark.skipif(GeminiAgentCLI is None, reason="GeminiAgentCLI not implemented yet")
    def test_map_tool_name_read(self):
        """GeminiAgentCLI.map_tool_name() maps Read to read_file."""
        cli = GeminiAgentCLI()
        assert cli.map_tool_name("Read") == "read_file"

    @pytest.mark.skipif(GeminiAgentCLI is None, reason="GeminiAgentCLI not implemented yet")
    def test_map_tool_name_write(self):
        """GeminiAgentCLI.map_tool_name() maps Write to write_file."""
        cli = GeminiAgentCLI()
        assert cli.map_tool_name("Write") == "write_file"

    @pytest.mark.skipif(GeminiAgentCLI is None, reason="GeminiAgentCLI not implemented yet")
    def test_map_tool_name_bash(self):
        """GeminiAgentCLI.map_tool_name() maps Bash to run_shell_command."""
        cli = GeminiAgentCLI()
        assert cli.map_tool_name("Bash") == "run_shell_command"

    @pytest.mark.skipif(GeminiAgentCLI is None, reason="GeminiAgentCLI not implemented yet")
    def test_map_tool_name_returns_none_for_unknown(self):
        """GeminiAgentCLI.map_tool_name() returns None for unknown tools."""
        cli = GeminiAgentCLI()
        assert cli.map_tool_name("UnknownTool") is None


class TestConfigurablePresets:
    """Unit tests for configurable worker/moderator presets."""

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_worker_defaults_to_claude(self):
        """Worker presets default to Claude provider."""
        config = AgentConfigPresets.worker("test")
        assert config.provider == CLIProvider.CLAUDE
        assert config.model == "claude-sonnet-4-5"

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_task_worker_defaults_to_claude(self):
        """Task worker preset defaults to Claude provider."""
        config = AgentConfigPresets.task_worker("test")
        assert config.provider == CLIProvider.CLAUDE
        assert config.model == "claude-sonnet-4-5"

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_sync_worker_defaults_to_claude(self):
        """Sync worker preset defaults to Claude provider."""
        config = AgentConfigPresets.sync_worker("test")
        assert config.provider == CLIProvider.CLAUDE
        assert config.model == "claude-sonnet-4-5"

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_task_moderator_defaults_to_claude(self):
        """Task moderator preset defaults to Claude provider."""
        config = AgentConfigPresets.task_moderator("test")
        assert config.provider == CLIProvider.CLAUDE
        assert config.model == "claude-sonnet-4-5"

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_sync_moderator_defaults_to_claude(self):
        """Sync moderator preset defaults to Claude provider."""
        config = AgentConfigPresets.sync_moderator("test")
        assert config.provider == CLIProvider.CLAUDE
        assert config.model == "claude-sonnet-4-5"

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_completion_moderator_defaults_to_claude(self):
        """Completion moderator preset defaults to Claude provider."""
        config = AgentConfigPresets.completion_moderator("test")
        assert config.provider == CLIProvider.CLAUDE
        assert config.model == "claude-sonnet-4-5"

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_worker_respects_env_var_provider(self, monkeypatch):
        """Worker presets respect AMI_AGENT_WORKER_PROVIDER env var."""
        monkeypatch.setenv("AMI_AGENT_WORKER_PROVIDER", "gemini")
        # Force config reload
        from scripts.automation.config import _ConfigSingleton

        _ConfigSingleton.instance = None

        config = AgentConfigPresets.worker("test")
        assert config.provider == CLIProvider.GEMINI
        assert config.model == "gemini-2.5-pro"  # Default for Gemini

        # Cleanup
        _ConfigSingleton.instance = None

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_moderator_respects_env_var_provider(self, monkeypatch):
        """Moderator presets respect AMI_AGENT_MODERATOR_PROVIDER env var."""
        monkeypatch.setenv("AMI_AGENT_MODERATOR_PROVIDER", "gemini")
        # Force config reload
        from scripts.automation.config import _ConfigSingleton

        _ConfigSingleton.instance = None

        config = AgentConfigPresets.task_moderator("test")
        assert config.provider == CLIProvider.GEMINI
        assert config.model == "gemini-2.5-pro"  # Default for Gemini

        # Cleanup
        _ConfigSingleton.instance = None

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_worker_respects_env_var_model(self, monkeypatch):
        """Worker presets respect AMI_AGENT_WORKER_MODEL env var."""
        monkeypatch.setenv("AMI_AGENT_WORKER_PROVIDER", "claude")
        monkeypatch.setenv("AMI_AGENT_WORKER_MODEL", "claude-haiku-3-5")
        # Force config reload
        from scripts.automation.config import _ConfigSingleton

        _ConfigSingleton.instance = None

        config = AgentConfigPresets.worker("test")
        assert config.provider == CLIProvider.CLAUDE
        assert config.model == "claude-haiku-3-5"

        # Cleanup
        _ConfigSingleton.instance = None

    @pytest.mark.skipif(AgentConfigPresets is None, reason="AgentConfigPresets not implemented yet")
    def test_moderator_respects_env_var_model(self, monkeypatch):
        """Moderator presets respect AMI_AGENT_MODERATOR_MODEL env var."""
        monkeypatch.setenv("AMI_AGENT_MODERATOR_PROVIDER", "gemini")
        monkeypatch.setenv("AMI_AGENT_MODERATOR_MODEL", "gemini-2.5-flash")
        # Force config reload
        from scripts.automation.config import _ConfigSingleton

        _ConfigSingleton.instance = None

        config = AgentConfigPresets.task_moderator("test")
        assert config.provider == CLIProvider.GEMINI
        assert config.model == "gemini-2.5-flash"

        # Cleanup
        _ConfigSingleton.instance = None
