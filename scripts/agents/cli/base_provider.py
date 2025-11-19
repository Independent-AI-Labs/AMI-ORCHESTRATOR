"""Base provider class for CLI agent implementations."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from base.backend.utils.uuid_utils import uuid7
from scripts.agents.cli.config import AgentConfig
from scripts.agents.cli.streaming import (
    execute_streaming,
)
from scripts.agents.cli.streaming_utils import load_instruction_with_replacements
from scripts.agents.config import get_config


class CLIProvider(ABC):
    """Base class for CLI agent providers with common functionality."""

    def __init__(self) -> None:
        """Initialize CLIProvider."""
        self.current_process: subprocess.Popen[str] | None = None

    def kill_current_process(self) -> bool:
        """Kill the current running agent process if one exists.

        Returns:
            True if a process was killed, False if no process was running
        """
        if self.current_process is None:
            return False

        try:
            # Try graceful termination first
            self.current_process.terminate()
            try:
                # Wait a short time for graceful exit
                self.current_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't exit gracefully
                self.current_process.kill()
                self.current_process.wait()  # Clean up zombie process
        except ProcessLookupError:
            # Process already terminated
            pass
        finally:
            self.current_process = None

        return True

    @abstractmethod
    def _build_command(
        self,
        instruction: str,
        cwd: Path | None,
        config: AgentConfig,
    ) -> list[str]:
        """Build the CLI command with proper flags and options.

        Args:
            instruction: Natural language instruction for the agent
            cwd: Working directory for agent execution
            config: Agent configuration

        Returns:
            List of command arguments
        """

    @abstractmethod
    def _parse_stream_message(
        self,
        line: str,
        cmd: list[str],
        line_count: int,
        agent_config: AgentConfig,
    ) -> tuple[str, dict[str, Any] | None]:
        """Parse a single line from CLI's streaming output.

        Args:
            line: Raw line from CLI output
            cmd: Original command for error reporting
            line_count: Current line number for error reporting
            agent_config: Agent configuration

        Returns:
            Tuple of (output text, metadata dict or None)
        """

    @abstractmethod
    def _get_default_config(self) -> AgentConfig:
        """Get default agent configuration.

        Returns:
            Default AgentConfig instance
        """

    def _execute_with_timeout(
        self,
        instruction: str,
        cwd: Path | None,
        agent_config: AgentConfig,
        stdin_data: str | None = None,
        audit_log_path: Path | None = None,  # noqa: ARG002
    ) -> tuple[str, dict[str, Any] | None]:
        """Execute CLI command with timeout handling.

        Args:
            instruction: Natural language instruction
            cwd: Working directory for execution
            agent_config: Agent configuration
            stdin_data: Data to provide to stdin
            audit_log_path: Path for audit logging (not used in base implementation but accepted for interface compatibility)

        Returns:
            Tuple of (output, metadata)

        Raises:
            AgentError: If execution fails or times out
        """
        # Build the command
        cmd = self._build_command(instruction, cwd, agent_config)

        # Use streaming execution for better timeout handling
        # Note: audit_log_path is accepted but not currently used by execute_streaming
        config = get_config()
        return execute_streaming(cmd=cmd, stdin_data=stdin_data, cwd=cwd, agent_config=agent_config, config=config)

    def run_interactive(
        self,
        instruction: str,
        cwd: Path | None = None,
        session_id: str | None = None,
        mcp_servers: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Run agent interactively with CLI.

        Args:
            instruction: Natural language instruction for the agent
            cwd: Working directory for agent execution (defaults to current)
            session_id: Session identifier for audit logging
            mcp_servers: MCP servers configuration for the session

        Returns:
            Tuple of (output, metadata) where metadata includes session info

        Raises:
            AgentError: If agent execution fails
        """
        config = AgentConfig(
            model="default-model",  # Subclass should override this
            session_id=session_id or uuid7(),
            allowed_tools=None,  # All tools allowed in interactive mode
            enable_hooks=True,
            timeout=None,  # No timeout for interactive sessions
            mcp_servers=mcp_servers,
        )
        return self._execute_with_timeout(instruction, cwd, config)

    def run_print(
        self,
        instruction: str | Path | None = None,
        cwd: Path | None = None,
        agent_config: AgentConfig | None = None,
        instruction_file: Path | None = None,
        stdin: str | None = None,
        audit_log_path: Path | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Run agent in print mode with CLI.

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
            # instruction is a string
            instruction_content = instruction  # type: ignore

        config = agent_config or self._get_default_config()
        return self._execute_with_timeout(instruction_content, cwd, config, stdin_data=stdin, audit_log_path=audit_log_path)
