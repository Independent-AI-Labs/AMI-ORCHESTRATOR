"""Factory function to get agent CLI instances."""

from scripts.agents.cli.claude_cli import ClaudeAgentCLI
from scripts.agents.cli.interface import AgentCLI


def get_agent_cli() -> AgentCLI:
    """Factory function to get agent CLI instance.

    Returns ClaudeAgentCLI by default.
    Future: Can return different implementations based on config.

    Returns:
        Agent CLI instance
    """
    return ClaudeAgentCLI()
