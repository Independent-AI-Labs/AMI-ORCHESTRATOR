"""Implementation of AgentCLI using Claude Code CLI.

ClaudeAgentCLI implements the AgentCLI interface and provides concrete
functionality for running Claude Code agents with proper error handling,
timeout management, and streaming support.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from uuid import UUID

from base.backend.utils.uuid_utils import uuid7
from scripts.agents.cli.base_provider import CLIProvider as BaseProvider
from scripts.agents.cli.config import AgentConfig
from scripts.agents.cli.config_service import ConfigService
from scripts.agents.cli.hooks_utils import create_settings_file_from_hooks_config
from scripts.agents.cli.interface import AgentCLI
from scripts.agents.cli.provider_type import ProviderType
from scripts.agents.cli.streaming_utils import load_instruction_with_replacements
from scripts.agents.config import get_config


class ClaudeAgentCLI(BaseProvider, AgentCLI):
    """Implementation of AgentCLI using Claude Code CLI."""

    # All Claude Code tools (capitalized as used by Claude CLI)
    ALL_TOOLS = {
        "Bash",
        "Edit",
        "Read",
        "Write",
        "Ask",
        "WebSearch",
        "WebFetch",
        "TermTool",  # Additional tools that may be available
        "VSCodeEditor",
        "CodeSearch",
        "GitClient",
        "FileSys",
        "DatabaseClient",
        "APIExplorer",
        "DebuggingTool",
    }

    def __init__(self) -> None:
        """Initialize ClaudeAgentCLI."""
        self.current_process: subprocess.Popen[str] | None = None
        self._temp_settings_file: Path | None = None

    @staticmethod
    def compute_disallowed_tools(allowed_tools: list[str] | None) -> list[str]:
        """Compute disallowed tools from allowed tools.

        Args:
            allowed_tools: List of allowed tools, or None for all tools allowed

        Returns:
            List of disallowed tools (complement of allowed tools)

        Raises:
            ValueError: If any tool in allowed_tools is not in ALL_TOOLS
        """
        if allowed_tools is None:
            return []  # All tools allowed, no disallowed tools

        # Validate that all allowed tools are in ALL_TOOLS
        allowed_set = set(allowed_tools)
        all_tools_set = ClaudeAgentCLI.ALL_TOOLS
        unknown_tools = allowed_set - all_tools_set
        if unknown_tools:
            raise ValueError(f"Unknown tools in allowed_tools: {unknown_tools}")

        # Compute complement
        disallowed = [tool for tool in all_tools_set if tool not in allowed_set]
        return sorted(disallowed)  # Return sorted to maintain consistent order

    def _get_default_config(self) -> AgentConfig:
        """Get default agent configuration.

        Returns:
            Default AgentConfig instance
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=uuid7(),
            provider=ProviderType.CLAUDE,
            allowed_tools=None,
            enable_hooks=True,
            timeout=180,
        )

    def run_print(
        self,
        instruction: str | Path | None = None,
        cwd: Path | None = None,
        agent_config: AgentConfig | None = None,
        instruction_file: Path | None = None,
        stdin: str | None = None,
        audit_log_path: Path | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Run agent in print mode with Claude-specific settings file handling.

        Args:
            instruction: Natural language instruction for the agent (or use instruction_file)
            cwd: Working directory for agent execution (defaults to current)
            agent_config: Configuration for agent execution
            instruction_file: Path to instruction file (alternative to instruction string)
            stdin: Data to provide to stdin
            audit_log_path: Path for audit logging (not used in ClaudeAgentCLI but accepted for interface compatibility)

        Returns:
            Tuple of (output, metadata) where metadata includes session info

        Raises:
            AgentError: If agent execution fails
        """
        # Handle instruction vs instruction_file
        if instruction_file is not None:
            if instruction is not None:
                raise ValueError("Cannot specify both instruction and instruction_file")
            instruction_content = load_instruction_with_replacements(instruction_file)
            if cwd is None:
                cwd = instruction_file.parent
        elif isinstance(instruction, Path):
            # Security restriction: Path should only be passed as instruction_file parameter
            raise ValueError("Path objects should be passed as instruction_file parameter, not instruction parameter")
        else:
            # instruction should be a string or None
            instruction_content = instruction if instruction is not None else ""

        config = agent_config or self._get_default_config()

        # Temporarily add settings file to instance if hooks are enabled
        if config.enable_hooks:
            global_config = get_config()
            settings_file = create_settings_file_from_hooks_config(global_config)

            # Temporarily add to instance
            self._temp_settings_file = settings_file
            try:
                result = self._execute_with_timeout(instruction_content, cwd, config, stdin_data=stdin, audit_log_path=audit_log_path)
            finally:
                # Cleanup
                settings_file.unlink(missing_ok=True)
                if self._temp_settings_file:
                    self._temp_settings_file = None
            return result
        # Hooks not enabled, use normal flow
        return self._execute_with_timeout(instruction_content, cwd, config, stdin_data=stdin, audit_log_path=audit_log_path)

    def _build_command(
        self,
        instruction: str,
        cwd: Path | None,
        config: AgentConfig,
    ) -> list[str]:
        """Build Claude Code CLI command with proper flags and options.

        Args:
            instruction: Natural language instruction for the agent
            cwd: Working directory for agent execution
            config: Agent configuration

        Returns:
            List of command arguments
        """
        # Get the configured Claude command from config service
        config_service: ConfigService = ConfigService()
        claude_cmd = config_service.get_provider_command(ProviderType.CLAUDE)

        cmd = [claude_cmd]  # Use the configured command

        # Add model flag
        cmd.extend(["--model", config.model])

        # Note: Claude CLI may not support --session flag directly
        # Add session ID if provided and properly formatted as UUID (Claude CLI uses --session-id)
        if config.session_id is not None and config.session_id:  # Explicit None check
            # Validate that config.session_id is a string before assignment
            session_id: str = str(config.session_id)
            # Validate that session_id is a proper UUID format to avoid Claude CLI errors
            try:
                UUID(session_id)
                cmd.extend(["--session-id", session_id])
            except ValueError:
                # If not a valid UUID, skip the session-id flag
                # This allows for test scenarios with non-UUID session IDs
                pass

        # Handle allowed/disallowed tools (Claude CLI uses --allowed-tools or --disallowed-tools)
        if config.allowed_tools is not None:
            # Add disallowed tools flags
            disallowed = self.compute_disallowed_tools(config.allowed_tools)
            if disallowed:
                cmd.extend(["--disallowed-tools"] + disallowed)
        else:
            # All tools allowed by default
            pass

        # Add settings file if it was created for hooks
        if self._temp_settings_file and config.enable_hooks:
            cmd.extend(["--settings", str(self._temp_settings_file)])

        # Add timeout handling
        # Claude CLI doesn't support --timeout flag directly
        # Timeouts are handled externally during process execution

        # Add streaming flag if enabled
        if config.enable_streaming:
            cmd.extend(["--verbose", "--output-format", "stream-json"])

        # Add MCP servers if provided
        if config.mcp_servers:
            # For now, MCP servers are handled via environment or config
            # Add them as needed based on your implementation
            pass

        # Add print mode for non-interactive execution
        cmd.append("--print")

        # Add the instruction at the end
        cmd.append(instruction)

        # Add working directory as an additional directory if provided
        if cwd:
            cmd.extend(["--add-dir", str(cwd)])

        return cmd

    def _parse_stream_message(
        self,
        line: str,
        _cmd: list[str],
        _line_count: int,
        _agent_config: AgentConfig,
    ) -> tuple[str, dict[str, Any] | None]:
        """Parse a single line from Claude CLI's streaming output.

        Args:
            line: Raw line from Claude CLI output
            _cmd: Original command for error reporting (unused in Claude implementation)
            _line_count: Current line number for error reporting (unused in Claude implementation)
            _agent_config: Agent configuration (unused in Claude implementation)

        Returns:
            Tuple of (output text, metadata dict or None)
        """
        if not line.strip():
            return "", None

        try:
            # Try to parse as JSON first
            data = json.loads(line)
            if isinstance(data, dict):
                return self._handle_json_dict(data)
            # Not a dict, return as string
            return str(data), None
        except json.JSONDecodeError:
            # Not JSON, return as regular text
            return line, None

    def _handle_json_dict(self, data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
        """Handle parsing of JSON dictionary from Claude CLI output."""
        if "type" in data:
            msg_type = data["type"]
            metadata = data

            if msg_type == "content_block_delta":
                # Streaming delta (for real-time output)
                delta = data.get("delta", {})
                output_text = delta.get("text", "") if isinstance(delta, dict) else ""
            elif msg_type == "assistant" and "message" in data:
                output_text = self._extract_assistant_message(data["message"])
            elif msg_type in {"system", "result"}:
                # These message types contain metadata but not ongoing conversation text
                output_text = ""
            else:
                # Other message types
                output_text = json.dumps(data)
        else:
            # Not a recognized message type, return as text
            output_text = json.dumps(data)
            metadata = None

        return output_text, metadata

    def _extract_assistant_message(self, message_data: dict[str, Any]) -> str:
        """Extract text content from assistant message."""
        if "content" in message_data and isinstance(message_data["content"], list):
            # Extract text from content array
            text_parts: list[str] = []
            for content_item in message_data["content"]:
                if content_item.get("type") == "text" and "text" in content_item:
                    text_parts.append(content_item["text"])
            return "".join(text_parts)
        return ""
