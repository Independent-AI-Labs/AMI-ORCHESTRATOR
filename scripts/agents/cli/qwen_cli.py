"""Implementation of AgentCLI using Qwen Code CLI.

QwenAgentCLI implements the AgentCLI interface and provides concrete
functionality for running Qwen Code agents with proper error handling,
timeout management, and streaming support.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from base.backend.utils.uuid_utils import uuid7
from scripts.agents.cli.base_provider import CLIProvider as BaseProvider
from scripts.agents.cli.config import AgentConfig
from scripts.agents.cli.config_service import ConfigService
from scripts.agents.cli.interface import AgentCLI
from scripts.agents.cli.provider_type import ProviderType
from scripts.agents.cli.streaming_utils import load_instruction_with_replacements


class QwenAgentCLI(BaseProvider, AgentCLI):
    """Implementation of AgentCLI using Qwen Code CLI."""

    # All Qwen Code tools (in snake_case format as used by Qwen CLI)
    ALL_TOOLS = {
        "read_file",
        "write_file",
        "edit",
        "run_shell_command",
        "ask",
        "web_search",
        "web_fetch",
        "term_tool",  # Additional tools that may be available
        "vscode_editor",
        "code_search",
        "git_client",
        "file_sys",
        "database_client",
        "api_explorer",
        "debugging_tool",
    }

    def __init__(self) -> None:
        """Initialize QwenAgentCLI."""
        super().__init__()  # Initialize parent class

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
        all_tools_set = QwenAgentCLI.ALL_TOOLS
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
            model="qwen-coder",  # Default Qwen model
            session_id=uuid7(),
            provider=ProviderType.QWEN,
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
        """Run agent in print mode with Qwen-specific settings.

        Args:
            instruction: Natural language instruction for the agent (or use instruction_file)
            cwd: Working directory for agent execution (defaults to current)
            agent_config: Configuration for agent execution
            instruction_file: Path to instruction file (alternative to instruction string)
            stdin: Data to provide to stdin
            audit_log_path: Path for audit logging (not used in base implementation but accepted for interface compatibility)

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
            # instruction is a string (not None since first condition handled instruction_file case)
            if instruction is None:
                raise ValueError("instruction cannot be None when instruction_file is not provided")
            instruction_content = instruction

        config = agent_config or self._get_default_config()
        return self._execute_with_timeout(instruction_content, cwd, config, stdin_data=stdin, audit_log_path=audit_log_path)

    def _build_command(
        self,
        instruction: str,
        cwd: Path | None,
        config: AgentConfig,
    ) -> list[str]:
        """Build Qwen Code CLI command with proper flags and options.

        Args:
            instruction: Natural language instruction for the agent
            cwd: Working directory for agent execution
            config: Agent configuration

        Returns:
            List of command arguments
        """
        # Get the configured Qwen command from config service
        config_service: ConfigService = ConfigService()
        qwen_cmd = config_service.get_provider_command(ProviderType.QWEN)

        cmd = [qwen_cmd]  # Use the configured command

        # Add model flag
        cmd.extend(["--model", config.model])

        # Add session ID if provided
        if config.session_id:
            # Qwen CLI may use different session handling
            # For now, add as an option - this might need adjustment
            pass

        # Handle allowed/disallowed tools (Qwen CLI uses different flags than Claude)
        if config.allowed_tools is not None:
            # Add disallowed tools flags
            disallowed = self.compute_disallowed_tools(config.allowed_tools)
            if disallowed:
                # Qwen CLI may use --allowed-tools or similar
                # For now, we'll use a template approach
                pass

        # Add timeout handling
        # Qwen CLI doesn't support --timeout flag directly
        # Timeouts are handled externally during process execution

        # Add streaming flag if enabled
        if config.enable_streaming:
            cmd.extend(["--output-format", "stream-json"])

        # Add print mode for non-interactive execution
        # Using --prompt to run in non-interactive mode
        cmd.extend(["--prompt", instruction])

        # Add working directory if provided
        if cwd:
            # Qwen CLI may support directory inclusion differently
            pass

        return cmd

    def _parse_stream_message(
        self,
        line: str,
        _cmd: list[str],
        _line_count: int,
        _agent_config: AgentConfig,
    ) -> tuple[str, dict[str, Any] | None]:
        """Parse a single line from Qwen CLI's streaming output.

        Args:
            line: Raw line from Qwen CLI output
            _cmd: Original command for error reporting (unused in Qwen implementation)
            _line_count: Current line number for error reporting (unused in Qwen implementation)
            _agent_config: Agent configuration (unused in Qwen implementation)

        Returns:
            Tuple of (output text, metadata dict or None)
        """
        output_text = ""
        metadata = None

        if not line.strip():
            return output_text, metadata

        # Qwen CLI can output JSON lines mixed with regular output
        try:
            # Try to parse as JSON first
            data = json.loads(line)
            if isinstance(data, dict):
                # This is a structured response
                if "type" in data:
                    msg_type = data["type"]
                    # Add delta content to output for content_block_delta, empty string for all other message types
                    output_text = data.get("delta", {}).get("text", "") if msg_type == "content_block_delta" else ""
                    metadata = data
                else:
                    # Not a recognized message type, return as text
                    output_text = json.dumps(data)
                    metadata = None
            else:
                # Not a dict, return as string
                output_text = str(data)
                metadata = None
        except json.JSONDecodeError:
            # Not JSON, return as regular text
            output_text = line
            metadata = None

        return output_text, metadata
