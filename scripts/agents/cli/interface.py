"""Abstract interface for agent CLI operations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scripts.agents.cli.config import AgentConfig


class AgentCLI(ABC):
    """Abstract base class defining the interface for agent interactions."""

    @abstractmethod
    def run_interactive(
        self,
        instruction: str,
        cwd: Path | None = None,
        session_id: str | None = None,
        mcp_servers: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Run agent interactively with Claude Code CLI.

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

    @abstractmethod
    def run_print(
        self,
        instruction: str | Path | None = None,
        cwd: Path | None = None,
        agent_config: "AgentConfig | None" = None,
        instruction_file: Path | None = None,
        stdin: str | None = None,
        audit_log_path: Path | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Run agent in print mode with Claude Code CLI.

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
