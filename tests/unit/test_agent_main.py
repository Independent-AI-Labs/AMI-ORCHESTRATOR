"""Unit tests for agent_main module."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from scripts.automation import agent_main


class TestCreateMCPConfigFile:
    """Tests for _create_mcp_config_file function."""

    def test_returns_none_when_mcp_disabled(self) -> None:
        """Returns None when MCP is disabled in config."""
        config = Mock()
        config.get.return_value = False  # MCP disabled

        result = agent_main._create_mcp_config_file(config)

        assert result is None

    def test_returns_none_when_no_servers_configured(self) -> None:
        """Returns None when no MCP servers configured."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "mcp.enabled": True,
            "mcp.servers": {},
        }.get(key, default)

        result = agent_main._create_mcp_config_file(config)

        assert result is None

    def test_creates_mcp_config_file_with_servers(self) -> None:
        """Creates MCP config file with server configurations."""
        config = Mock()
        config.root = Path("/test/root")
        config.get.side_effect = lambda key, default=None: {
            "mcp.enabled": True,
            "mcp.servers": {
                "filesys": {
                    "command": "uv",
                    "args": ["run", "{root}/files/server.py"],
                },
            },
        }.get(key, default)

        result = agent_main._create_mcp_config_file(config)

        assert result is not None
        assert result.exists()
        assert result.suffix == ".json"

        # Verify content
        with result.open() as f:
            mcp_config = json.load(f)

        assert "mcpServers" in mcp_config
        assert "filesys" in mcp_config["mcpServers"]
        assert mcp_config["mcpServers"]["filesys"]["command"] == "uv"
        assert "/test/root/files/server.py" in mcp_config["mcpServers"]["filesys"]["args"]

        # Cleanup
        result.unlink()

    def test_substitutes_root_template_in_args(self) -> None:
        """Substitutes {root} template in server args."""
        config = Mock()
        config.root = Path("/custom/path")
        config.get.side_effect = lambda key, default=None: {
            "mcp.enabled": True,
            "mcp.servers": {
                "test": {
                    "command": "python",
                    "args": ["{root}/module/script.py", "--config", "{root}/config.json"],
                },
            },
        }.get(key, default)

        result = agent_main._create_mcp_config_file(config)

        assert result is not None

        with result.open() as f:
            mcp_config = json.load(f)

        # Check both occurrences of {root} were substituted
        args = mcp_config["mcpServers"]["test"]["args"]
        assert args[0] == "/custom/path/module/script.py"
        assert args[1] == "--config"
        assert args[2] == "/custom/path/config.json"

        result.unlink()

    def test_handles_non_template_args(self) -> None:
        """Handles args without {root} template."""
        config = Mock()
        config.root = Path("/test/root")
        config.get.side_effect = lambda key, default=None: {
            "mcp.enabled": True,
            "mcp.servers": {
                "test": {
                    "command": "node",
                    "args": ["server.js", "--port", "8080"],
                },
            },
        }.get(key, default)

        result = agent_main._create_mcp_config_file(config)

        assert result is not None

        with result.open() as f:
            mcp_config = json.load(f)

        # Args without template should pass through unchanged
        args = mcp_config["mcpServers"]["test"]["args"]
        assert args == ["server.js", "--port", "8080"]

        result.unlink()


class TestCreateSettingsFile:
    """Tests for _create_settings_file function."""

    @pytest.fixture
    def mock_hooks_file(self, tmp_path: Path) -> Path:
        """Create a mock hooks configuration file."""
        hooks_config = {
            "hooks": [
                {
                    "event": "before_tool_execution",
                    "command": "bash-guard",
                    "matcher": ["Bash"],
                    "timeout": 30000,
                },
                {
                    "event": "after_response",
                    "command": "response-scanner",
                },
            ],
        }

        hooks_file = tmp_path / "hooks.yaml"
        with hooks_file.open("w") as f:
            yaml.dump(hooks_config, f)

        return hooks_file

    def test_creates_settings_file_from_hooks(self, mock_hooks_file: Path) -> None:
        """Creates settings file from hooks configuration."""
        config = Mock()
        config.root = mock_hooks_file.parent
        config.get.return_value = "hooks.yaml"

        result = agent_main._create_settings_file(config)

        assert result is not None
        assert result.exists()

        with result.open() as f:
            settings = json.load(f)

        assert "hooks" in settings
        assert "before_tool_execution" in settings["hooks"]
        assert "after_response" in settings["hooks"]

        result.unlink()

    def test_converts_list_matcher_to_regex(self, mock_hooks_file: Path) -> None:
        """Converts list matchers to regex string."""
        config = Mock()
        config.root = mock_hooks_file.parent
        config.get.return_value = "hooks.yaml"

        result = agent_main._create_settings_file(config)

        assert result is not None

        with result.open() as f:
            settings = json.load(f)

        # List matcher ["Bash"] should become "Bash"
        hook_entry = settings["hooks"]["before_tool_execution"][0]
        assert hook_entry["matcher"] == "Bash"

        result.unlink()

    def test_raises_error_if_hooks_file_not_found(self) -> None:
        """Raises RuntimeError if hooks file doesn't exist."""
        config = Mock()
        config.root = Path("/test/root")
        config.get.return_value = "nonexistent/hooks.yaml"

        with pytest.raises(RuntimeError, match="Hooks file not found"):
            agent_main._create_settings_file(config)

    def test_includes_hook_command_timeout(self, tmp_path: Path) -> None:
        """Includes timeout in hook command if specified."""
        hooks_config = {
            "hooks": [
                {
                    "event": "before_tool_execution",
                    "command": "test-hook",
                    "timeout": 60000,
                },
            ],
        }

        hooks_file = tmp_path / "hooks.yaml"
        with hooks_file.open("w") as f:
            yaml.dump(hooks_config, f)

        config = Mock()
        config.root = tmp_path
        config.get.return_value = "hooks.yaml"

        result = agent_main._create_settings_file(config)

        with result.open() as f:
            settings = json.load(f)

        hook_command = settings["hooks"]["before_tool_execution"][0]["hooks"][0]
        assert hook_command["timeout"] == 60000

        result.unlink()

    def test_converts_multiple_matchers_to_pipe_separated(self, tmp_path: Path) -> None:
        """Converts multiple matchers to pipe-separated regex."""
        hooks_config = {
            "hooks": [
                {
                    "event": "before_tool_execution",
                    "command": "multi-guard",
                    "matcher": ["Edit", "Write", "Delete"],
                },
            ],
        }

        hooks_file = tmp_path / "hooks.yaml"
        with hooks_file.open("w") as f:
            yaml.dump(hooks_config, f)

        config = Mock()
        config.root = tmp_path
        config.get.return_value = "hooks.yaml"

        result = agent_main._create_settings_file(config)

        with result.open() as f:
            settings = json.load(f)

        hook_entry = settings["hooks"]["before_tool_execution"][0]
        assert hook_entry["matcher"] == "Edit|Write|Delete"

        result.unlink()


class TestModeInteractive:
    """Tests for mode_interactive function."""

    def test_mode_interactive_loads_agent_instruction(self) -> None:
        """mode_interactive loads agent instruction from file."""
        with (
            patch("scripts.automation.agent_main.get_config") as mock_get_config,
            patch("scripts.automation.agent_main.get_logger"),
            patch("scripts.automation.agent_main._create_mcp_config_file", return_value=None),
            patch("scripts.automation.agent_main._create_settings_file") as mock_create_settings,
            patch("scripts.automation.agent_main.subprocess.run") as mock_subprocess,
        ):
            # Mock settings file
            mock_settings_file = Mock()
            mock_settings_file.unlink = Mock()
            mock_create_settings.return_value = mock_settings_file

            config = Mock()
            config.root = Path("/test/root")
            config.get.side_effect = lambda key, default=None: {
                "prompts.dir": "config/prompts",
                "prompts.agent": "agent.txt",
                "claude_cli.command": "claude",
            }.get(key, default)

            mock_get_config.return_value = config

            # Mock agent file and debug log file
            agent_file_content = "Agent instruction with date: {date}"
            mock_file = Mock()
            mock_file.__enter__ = Mock(return_value=mock_file)
            mock_file.__exit__ = Mock(return_value=False)
            mock_file.write = Mock()

            with (
                patch.object(Path, "read_text", return_value=agent_file_content),
                patch.object(Path, "open", return_value=mock_file),
            ):
                result = agent_main.mode_interactive()

                # Should have called subprocess.run with claude command
                assert mock_subprocess.called
                assert result == 0
