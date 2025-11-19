"""Configuration classes for agent execution."""

from typing import Any


class AgentConfig:
    """Configuration for an agent execution.

    Defines tools, model, hooks, timeout, and session settings for an agent.

    NOTE: disallowed_tools is NOT stored here - it's computed automatically
    by ClaudeAgentCLI.compute_disallowed_tools() as the complement of allowed_tools.
    """

    def __init__(
        self,
        model: str,
        session_id: str,  # Claude Code session ID for execution tracking
        allowed_tools: list[str] | None = None,  # None = all tools allowed
        enable_hooks: bool = True,
        enable_streaming: bool | None = False,  # Enable --resume and --output-format stream-json
        timeout: int | None = 180,  # None = no timeout (interactive)
        mcp_servers: dict[str, Any] | None = None,
    ):
        self.model = model
        self.session_id = session_id
        self.allowed_tools = allowed_tools
        self.enable_hooks = enable_hooks
        self.enable_streaming = enable_streaming
        self.timeout = timeout
        self.mcp_servers = mcp_servers


class AgentConfigPresets:
    """Common agent configuration presets.

    Identifies patterns behind audit agents, code quality agents, worker agents, etc.
    """

    @staticmethod
    def audit(session_id: str) -> AgentConfig:
        """Code audit agent: WebSearch/WebFetch only, hooks disabled, high-quality model.

        Used for: Full file code audits, security analysis
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=180,
        )

    @staticmethod
    def audit_diff(session_id: str) -> AgentConfig:
        """Diff audit agent: For PreToolUse hooks checking code quality.

        Used for: Edit/Write validation, regression detection
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=60,  # Fast for hooks
        )

    @staticmethod
    def consolidate(session_id: str) -> AgentConfig:
        """Pattern consolidation agent: Read/Write/Edit for updating consolidated reports.

        Used for: Extracting patterns from failed audits
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["Read", "Write", "Edit", "WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=300,
        )

    @staticmethod
    def worker(session_id: str) -> AgentConfig:
        """General worker agent: All tools, hooks enabled.

        Used for: General automation, --print mode with hooks
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=None,  # All tools
            enable_hooks=True,
            timeout=180,
        )

    @staticmethod
    def interactive(session_id: str, mcp_servers: dict[str, Any] | None = None) -> AgentConfig:
        """Interactive agent: All tools, hooks enabled, MCP servers.

        Used for: Interactive sessions with user
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=None,
            enable_hooks=True,
            timeout=None,  # No timeout
            mcp_servers=mcp_servers,
        )

    @staticmethod
    def task_worker(session_id: str) -> AgentConfig:
        """Task worker agent: All tools, hooks enabled, higher timeout.

        Used for: Complex task execution
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=None,  # All tools
            enable_hooks=True,
            timeout=600,  # 10 minutes for complex tasks
        )

    @staticmethod
    def task_moderator(session_id: str) -> AgentConfig:
        """Task moderator agent: WebSearch/WebFetch only, hooks disabled.

        Used for: Task completion validation and moderation
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=300,  # 5 minutes
        )

    @staticmethod
    def sync_worker(session_id: str) -> AgentConfig:
        """Sync worker agent: All tools, hooks enabled.

        Used for: File synchronization tasks
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=None,  # All tools
            enable_hooks=False,  # No hooks during sync
            timeout=600,  # 10 minutes for sync operations
        )

    @staticmethod
    def sync_moderator(session_id: str) -> AgentConfig:
        """Sync moderator agent: WebSearch/WebFetch only, hooks disabled.

        Used for: Sync completion validation
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=180,  # 3 minutes
        )

    @staticmethod
    def completion_moderator(session_id: str) -> AgentConfig:
        """Completion moderator agent: WebSearch/WebFetch only, hooks disabled.

        Used for: Final completion validation with high quality model
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=100,  # 100s timeout for completion moderation
        )
