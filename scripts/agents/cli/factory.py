"""Factory function to get agent CLI instances."""

from scripts.agents.cli.claude_cli import ClaudeAgentCLI
from scripts.agents.cli.config import AgentConfig
from scripts.agents.cli.interface import AgentCLI
from scripts.agents.cli.provider_type import ProviderType
from scripts.agents.cli.qwen_cli import QwenAgentCLI


def get_agent_cli(agent_config: AgentConfig | None = None) -> AgentCLI:
    """Factory function to get agent CLI instance.

    Args:
        agent_config: Agent configuration containing provider information (defaults to Claude provider if not specified)

    Returns:
        Agent CLI instance for the specified provider
    """
    provider = agent_config.provider if agent_config else ProviderType.CLAUDE
    if provider == ProviderType.CLAUDE:
        return ClaudeAgentCLI()
    if provider == ProviderType.QWEN:
        return QwenAgentCLI()
    # For now, defaulting to Claude for any other provider
    # Future: add support for GEMINI
    return ClaudeAgentCLI()
