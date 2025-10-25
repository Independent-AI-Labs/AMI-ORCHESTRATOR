"""Tests for bash command guard enforcement in all agents."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest

from scripts.automation.agent_cli import AgentConfigPresets, ClaudeAgentCLI


class TestBashHooksEnforcement:
    """Tests for bash command guard being ALWAYS enabled."""

    @pytest.fixture
    def agent_cli(self) -> Generator[ClaudeAgentCLI, None, None]:
        """Create ClaudeAgentCLI instance with mocked config."""
        with patch("scripts.automation.agent_cli.get_config") as mock_config, patch("scripts.automation.agent_cli.get_logger"):
            mock_config.return_value.get.side_effect = lambda key, default=None: {
                "claude_cli.command": "claude",
                "hooks.file": "scripts/config/hooks.yaml",
            }.get(key, default)
            mock_config.return_value.root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

            cli = ClaudeAgentCLI()
            yield cli

    def test_all_moderator_presets_have_enable_hooks_false(self) -> None:
        """Verify all moderator presets have enable_hooks=False."""
        moderator_presets = [
            AgentConfigPresets.audit(),
            AgentConfigPresets.audit_diff(),
            AgentConfigPresets.consolidate(),
            AgentConfigPresets.task_moderator(),
            AgentConfigPresets.sync_moderator(),
            AgentConfigPresets.completion_moderator(),
        ]

        for preset in moderator_presets:
            assert preset.enable_hooks is False, f"Preset {preset} should have enable_hooks=False for selective hook control"

    def test_create_bash_only_hooks_file_basic(self, agent_cli: ClaudeAgentCLI) -> None:
        """Test basic functionality of _create_bash_only_hooks_file()."""
        settings_file = agent_cli._create_bash_only_hooks_file()

        try:
            assert settings_file.exists()
            assert settings_file.suffix == ".json"

            # Read settings file
            with settings_file.open("r") as f:
                settings = json.load(f)

            # Should have hooks -> PreToolUse structure
            assert "hooks" in settings
            assert "PreToolUse" in settings["hooks"]
            assert isinstance(settings["hooks"]["PreToolUse"], list)
            assert len(settings["hooks"]["PreToolUse"]) == 1

            # Should be bash guard hook
            bash_hook = settings["hooks"]["PreToolUse"][0]
            assert bash_hook["event"] == "PreToolUse"
            assert bash_hook["matcher"] == "Bash"
            assert bash_hook["command"] == "command-guard"

        finally:
            if settings_file.exists():
                settings_file.unlink()

    def test_create_bash_only_hooks_file_missing_hooks_yaml(self, agent_cli: ClaudeAgentCLI) -> None:
        """Test error handling when hooks.yaml not found."""
        agent_cli.config.root = Path("/nonexistent")

        with pytest.raises(RuntimeError, match="hooks.yaml not found"):
            agent_cli._create_bash_only_hooks_file()

    def test_create_bash_only_hooks_file_no_bash_hook(self, agent_cli: ClaudeAgentCLI) -> None:
        """Test error handling when bash hook not in hooks.yaml."""
        # Create temporary hooks.yaml without bash hook
        tmp_dir = Path(tempfile.mkdtemp())
        hooks_yaml = tmp_dir / "hooks.yaml"
        with hooks_yaml.open("w") as f:
            f.write("version: '2.0.0'\nhooks: []\n")

        cast(Any, agent_cli.config).root = tmp_dir
        cast(Any, agent_cli.config).get = Mock(return_value="hooks.yaml")

        try:
            with pytest.raises(RuntimeError, match="Bash command guard hook not found"):
                agent_cli._create_bash_only_hooks_file()
        finally:
            hooks_yaml.unlink()
            tmp_dir.rmdir()

    def test_run_print_creates_bash_only_settings(self, agent_cli: ClaudeAgentCLI) -> None:
        """Test that run_print() creates bash-only settings when enable_hooks=False."""
        agent_config = AgentConfigPresets.completion_moderator()
        assert agent_config.enable_hooks is False

        with patch.object(agent_cli, "_create_bash_only_hooks_file") as mock_create_hooks, patch("subprocess.Popen") as mock_popen:
            # Mock settings file creation
            mock_settings = Path("/tmp/test_settings.json")
            mock_create_hooks.return_value = mock_settings

            # Mock process
            mock_process = Mock()
            mock_process.communicate.return_value = ("output", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            try:
                agent_cli.run_print(
                    instruction="test",
                    agent_config=agent_config,
                )

                # Should have called _create_bash_only_hooks_file
                mock_create_hooks.assert_called_once()

                # Should have passed settings file to claude command
                call_args = mock_popen.call_args[0][0]
                assert "--settings" in call_args
                settings_idx = call_args.index("--settings")
                assert call_args[settings_idx + 1] == str(mock_settings)

            finally:
                pass

    def test_bash_guard_in_completion_moderator(self) -> None:
        """Test that completion_moderator preset will have bash guard."""
        preset = AgentConfigPresets.completion_moderator()

        # Should have Bash in allowed tools
        assert preset.allowed_tools is not None
        assert "Bash" in preset.allowed_tools

        # Should have enable_hooks=False (will use bash-only settings)
        assert preset.enable_hooks is False

    def test_bash_guard_in_task_moderator(self) -> None:
        """Test that task_moderator does NOT have Bash (read-only)."""
        preset = AgentConfigPresets.task_moderator()

        # Should NOT have Bash (read-only moderator)
        assert preset.allowed_tools is not None
        assert "Bash" not in preset.allowed_tools

        # Should have enable_hooks=False
        assert preset.enable_hooks is False

    def test_bash_guard_in_sync_moderator(self) -> None:
        """Test that sync_moderator has Bash with guard enabled."""
        preset = AgentConfigPresets.sync_moderator()

        # Should have Bash for git commands
        assert preset.allowed_tools is not None
        assert "Bash" in preset.allowed_tools

        # Should have enable_hooks=False (will use bash-only settings)
        assert preset.enable_hooks is False

    def test_worker_preset_has_full_hooks(self) -> None:
        """Test that worker preset has ALL hooks enabled (not bash-only)."""
        preset = AgentConfigPresets.worker()

        # Should have enable_hooks=True (full hooks, not selective)
        assert preset.enable_hooks is True

    def test_interactive_preset_has_full_hooks(self) -> None:
        """Test that interactive preset has ALL hooks enabled."""
        preset = AgentConfigPresets.interactive()

        # Should have enable_hooks=True
        assert preset.enable_hooks is True


class TestBashGuardIntegration:
    """Integration tests for bash guard with actual hooks.yaml."""

    def test_hooks_yaml_contains_bash_guard(self) -> None:
        """Test that hooks.yaml contains bash command guard."""
        hooks_yaml_path = Path("/home/ami/Projects/AMI-ORCHESTRATOR/scripts/config/hooks.yaml")

        if not hooks_yaml_path.exists():
            pytest.skip("hooks.yaml not found")

        import yaml

        with hooks_yaml_path.open("r") as f:
            hooks_config = yaml.safe_load(f)

        # Find bash guard hook
        bash_hook_found = False
        for hook in hooks_config.get("hooks", []):
            if hook.get("event") == "PreToolUse" and hook.get("matcher") == "Bash":
                bash_hook_found = True
                assert hook.get("command") == "command-guard"
                assert hook.get("timeout") == 10
                break

        assert bash_hook_found, "Bash command guard not found in hooks.yaml"

    def test_create_bash_only_settings_with_real_hooks(self) -> None:
        """Test creating bash-only settings from real hooks.yaml."""
        hooks_yaml_path = Path("/home/ami/Projects/AMI-ORCHESTRATOR/scripts/config/hooks.yaml")

        if not hooks_yaml_path.exists():
            pytest.skip("hooks.yaml not found")

        with patch("scripts.automation.agent_cli.get_config") as mock_config, patch("scripts.automation.agent_cli.get_logger"):
            mock_config.return_value.get.side_effect = lambda key, default=None: {
                "claude_cli.command": "claude",
                "hooks.file": "scripts/config/hooks.yaml",
            }.get(key, default)
            mock_config.return_value.root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

            cli = ClaudeAgentCLI()
            settings_file = cli._create_bash_only_hooks_file()

            try:
                # Verify settings file contains only bash guard
                with settings_file.open("r") as f:
                    settings = json.load(f)

                assert "hooks" in settings
                assert "PreToolUse" in settings["hooks"]

                # Should only have 1 hook (bash guard)
                assert len(settings["hooks"]["PreToolUse"]) == 1

                bash_hook = settings["hooks"]["PreToolUse"][0]
                assert bash_hook["matcher"] == "Bash"
                assert bash_hook["command"] == "command-guard"

                # Should NOT have code quality or response scanner hooks
                assert "Stop" not in settings["hooks"]
                assert "SubagentStop" not in settings["hooks"]

            finally:
                if settings_file.exists():
                    settings_file.unlink()
