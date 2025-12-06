"""Unit tests for agent_main module."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from scripts.agents.cli.hooks_utils import create_mcp_config_file, create_settings_file_from_hooks_config

# Test constants
HOOK_TIMEOUT_MS = 60000


class TestCreateMCPConfigFile:
    """Tests for _create_mcp_config_file function."""

    def test_returns_none_when_mcp_disabled(self) -> None:
        """Returns None when MCP is disabled in config."""
        config = Mock()
        config.get.return_value = False  # MCP disabled

        result = create_mcp_config_file(config)

        assert result is None

    def test_returns_none_when_no_servers_configured(self) -> None:
        """Returns None when no MCP servers configured."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "mcp.enabled": True,
            "mcp.servers": {},
        }.get(key, default)

        result = create_mcp_config_file(config)

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

        result = create_mcp_config_file(config)

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

        result = create_mcp_config_file(config)

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

        result = create_mcp_config_file(config)

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
                    "event": "PreToolUse",
                    "command": "bash-guard",
                    "matcher": ["Bash"],
                    "timeout": 30000,
                },
                {
                    "event": "Stop",
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
        # Updated to use dictionary format instead of string for security
        config.get.return_value = {"file": "hooks.yaml"}

        result = create_settings_file_from_hooks_config(config)

        assert result is not None
        assert result.exists()

        with result.open() as f:
            settings = json.load(f)

        assert "hooks" in settings
        assert "PreToolUse" in settings["hooks"]
        assert "Stop" in settings["hooks"]

        # Verify the structure follows Claude Code format
        # Each event should have an array of hook containers with nested "hooks" arrays
        pre_tool_use_hooks = settings["hooks"]["PreToolUse"]
        assert len(pre_tool_use_hooks) > 0
        hook_container = pre_tool_use_hooks[0]
        assert "hooks" in hook_container
        assert isinstance(hook_container["hooks"], list)
        assert len(hook_container["hooks"]) > 0

        # Verify inner hook has proper Claude Code format
        inner_hook = hook_container["hooks"][0]
        assert "type" in inner_hook
        assert inner_hook["type"] == "command"
        assert "command" in inner_hook
        # Verify that legacy fields are not present for command-based hooks
        assert "name" not in inner_hook
        assert "allow_bypass" not in inner_hook

        # Check Stop hooks as well
        stop_hooks = settings["hooks"]["Stop"]
        if stop_hooks:  # Only check if Stop hooks exist
            stop_hook_container = stop_hooks[0]
            if "hooks" in stop_hook_container and stop_hook_container["hooks"]:
                stop_inner_hook = stop_hook_container["hooks"][0]
                assert "type" in stop_inner_hook
                assert stop_inner_hook["type"] == "command"

        result.unlink()

    def test_converts_list_matcher_to_regex(self, mock_hooks_file: Path) -> None:
        """Converts list matchers to regex string."""
        config = Mock()
        config.root = mock_hooks_file.parent
        # Updated to use dictionary format instead of string for security
        config.get.return_value = {"file": "hooks.yaml"}

        result = create_settings_file_from_hooks_config(config)

        assert result is not None

        with result.open() as f:
            settings = json.load(f)

        # List matcher ["Bash"] should become a regex pattern matching Bash and related tools
        hook_entry = settings["hooks"]["PreToolUse"][0]
        assert hook_entry["matcher"] in ["Bash", "Write|Edit|Bash"]  # Accept either old or new format

        # Verify the inner hook has the correct Claude Code format
        inner_hook = hook_entry["hooks"][0]
        assert inner_hook["type"] == "command"
        assert "name" not in inner_hook
        assert "allow_bypass" not in inner_hook

        result.unlink()

    def test_raises_error_if_hooks_file_not_found(self) -> None:
        """Raises RuntimeError if hooks file doesn't exist."""
        config = Mock()
        config.root = Path("/test/root")
        # Updated to use dictionary format instead of string for security
        config.get.return_value = {"file": "nonexistent/hooks.yaml"}

        with (
            patch("scripts.agents.config.get_config", return_value=config),
            pytest.raises(RuntimeError, match="Hooks file not found"),
        ):
            create_settings_file_from_hooks_config(config)

    def test_includes_hook_command_timeout(self, tmp_path: Path) -> None:
        """Includes timeout in hook command if specified."""
        hooks_config = {
            "hooks": [
                {
                    "event": "PreToolUse",
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
        # Updated to use dictionary format instead of string for security
        config.get.return_value = {"file": "hooks.yaml"}

        with patch("scripts.agents.config.get_config", return_value=config):
            result = create_settings_file_from_hooks_config(config)

        with result.open() as f:
            settings = json.load(f)

        hook_command = settings["hooks"]["PreToolUse"][0]["hooks"][0]
        assert hook_command["timeout"] == HOOK_TIMEOUT_MS
        assert hook_command["type"] == "command"
        # Verify that name and allow_bypass are not present for command-based hooks
        assert "name" not in hook_command
        assert "allow_bypass" not in hook_command

        result.unlink()

    def test_converts_multiple_matchers_to_pipe_separated(self, tmp_path: Path) -> None:
        """Converts multiple matchers to pipe-separated regex."""
        hooks_config = {
            "hooks": [
                {
                    "event": "PreToolUse",
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
        # Updated to use dictionary format instead of string for security
        config.get.return_value = {"file": "hooks.yaml"}

        with patch("scripts.agents.config.get_config", return_value=config):
            result = create_settings_file_from_hooks_config(config)

        with result.open() as f:
            settings = json.load(f)

        hook_entry = settings["hooks"]["PreToolUse"][0]
        assert hook_entry["matcher"] == "Edit|Write|Delete"

        # Verify the inner hook has the correct Claude Code format
        inner_hook = hook_entry["hooks"][0]
        assert inner_hook["type"] == "command"
        assert "name" not in inner_hook
        assert "allow_bypass" not in inner_hook

        result.unlink()
