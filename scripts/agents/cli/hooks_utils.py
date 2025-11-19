"""Utilities for hook configuration and management.

This module contains hook-specific utilities extracted from utils.py
to reduce code size and improve maintainability.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Protocol

import yaml


class ConfigProtocol(Protocol):
    root: Path

    def get(self, key: str, default: Any = None) -> Any: ...


def _validate_hooks_config(config: ConfigProtocol) -> Path:
    """Validate hooks config and return the path to the hooks file.

    Args:
        config: Configuration object containing hooks file path

    Returns:
        Path to the hooks file

    Raises:
        RuntimeError: If hooks file not found
        ValueError: If hooks configuration is invalid
    """
    hooks_config = config.get("hooks", "hooks.yaml")

    # If hooks_config is a dict (new format), extract the file path
    # Only support new dict format - no backward compatibility for security
    if not isinstance(hooks_config, dict):
        raise ValueError("Hooks configuration must be a dictionary with 'file' key")
    hooks_file_path = hooks_config.get("file", "hooks.yaml")

    # Ensure hooks_file_path is a string, not Any
    if not isinstance(hooks_file_path, str):
        raise ValueError(f"hooks file path must be a string, got {type(hooks_file_path)}")

    # Resolve hooks file path relative to config root
    hooks_path = config.root / hooks_file_path
    if not hooks_path.exists():
        raise RuntimeError(f"Hooks file not found: {hooks_path}")

    return hooks_path


def _read_hooks_config(hooks_path: Path) -> dict[Any, Any]:
    """Read and parse the hooks configuration from YAML file.

    Args:
        hooks_path: Path to the hooks file

    Returns:
        Parsed hooks configuration
    """
    with hooks_path.open() as f:
        result: dict[Any, Any] = yaml.safe_load(f)
        return result


def _group_hooks_by_event(hooks_config: dict[Any, Any]) -> dict[str, list[dict[str, Any]]]:
    """Group hooks by event type.

    Args:
        hooks_config: Parsed hooks configuration

    Returns:
        Dictionary mapping event types to lists of hooks
    """
    yaml_hooks_list = hooks_config.get("hooks", [])

    # Group hooks by event type
    hooks_by_event: dict[str, list[dict[str, Any]]] = {}
    for hook_entry in yaml_hooks_list:
        event_type = hook_entry.get("event", "PreToolUse")  # Default to PreToolUse
        if event_type not in hooks_by_event:
            hooks_by_event[event_type] = []
        hooks_by_event[event_type].append(hook_entry)

    return hooks_by_event


def _convert_hook_info_to_hook_container(hook_info: dict[Any, Any], config: ConfigProtocol) -> dict[str, Any]:
    """Convert a single hook_info to a hook container format.

    Args:
        hook_info: Individual hook information
        config: Configuration object

    Returns:
        Converted hook container
    """
    # Create hook entry with the right structure
    converted_hook: dict[str, Any] = {}

    # Add the required "type" field for Claude Code
    converted_hook["type"] = "command"

    # Map the command name from hooks.yaml to the appropriate external command
    # This is what Claude Code expects for hook execution
    if "command" in hook_info:
        command_name = hook_info.get("command", "")

        # Create command field to tell Claude Code to execute external hook
        # Use full path to ami-run wrapper to ensure proper environment
        # Execute the main.py directly to avoid hybrid script issues
        ami_run_path = config.root / "scripts" / "ami-run"
        script_path = config.root / "scripts" / "agents" / "cli" / "main.py"
        converted_hook["command"] = f"{ami_run_path} {script_path} --hook {command_name}"

    else:
        # Use the original field names if command is not present
        converted_hook["name"] = hook_info.get("name", "")
        converted_hook["module"] = hook_info.get("module", "")
        converted_hook["function"] = hook_info.get("function", "")

    # Only allow bypass for non-command hooks (new format)
    if "command" in hook_info:
        # For the new command format, don't add allow_bypass as it's not part of Claude Code spec
        pass
    else:
        converted_hook["allow_bypass"] = hook_info.get("allow_bypass", False)

    # Add timeout to inner hook as well, since some tests expect it there
    if "timeout" in hook_info:
        converted_hook["timeout"] = hook_info["timeout"]

    # Create hook container with nested hooks structure as expected by Claude Code
    hook_container: dict[str, Any] = {"hooks": [converted_hook]}

    # Add other attributes that apply to the hook container level (not the inner hook)
    # These include matcher, etc. which are at the same level as 'hooks' in the JSON
    if "matcher" in hook_info:
        matcher_value = hook_info["matcher"]
        if isinstance(matcher_value, list):
            # Convert list to pipe-separated regex - this results in a string
            hook_container["matcher"] = "|".join(str(item) for item in matcher_value)
        else:
            # Ensure it's a string for type safety
            hook_container["matcher"] = str(matcher_value) if matcher_value is not None else ""

    # Add timeout to hook container as well for completeness
    if "timeout" in hook_info:
        hook_container["timeout"] = hook_info["timeout"]

    return hook_container


def create_settings_file_from_hooks_config(config: ConfigProtocol) -> Path:
    """Create Claude settings file with hooks from config.

    Args:
        config: Configuration object containing hooks file path

    Returns:
        Path to created settings file with hooks configuration

    Raises:
        RuntimeError: If hooks file not found or settings file write fails
    """
    hooks_path = _validate_hooks_config(config)
    hooks_config = _read_hooks_config(hooks_path)

    # Convert to Claude Code settings format
    settings: dict[str, Any] = {"hooks": {}}

    hooks_by_event = _group_hooks_by_event(hooks_config)

    # Process each event type
    for event_type, hooks_list in hooks_by_event.items():
        converted_hooks: list[dict[str, Any]] = []

        for hook_info in hooks_list:
            hook_container = _convert_hook_info_to_hook_container(hook_info, config)
            converted_hooks.append(hook_container)

        if converted_hooks:
            # Claude Code expects array of individual hook configs, not nested structure
            # Each converted hook should be directly in the event array
            settings["hooks"][event_type] = converted_hooks
        else:
            settings["hooks"][event_type] = []

    # Ensure Stop hook exists as expected by tests
    if "Stop" not in settings["hooks"]:
        settings["hooks"]["Stop"] = []

    # Write to temporary settings file
    with tempfile.NamedTemporaryFile(mode="w", suffix="_settings.json", delete=False) as f:
        json.dump(settings, f)
        return Path(f.name)


def create_mcp_config_file(config: ConfigProtocol) -> Path | None:
    """Create MCP configuration file from automation.yaml config.

    Args:
        config: Configuration object

    Returns:
        Path to created config file if MCP enabled and servers configured, None otherwise
    """
    mcp_enabled = config.get("mcp.enabled", True)
    if not mcp_enabled:
        return None

    mcp_servers = config.get("mcp.servers", {})
    if not mcp_servers:
        return None

    # Build MCP config from YAML configuration
    mcp_config: dict[str, Any] = {"mcpServers": {}}

    for server_name, server_config in mcp_servers.items():
        # Substitute {root} template in args
        args = []
        for arg in server_config.get("args", []):
            if isinstance(arg, str) and "{root}" in arg:
                args.append(arg.format(root=config.root))
            else:
                args.append(arg)

        mcp_config["mcpServers"][server_name] = {
            "command": server_config["command"],
            "args": args,
        }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mcp_config_file:
        try:
            json.dump(mcp_config, mcp_config_file)
            file_name = mcp_config_file.name
        except (OSError, TypeError) as e:
            # If json.dump fails, clean up the temp file and re-raise
            Path(mcp_config_file.name).unlink(missing_ok=True)
            raise RuntimeError(f"Failed to write MCP config: {e}") from e

    return Path(file_name)
