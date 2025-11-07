# AGENT FRAMEWORK SPECIFICATION V2

**Date**: 2025-11-07
**Status**: Enterprise Architecture Specification
**Supersedes**: SPEC-AGENTS.md v1.0

---

## Executive Summary

This specification defines the migration of the agent automation framework from `/scripts/automation` to `/backend/agents`, applying enterprise patterns from established modules (`/base`, `/files`, `/nodes`).

### Core Objectives

1. **Factory with Registry** - Extensible provider system following DAOFactory pattern
2. **Async/Await Throughout** - All I/O operations async for concurrency
3. **Facade Pattern** - Unified operation interface following filesys tools pattern
4. **Protocol-Based Capabilities** - Provider feature negotiation via protocols
5. **Structured Error Handling** - Exceptions with context and to_dict() for logging
6. **Provider Base with Lifecycle** - Complete resource management following BaseDAO pattern
7. **Separation of Concerns** - Single responsibility per module (<300 lines)

### Key Anti-Patterns to Eliminate

- ❌ Monolithic 1219-line agent_cli.py
- ❌ Simple if/else provider selection
- ❌ Blocking subprocess I/O
- ❌ Mixed concerns (parsing + execution + I/O in single methods)
- ❌ No resource cleanup (missing context managers)
- ❌ Unstructured exceptions

---

## Directory Structure

Following `/base/backend/dataops` and `/files/backend/mcp/filesys` patterns:

```
backend/agents/
├── __init__.py                      # Public API exports
├── README.md                        # Framework documentation
│
├── core/                            # Core abstractions
│   ├── __init__.py
│   ├── exceptions.py                # Structured error hierarchy
│   ├── protocols.py                 # Provider capability protocols
│   ├── base.py                      # Provider ABC with lifecycle
│   ├── config.py                    # AgentConfig dataclass
│   ├── presets.py                   # AgentConfigPresets
│   ├── factory.py                   # ProviderFactory with registry
│   └── models.py                    # ExecutionResult, StreamChunk, etc.
│
├── providers/                       # CLI provider implementations
│   ├── __init__.py
│   ├── claude/                      # Claude provider package
│   │   ├── __init__.py
│   │   ├── provider.py              # ClaudeProvider implementation
│   │   ├── streaming.py             # Claude streaming logic
│   │   ├── hooks.py                 # Hook file management
│   │   └── tools.py                 # Tool restriction logic
│   ├── gemini/                      # Gemini provider package
│   │   ├── __init__.py
│   │   ├── provider.py              # GeminiProvider implementation
│   │   ├── streaming.py             # Gemini streaming logic
│   │   ├── parser.py                # JSON message parsing
│   │   └── tools.py                 # Tool mapping logic
│   ├── models.py                    # CLIProvider enum, model enums
│   └── registry.py                  # Auto-registration on import
│
├── operations/                      # Individual operations (facade pattern)
│   ├── __init__.py
│   ├── facade.py                    # Unified operation facade
│   ├── audit.py                     # Audit operation implementation
│   ├── tasks.py                     # Task operation implementation
│   ├── sync.py                      # Sync operation implementation
│   └── docs.py                      # Docs operation implementation
│
├── executors/                       # High-level orchestrators
│   ├── __init__.py
│   ├── batch.py                     # Batch execution engine
│   └── workflow.py                  # Multi-step workflow engine
│
├── hooks/                           # Hook validation framework
│   ├── __init__.py
│   ├── base.py                      # HookValidator ABC
│   ├── registry.py                  # Hook validator registry
│   ├── validators/                  # Validator implementations
│   │   ├── __init__.py
│   │   ├── malicious_behavior.py
│   │   ├── command_guard.py
│   │   ├── code_quality.py
│   │   ├── shebang.py
│   │   ├── response.py
│   │   └── todo.py
│   └── utils/                       # Hook utilities
│       ├── __init__.py
│       ├── transcript.py
│       └── context.py
│
├── utils/                           # Shared utilities
│   ├── __init__.py
│   ├── config.py                    # Config loader
│   ├── logger.py                    # Structured logging
│   ├── subprocess.py                # Async subprocess wrapper
│   └── validators.py                # LLM-based validation
│
└── cli/                             # CLI entry point
    ├── __init__.py
    └── main.py                      # Route to operations
```

---

## Core Components

### 1. Provider Factory with Registry

**Pattern Source**: `/base/backend/dataops/core/factory.py` (DAOFactory)

```python
# backend/agents/core/factory.py
from typing import ClassVar
from backend.agents.core.base import Provider
from backend.agents.core.config import AgentConfig
from backend.agents.providers.models import CLIProvider


class ProviderFactory:
    """Factory for creating CLI provider instances with registry pattern."""

    _registry: ClassVar[dict[CLIProvider, type[Provider]]] = {}

    @classmethod
    def register(cls, provider_type: CLIProvider, provider_class: type[Provider]) -> None:
        """Register a provider implementation.

        Args:
            provider_type: Provider enum value
            provider_class: Provider implementation class
        """
        cls._registry[provider_type] = provider_class

    @classmethod
    def create(cls, config: AgentConfig) -> Provider:
        """Create provider instance with capability validation.

        Args:
            config: Agent configuration

        Returns:
            Initialized provider instance

        Raises:
            ValueError: If provider not registered or lacks required capabilities
        """
        provider_class = cls._registry.get(config.provider)
        if not provider_class:
            raise ValueError(
                f"No provider registered for: {config.provider.value}\n"
                f"Available providers: {[p.value for p in cls._registry.keys()]}"
            )

        # Validate provider capabilities against config
        instance = provider_class(config)
        _validate_provider_capabilities(instance, config)
        return instance

    @classmethod
    def list_providers(cls) -> list[CLIProvider]:
        """Get list of all registered providers."""
        return list(cls._registry.keys())


def _validate_provider_capabilities(provider: Provider, config: AgentConfig) -> None:
    """Validate provider supports requested capabilities.

    Args:
        provider: Provider instance
        config: Agent configuration

    Raises:
        ValueError: If provider lacks required capabilities
    """
    from backend.agents.core.protocols import StreamingCapable, ToolCapable

    if config.enable_streaming:
        if not isinstance(provider, StreamingCapable):
            raise ValueError(
                f"Provider {config.provider.value} doesn't support streaming. "
                "Set enable_streaming=False or use a different provider."
            )

    if config.allowed_tools:
        if not isinstance(provider, ToolCapable):
            raise ValueError(
                f"Provider {config.provider.value} doesn't support tool restrictions. "
                "Remove allowed_tools or use a different provider."
            )
```

---

### 2. Provider Base Class with Lifecycle

**Pattern Source**: `/base/backend/dataops/core/dao.py` (BaseDAO)

```python
# backend/agents/core/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from backend.agents.core.config import AgentConfig
from backend.agents.core.models import ExecutionResult


class Provider(ABC):
    """Abstract base class for all CLI providers with complete lifecycle management.

    Follows BaseDAO pattern from base/backend/dataops/core/dao.py:
    - Lifecycle methods (connect, disconnect, health_check)
    - Context manager support for resource cleanup
    - Capability query methods
    - Async operations throughout
    """

    def __init__(self, config: AgentConfig):
        """Initialize provider with configuration.

        Args:
            config: Agent configuration
        """
        self.config = config
        self._connected = False

    # Lifecycle Management
    @abstractmethod
    async def connect(self) -> None:
        """Initialize provider connection/resources.

        Called before first use. May setup:
        - CLI executable verification
        - Environment variable validation
        - Working directory creation
        - Audit log initialization
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanup provider resources.

        Called after last use. Should cleanup:
        - Temporary files
        - Background processes
        - Open file handles
        - Cached state
        """

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health and availability.

        Returns:
            Health status dict with keys:
            - status: "healthy" | "degraded" | "unhealthy"
            - cli_available: bool
            - version: str | None
            - issues: list[str]
        """

    # Capability Queries
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether provider supports streaming execution."""

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether provider supports tool use/restrictions."""

    @abstractmethod
    def max_context_size(self) -> int:
        """Maximum context size in tokens."""

    @abstractmethod
    def model_name(self) -> str:
        """Model identifier (e.g., 'claude-3-5-sonnet-20241022')."""

    # Execution Interface
    @abstractmethod
    async def execute(
        self,
        instruction: str,
        config: AgentConfig,
        stdin: str | None = None,
        cwd: Path | None = None,
    ) -> ExecutionResult:
        """Execute instruction with provider (streaming auto-detected from config).

        Args:
            instruction: Instruction text to execute
            config: Execution configuration (overrides instance config)
            stdin: Optional stdin data
            cwd: Optional working directory

        Returns:
            ExecutionResult with output, metadata, and audit info

        Raises:
            AgentError: On execution failure
            ProviderError: On provider-specific errors
        """

    # Context Manager Support (Following BaseDAO pattern)
    async def __aenter__(self) -> "Provider":
        """Async context manager entry - connect to provider."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - disconnect from provider."""
        await self.disconnect()
```

---

### 3. Protocol-Based Capabilities

**Pattern Source**: `/base/backend/llms/` (implied from provider patterns)

```python
# backend/agents/core/protocols.py
from typing import Protocol, AsyncIterator, runtime_checkable
from backend.agents.core.models import StreamChunk, ExecutionResult


@runtime_checkable
class StreamingCapable(Protocol):
    """Protocol for providers supporting streaming execution."""

    def supports_streaming(self) -> bool:
        """Whether provider supports streaming."""
        ...

    async def execute_streaming(
        self,
        instruction: str,
        stdin: str | None = None,
        cwd: Path | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Execute with streaming output.

        Yields:
            StreamChunk instances as they arrive
        """
        ...


@runtime_checkable
class ToolCapable(Protocol):
    """Protocol for providers supporting tool use/restrictions."""

    def supports_tools(self) -> bool:
        """Whether provider supports tools."""
        ...

    def list_available_tools(self) -> list[str]:
        """Get list of all available tools."""
        ...

    def map_tool_name(self, canonical: str) -> str:
        """Map canonical tool name to provider-specific name.

        Args:
            canonical: Canonical tool name (e.g., 'Bash')

        Returns:
            Provider-specific tool name
        """
        ...


@runtime_checkable
class VisionCapable(Protocol):
    """Protocol for providers supporting image inputs (future)."""

    def supports_vision(self) -> bool:
        """Whether provider supports vision."""
        ...

    def max_image_size(self) -> int:
        """Maximum image size in bytes."""
        ...


@runtime_checkable
class ThinkingCapable(Protocol):
    """Protocol for providers supporting extended thinking (future)."""

    def supports_thinking(self) -> bool:
        """Whether provider supports thinking mode."""
        ...

    def max_thinking_tokens(self) -> int:
        """Maximum thinking budget in tokens."""
        ...
```

---

### 4. Structured Error Handling

**Pattern Source**: `/base/backend/dataops/core/exceptions.py` (StorageError)

```python
# backend/agents/core/exceptions.py
from datetime import datetime
from typing import Any
from backend.agents.providers.models import CLIProvider


class AgentError(Exception):
    """Base exception for all agent execution errors with structured context."""

    def __init__(
        self,
        message: str,
        provider: CLIProvider | None = None,
        session_id: str | None = None,
        **context: Any,
    ):
        """Initialize error with structured context.

        Args:
            message: Error description
            provider: Provider that raised error (if applicable)
            session_id: Session/execution ID (if applicable)
            **context: Additional context (command, exit_code, etc.)
        """
        super().__init__(message)
        self.provider = provider
        self.session_id = session_id
        self.context = context
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to structured dict for logging/monitoring.

        Returns:
            Dict with error_type, message, provider, session_id, context
        """
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "provider": self.provider.value if self.provider else None,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            **self.context,
        }

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"{self.__class__.__name__}({self.to_dict()})"


class ProviderError(AgentError):
    """Provider-specific execution error (non-zero exit, crash, etc.)."""


class ConfigurationError(AgentError):
    """Invalid configuration error."""


class CapabilityError(AgentError):
    """Provider lacks required capability."""


class StreamingError(AgentError):
    """Streaming execution error (malformed JSON, etc.)."""


class HookValidationError(AgentError):
    """Hook validation failure."""


class TimeoutError(AgentError):
    """Execution timeout error."""
```

---

### 5. Configuration Models

```python
# backend/agents/core/config.py
from dataclasses import dataclass, field
from pathlib import Path
from backend.agents.providers.models import CLIProvider, ClaudeModel


@dataclass(frozen=True)
class AgentConfig:
    """Agent execution configuration.

    Immutable configuration object for agent execution.
    """

    # Provider Selection
    provider: CLIProvider = CLIProvider.CLAUDE
    model: str = ClaudeModel.SONNET_3_5.value

    # Execution Settings
    enable_streaming: bool = False
    session_id: str | None = None
    working_dir: Path | None = None
    timeout: int | None = None  # seconds

    # Tool Restrictions
    allowed_tools: list[str] = field(default_factory=list)

    # Hook Configuration
    enable_hooks: bool = True
    hooks_config_path: Path | None = None

    # Audit Configuration
    audit_log_path: Path | None = None
    enable_first_output_markers: bool = True  # For hang detection

    # Advanced Settings
    max_tokens: int | None = None
    temperature: float | None = None
    custom_system_prompt: str | None = None


# backend/agents/core/presets.py
class AgentConfigPresets:
    """Preset configurations for common use cases."""

    @staticmethod
    def audit_runner() -> AgentConfig:
        """Configuration for audit operations."""
        return AgentConfig(
            provider=CLIProvider.CLAUDE,
            model=ClaudeModel.SONNET_3_5.value,
            enable_streaming=True,
            enable_hooks=True,
            enable_first_output_markers=True,
        )

    @staticmethod
    def task_executor() -> AgentConfig:
        """Configuration for task execution."""
        return AgentConfig(
            provider=CLIProvider.CLAUDE,
            model=ClaudeModel.SONNET_3_5.value,
            enable_streaming=False,
            enable_hooks=True,
        )

    @staticmethod
    def docs_generator() -> AgentConfig:
        """Configuration for documentation generation."""
        return AgentConfig(
            provider=CLIProvider.CLAUDE,
            model=ClaudeModel.SONNET_3_5.value,
            enable_streaming=False,
            enable_hooks=False,  # Docs don't need validation
            max_tokens=8000,
        )

    @staticmethod
    def gemini_experimental() -> AgentConfig:
        """Configuration for Gemini provider testing."""
        return AgentConfig(
            provider=CLIProvider.GEMINI,
            model="gemini-2.0-flash-exp",
            enable_streaming=True,
            enable_hooks=True,
            enable_first_output_markers=True,
        )
```

---

### 6. Execution Result Models

```python
# backend/agents/core/models.py
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExecutionResult:
    """Result from provider execution."""

    # Output
    stdout: str
    stderr: str
    exit_code: int

    # Metadata
    session_id: str
    provider: str
    model: str
    execution_time: float  # seconds
    timestamp: datetime = field(default_factory=datetime.now)

    # Audit Information
    audit_log_path: Path | None = None
    first_output_time: float | None = None  # seconds from start
    total_tokens: int | None = None
    hook_validations: list[dict[str, Any]] = field(default_factory=list)

    # Error Context (if failed)
    error: dict[str, Any] | None = None

    @property
    def success(self) -> bool:
        """Whether execution succeeded."""
        return self.exit_code == 0 and self.error is None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging/serialization."""
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "session_id": self.session_id,
            "provider": self.provider,
            "model": self.model,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
            "audit_log_path": str(self.audit_log_path) if self.audit_log_path else None,
            "first_output_time": self.first_output_time,
            "total_tokens": self.total_tokens,
            "hook_validations": self.hook_validations,
            "error": self.error,
            "success": self.success,
        }


@dataclass
class StreamChunk:
    """Single chunk from streaming execution."""

    # Chunk Content
    type: str  # "text", "tool_use", "tool_result", "thinking"
    content: str
    raw_json: dict[str, Any]

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    cumulative_tokens: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging."""
        return {
            "type": self.type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "cumulative_tokens": self.cumulative_tokens,
        }
```

---

## Provider Implementations

### 7. Claude Provider (Extracted from agent_cli.py:322-1208)

```python
# backend/agents/providers/claude/provider.py
import asyncio
from pathlib import Path
from typing import Any
from backend.agents.core.base import Provider
from backend.agents.core.config import AgentConfig
from backend.agents.core.exceptions import ProviderError
from backend.agents.core.models import ExecutionResult
from backend.agents.core.protocols import StreamingCapable, ToolCapable
from backend.agents.providers.claude.streaming import ClaudeStreamingExecutor
from backend.agents.providers.claude.hooks import ClaudeHookManager
from backend.agents.providers.claude.tools import ClaudeToolMapper
from backend.agents.utils.subprocess import AsyncSubprocess


class ClaudeProvider(Provider, StreamingCapable, ToolCapable):
    """Claude CLI provider implementation.

    Extracted from scripts/automation/agent_cli.py:322-1208 (ClaudeAgentCLI).

    Implements:
    - StreamingCapable: Full streaming support with first-output markers
    - ToolCapable: Tool restriction via --disable-tools flag
    """

    # Tool catalog (from agent_cli.py:331-354)
    ALL_TOOLS = [
        "Bash", "BashOutput", "Edit", "Glob", "Grep", "KillShell",
        "NotebookEdit", "Read", "SlashCommand", "Task", "TodoWrite",
        "WebFetch", "WebSearch", "Write"
    ]

    def __init__(self, config: AgentConfig):
        """Initialize Claude provider.

        Args:
            config: Agent configuration
        """
        super().__init__(config)
        self._hook_manager = ClaudeHookManager(config)
        self._tool_mapper = ClaudeToolMapper(self.ALL_TOOLS)
        self._streaming_executor = ClaudeStreamingExecutor(config)
        self._subprocess = AsyncSubprocess()

    # Lifecycle Methods
    async def connect(self) -> None:
        """Initialize Claude provider resources."""
        if self._connected:
            return

        # Verify claude CLI is available
        health = await self.health_check()
        if health["status"] == "unhealthy":
            raise ProviderError(
                "Claude CLI not available",
                provider=self.config.provider,
                issues=health["issues"],
            )

        # Setup hook files if enabled
        if self.config.enable_hooks:
            await self._hook_manager.setup()

        self._connected = True

    async def disconnect(self) -> None:
        """Cleanup Claude provider resources."""
        if not self._connected:
            return

        # Cleanup hook files
        if self.config.enable_hooks:
            await self._hook_manager.cleanup()

        self._connected = False

    async def health_check(self) -> dict[str, Any]:
        """Check Claude CLI health.

        Returns:
            Health status with CLI availability and version
        """
        try:
            result = await self._subprocess.run(
                ["claude", "--version"],
                timeout=5.0,
            )
            version = result["stdout"].strip() if result["exit_code"] == 0 else None
            return {
                "status": "healthy" if result["exit_code"] == 0 else "unhealthy",
                "cli_available": result["exit_code"] == 0,
                "version": version,
                "issues": [] if result["exit_code"] == 0 else ["Claude CLI not found"],
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "cli_available": False,
                "version": None,
                "issues": [str(e)],
            }

    # Capability Methods
    def supports_streaming(self) -> bool:
        """Claude supports streaming."""
        return True

    def supports_tools(self) -> bool:
        """Claude supports tool restrictions."""
        return True

    def max_context_size(self) -> int:
        """Claude Sonnet 3.5 max context."""
        return 200_000

    def model_name(self) -> str:
        """Current model identifier."""
        return self.config.model

    # Execution Methods
    async def execute(
        self,
        instruction: str,
        config: AgentConfig,
        stdin: str | None = None,
        cwd: Path | None = None,
    ) -> ExecutionResult:
        """Execute instruction with Claude CLI.

        Args:
            instruction: Instruction to execute
            config: Execution config (overrides instance config)
            stdin: Optional stdin data
            cwd: Optional working directory

        Returns:
            ExecutionResult with output and metadata
        """
        if not self._connected:
            await self.connect()

        # Build command
        cmd = self._build_command(instruction, config)
        cwd = cwd or config.working_dir or Path.cwd()

        # Execute with streaming or blocking
        if config.enable_streaming:
            return await self._streaming_executor.execute(
                cmd=cmd,
                stdin=stdin,
                cwd=cwd,
                audit_log_path=config.audit_log_path,
            )
        else:
            return await self._execute_blocking(cmd, stdin, cwd)

    def _build_command(self, instruction: str, config: AgentConfig) -> list[str]:
        """Build claude CLI command.

        Args:
            instruction: Instruction text
            config: Agent configuration

        Returns:
            Command arguments list
        """
        cmd = ["claude"]

        # Add model
        if config.model:
            cmd.extend(["--model", config.model])

        # Add tool restrictions
        if config.allowed_tools:
            disabled_tools = self._tool_mapper.get_disabled_tools(config.allowed_tools)
            if disabled_tools:
                cmd.extend(["--disable-tools", ",".join(disabled_tools)])

        # Add max tokens
        if config.max_tokens:
            cmd.extend(["--max-tokens", str(config.max_tokens)])

        # Add temperature
        if config.temperature is not None:
            cmd.extend(["--temperature", str(config.temperature)])

        # Add custom system prompt
        if config.custom_system_prompt:
            cmd.extend(["--system", config.custom_system_prompt])

        # Add instruction
        cmd.append(instruction)

        return cmd

    async def _execute_blocking(
        self,
        cmd: list[str],
        stdin: str | None,
        cwd: Path,
    ) -> ExecutionResult:
        """Execute blocking (non-streaming) command.

        Args:
            cmd: Command arguments
            stdin: Optional stdin data
            cwd: Working directory

        Returns:
            ExecutionResult
        """
        import time
        start_time = time.time()

        result = await self._subprocess.run(
            cmd=cmd,
            input_text=stdin,
            cwd=str(cwd),
            timeout=self.config.timeout,
        )

        execution_time = time.time() - start_time

        return ExecutionResult(
            stdout=result["stdout"],
            stderr=result["stderr"],
            exit_code=result["exit_code"],
            session_id=self.config.session_id or "unknown",
            provider=self.config.provider.value,
            model=self.config.model,
            execution_time=execution_time,
        )

    # ToolCapable Protocol Methods
    def list_available_tools(self) -> list[str]:
        """Get list of all Claude tools."""
        return self.ALL_TOOLS.copy()

    def map_tool_name(self, canonical: str) -> str:
        """Map canonical to Claude tool name (identity mapping)."""
        return canonical
```

---

### 8. Claude Streaming Executor

```python
# backend/agents/providers/claude/streaming.py
import asyncio
import time
from pathlib import Path
from backend.agents.core.config import AgentConfig
from backend.agents.core.models import ExecutionResult
from backend.agents.core.exceptions import StreamingError
from backend.agents.utils.subprocess import AsyncSubprocess


class ClaudeStreamingExecutor:
    """Claude streaming execution with first-output markers.

    Extracted from agent_cli.py:846-948 (_execute_streaming).

    Features:
    - First-output timing for hang detection
    - Real-time stdout/stderr capture
    - Audit log writing
    """

    def __init__(self, config: AgentConfig):
        """Initialize streaming executor.

        Args:
            config: Agent configuration
        """
        self.config = config
        self._subprocess = AsyncSubprocess()

    async def execute(
        self,
        cmd: list[str],
        stdin: str | None,
        cwd: Path,
        audit_log_path: Path | None,
    ) -> ExecutionResult:
        """Execute with streaming output capture.

        Args:
            cmd: Command arguments
            stdin: Optional stdin data
            cwd: Working directory
            audit_log_path: Optional audit log path

        Returns:
            ExecutionResult with streaming metadata
        """
        start_time = time.time()
        first_output_time = None
        stdout_lines = []
        stderr_lines = []

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if stdin else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )

        # Write stdin if provided
        if stdin and process.stdin:
            process.stdin.write(stdin.encode())
            await process.stdin.drain()
            process.stdin.close()

        # Stream stdout and stderr concurrently
        async def read_stdout():
            nonlocal first_output_time
            async for line in process.stdout:
                line_str = line.decode()
                stdout_lines.append(line_str)

                # Mark first output time
                if first_output_time is None:
                    first_output_time = time.time() - start_time
                    if audit_log_path and self.config.enable_first_output_markers:
                        await self._write_first_output_marker(audit_log_path, first_output_time)

        async def read_stderr():
            async for line in process.stderr:
                stderr_lines.append(line.decode())

        # Run both readers concurrently
        await asyncio.gather(read_stdout(), read_stderr())

        # Wait for process to complete
        exit_code = await process.wait()
        execution_time = time.time() - start_time

        return ExecutionResult(
            stdout="".join(stdout_lines),
            stderr="".join(stderr_lines),
            exit_code=exit_code,
            session_id=self.config.session_id or "unknown",
            provider=self.config.provider.value,
            model=self.config.model,
            execution_time=execution_time,
            first_output_time=first_output_time,
            audit_log_path=audit_log_path,
        )

    async def _write_first_output_marker(self, audit_log_path: Path, elapsed: float) -> None:
        """Write first-output marker to audit log.

        Args:
            audit_log_path: Audit log file path
            elapsed: Seconds since execution start
        """
        async with asyncio.Lock():  # Prevent concurrent writes
            with audit_log_path.open("a") as f:
                f.write(f"\n=== FIRST OUTPUT: {elapsed:.4f}s ===\n\n")
```

---

### 9. Gemini Provider (NEW Implementation)

```python
# backend/agents/providers/gemini/provider.py
import asyncio
from pathlib import Path
from typing import Any
from backend.agents.core.base import Provider
from backend.agents.core.config import AgentConfig
from backend.agents.core.exceptions import ProviderError
from backend.agents.core.models import ExecutionResult
from backend.agents.core.protocols import StreamingCapable, ToolCapable
from backend.agents.providers.gemini.streaming import GeminiStreamingExecutor
from backend.agents.providers.gemini.tools import GeminiToolMapper
from backend.agents.utils.subprocess import AsyncSubprocess


class GeminiProvider(Provider, StreamingCapable, ToolCapable):
    """Gemini CLI provider implementation.

    NEW IMPLEMENTATION based on gemini-cli patterns.

    Implements:
    - StreamingCapable: Full streaming with JSON message parsing
    - ToolCapable: Tool mapping Claude->Gemini names

    Key Differences from Claude:
    - Streaming: JSON objects per message (not plain text)
    - Tools: Different names (Bash->bash, Read->read_file, etc.)
    - Auth: Requires GOOGLE_API_KEY or gcloud auth
    - No hook files: Gemini CLI doesn't support hook system
    """

    # Tool mapping (Claude canonical -> Gemini)
    TOOL_MAPPING = {
        "Bash": "bash",
        "Read": "read_file",
        "Write": "write_file",
        "Edit": "edit_file",
        "Glob": "glob",
        "Grep": "grep",
        # Gemini doesn't support: Task, TodoWrite, WebSearch, SlashCommand
    }

    def __init__(self, config: AgentConfig):
        """Initialize Gemini provider.

        Args:
            config: Agent configuration
        """
        super().__init__(config)
        self._tool_mapper = GeminiToolMapper(self.TOOL_MAPPING)
        self._streaming_executor = GeminiStreamingExecutor(config)
        self._subprocess = AsyncSubprocess()

    # Lifecycle Methods
    async def connect(self) -> None:
        """Initialize Gemini provider resources."""
        if self._connected:
            return

        # Verify gemini CLI is available
        health = await self.health_check()
        if health["status"] == "unhealthy":
            raise ProviderError(
                "Gemini CLI not available",
                provider=self.config.provider,
                issues=health["issues"],
            )

        # Verify authentication
        if not await self._check_auth():
            raise ProviderError(
                "Gemini authentication not configured. Set GOOGLE_API_KEY or run 'gcloud auth login'",
                provider=self.config.provider,
            )

        self._connected = True

    async def disconnect(self) -> None:
        """Cleanup Gemini provider resources."""
        if not self._connected:
            return
        # Gemini has no cleanup (no hook files, etc.)
        self._connected = False

    async def health_check(self) -> dict[str, Any]:
        """Check Gemini CLI health.

        Returns:
            Health status with CLI availability and version
        """
        try:
            result = await self._subprocess.run(
                ["gemini", "--version"],
                timeout=5.0,
            )
            version = result["stdout"].strip() if result["exit_code"] == 0 else None
            return {
                "status": "healthy" if result["exit_code"] == 0 else "unhealthy",
                "cli_available": result["exit_code"] == 0,
                "version": version,
                "issues": [] if result["exit_code"] == 0 else ["Gemini CLI not found"],
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "cli_available": False,
                "version": None,
                "issues": [str(e)],
            }

    async def _check_auth(self) -> bool:
        """Check if Gemini authentication is configured.

        Returns:
            True if authenticated, False otherwise
        """
        import os

        # Check for API key
        if os.environ.get("GOOGLE_API_KEY"):
            return True

        # Check gcloud auth
        try:
            result = await self._subprocess.run(
                ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
                timeout=5.0,
            )
            return bool(result["stdout"].strip())
        except Exception:
            return False

    # Capability Methods
    def supports_streaming(self) -> bool:
        """Gemini supports streaming."""
        return True

    def supports_tools(self) -> bool:
        """Gemini supports tool restrictions (via mapping)."""
        return True

    def max_context_size(self) -> int:
        """Gemini 2.0 Flash max context."""
        return 1_000_000  # 1M tokens

    def model_name(self) -> str:
        """Current model identifier."""
        return self.config.model

    # Execution Methods
    async def execute(
        self,
        instruction: str,
        config: AgentConfig,
        stdin: str | None = None,
        cwd: Path | None = None,
    ) -> ExecutionResult:
        """Execute instruction with Gemini CLI.

        Args:
            instruction: Instruction to execute
            config: Execution config (overrides instance config)
            stdin: Optional stdin data
            cwd: Optional working directory

        Returns:
            ExecutionResult with output and metadata
        """
        if not self._connected:
            await self.connect()

        # Build command
        cmd = self._build_command(instruction, config)
        cwd = cwd or config.working_dir or Path.cwd()

        # Execute with streaming or blocking
        if config.enable_streaming:
            return await self._streaming_executor.execute(
                cmd=cmd,
                stdin=stdin,
                cwd=cwd,
                audit_log_path=config.audit_log_path,
            )
        else:
            return await self._execute_blocking(cmd, stdin, cwd)

    def _build_command(self, instruction: str, config: AgentConfig) -> list[str]:
        """Build gemini CLI command.

        Args:
            instruction: Instruction text
            config: Agent configuration

        Returns:
            Command arguments list
        """
        cmd = ["gemini"]

        # Add model
        if config.model:
            cmd.extend(["--model", config.model])

        # Add max tokens
        if config.max_tokens:
            cmd.extend(["--max-tokens", str(config.max_tokens)])

        # Add temperature
        if config.temperature is not None:
            cmd.extend(["--temperature", str(config.temperature)])

        # Add streaming flag
        if config.enable_streaming:
            cmd.append("--stream")

        # Gemini doesn't support tool restrictions via CLI
        # (tool mapping happens in hook validators instead)

        # Add instruction
        cmd.append(instruction)

        return cmd

    async def _execute_blocking(
        self,
        cmd: list[str],
        stdin: str | None,
        cwd: Path,
    ) -> ExecutionResult:
        """Execute blocking (non-streaming) command.

        Args:
            cmd: Command arguments
            stdin: Optional stdin data
            cwd: Working directory

        Returns:
            ExecutionResult
        """
        import time
        start_time = time.time()

        result = await self._subprocess.run(
            cmd=cmd,
            input_text=stdin,
            cwd=str(cwd),
            timeout=self.config.timeout,
        )

        execution_time = time.time() - start_time

        return ExecutionResult(
            stdout=result["stdout"],
            stderr=result["stderr"],
            exit_code=result["exit_code"],
            session_id=self.config.session_id or "unknown",
            provider=self.config.provider.value,
            model=self.config.model,
            execution_time=execution_time,
        )

    # ToolCapable Protocol Methods
    def list_available_tools(self) -> list[str]:
        """Get list of available Gemini tools."""
        return list(self.TOOL_MAPPING.values())

    def map_tool_name(self, canonical: str) -> str:
        """Map canonical (Claude) to Gemini tool name.

        Args:
            canonical: Claude tool name (e.g., 'Bash')

        Returns:
            Gemini tool name (e.g., 'bash')
        """
        return self.TOOL_MAPPING.get(canonical, canonical.lower())
```

---

### 10. Gemini Streaming Executor

```python
# backend/agents/providers/gemini/streaming.py
import asyncio
import json
import time
from pathlib import Path
from backend.agents.core.config import AgentConfig
from backend.agents.core.models import ExecutionResult
from backend.agents.core.exceptions import StreamingError
from backend.agents.providers.gemini.parser import GeminiMessageParser
from backend.agents.utils.subprocess import AsyncSubprocess


class GeminiStreamingExecutor:
    """Gemini streaming execution with JSON message parsing.

    Gemini streaming format:
    {"type": "message", "content": [{"type": "text", "text": "..."}]}
    {"type": "tool_use", "name": "bash", "input": {...}}
    {"type": "tool_result", "tool_use_id": "...", "content": "..."}

    Features:
    - JSON message parsing
    - First-output timing for hang detection
    - Real-time message assembly
    - Audit log writing
    """

    def __init__(self, config: AgentConfig):
        """Initialize streaming executor.

        Args:
            config: Agent configuration
        """
        self.config = config
        self._subprocess = AsyncSubprocess()
        self._parser = GeminiMessageParser()

    async def execute(
        self,
        cmd: list[str],
        stdin: str | None,
        cwd: Path,
        audit_log_path: Path | None,
    ) -> ExecutionResult:
        """Execute with streaming JSON message parsing.

        Args:
            cmd: Command arguments
            stdin: Optional stdin data
            cwd: Working directory
            audit_log_path: Optional audit log path

        Returns:
            ExecutionResult with streaming metadata
        """
        start_time = time.time()
        first_output_time = None
        messages = []
        stderr_lines = []

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if stdin else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )

        # Write stdin if provided
        if stdin and process.stdin:
            process.stdin.write(stdin.encode())
            await process.stdin.drain()
            process.stdin.close()

        # Stream stdout (JSON messages) and stderr concurrently
        async def read_stdout():
            nonlocal first_output_time
            async for line in process.stdout:
                line_str = line.decode().strip()
                if not line_str:
                    continue

                # Parse JSON message
                try:
                    msg = json.loads(line_str)
                    messages.append(msg)

                    # Mark first output time
                    if first_output_time is None:
                        first_output_time = time.time() - start_time
                        if audit_log_path and self.config.enable_first_output_markers:
                            await self._write_first_output_marker(audit_log_path, first_output_time)

                except json.JSONDecodeError as e:
                    # Log malformed JSON but continue
                    stderr_lines.append(f"WARNING: Malformed JSON: {line_str}\n")

        async def read_stderr():
            async for line in process.stderr:
                stderr_lines.append(line.decode())

        # Run both readers concurrently
        await asyncio.gather(read_stdout(), read_stderr())

        # Wait for process to complete
        exit_code = await process.wait()
        execution_time = time.time() - start_time

        # Assemble final output from messages
        stdout = self._parser.assemble_output(messages)

        return ExecutionResult(
            stdout=stdout,
            stderr="".join(stderr_lines),
            exit_code=exit_code,
            session_id=self.config.session_id or "unknown",
            provider=self.config.provider.value,
            model=self.config.model,
            execution_time=execution_time,
            first_output_time=first_output_time,
            audit_log_path=audit_log_path,
        )

    async def _write_first_output_marker(self, audit_log_path: Path, elapsed: float) -> None:
        """Write first-output marker to audit log.

        Args:
            audit_log_path: Audit log file path
            elapsed: Seconds since execution start
        """
        async with asyncio.Lock():  # Prevent concurrent writes
            with audit_log_path.open("a") as f:
                f.write(f"\n=== FIRST OUTPUT: {elapsed:.4f}s ===\n\n")
```

---

### 11. Gemini Message Parser

```python
# backend/agents/providers/gemini/parser.py
from typing import Any


class GeminiMessageParser:
    """Parse Gemini streaming JSON messages into output.

    Message types:
    - message: Text response
    - tool_use: Tool invocation
    - tool_result: Tool execution result
    - thinking: Extended thinking (future)
    """

    def assemble_output(self, messages: list[dict[str, Any]]) -> str:
        """Assemble final output from message stream.

        Args:
            messages: List of parsed JSON messages

        Returns:
            Assembled output text
        """
        output_parts = []

        for msg in messages:
            msg_type = msg.get("type", "")

            if msg_type == "message":
                # Extract text content
                content = msg.get("content", [])
                for item in content:
                    if item.get("type") == "text":
                        output_parts.append(item.get("text", ""))

            elif msg_type == "tool_use":
                # Format tool use
                name = msg.get("name", "unknown")
                input_data = msg.get("input", {})
                output_parts.append(f"\n[TOOL USE: {name}]\n{input_data}\n")

            elif msg_type == "tool_result":
                # Format tool result
                content = msg.get("content", "")
                output_parts.append(f"\n[TOOL RESULT]\n{content}\n")

            elif msg_type == "thinking":
                # Format thinking (future)
                thinking = msg.get("thinking", "")
                output_parts.append(f"\n[THINKING]\n{thinking}\n")

        return "".join(output_parts)
```

---

## Operations Facade

### 12. Unified Operation Interface

**Pattern Source**: `/files/backend/mcp/filesys/tools/facade/filesystem.py`

```python
# backend/agents/operations/facade.py
from typing import Literal, Any, Callable, Awaitable
from pathlib import Path
from backend.agents.core.base import Provider
from backend.agents.core.config import AgentConfig
from backend.agents.operations.audit import audit_operation
from backend.agents.operations.tasks import task_operation
from backend.agents.operations.sync import sync_operation
from backend.agents.operations.docs import docs_operation


# Operation type
OperationType = Literal["audit", "task", "sync", "docs"]


class OperationResult:
    """Result from agent operation."""

    def __init__(
        self,
        success: bool,
        output: str,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        self.success = success
        self.output = output
        self.metadata = metadata or {}
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging."""
        return {
            "success": self.success,
            "output": self.output,
            "metadata": self.metadata,
            "error": self.error,
        }


# Operation handlers registry (following facade pattern)
OPERATION_HANDLERS: dict[OperationType, Callable[..., Awaitable[OperationResult]]] = {
    "audit": audit_operation,
    "task": task_operation,
    "sync": sync_operation,
    "docs": docs_operation,
}


async def agent_operation(
    provider: Provider,
    operation: OperationType,
    config: AgentConfig,
    **kwargs: Any,
) -> OperationResult:
    """Unified facade for all agent operations.

    Follows facade pattern from files/backend/mcp/filesys/tools/facade/filesystem.py.

    Args:
        provider: Initialized provider instance
        operation: Operation type to execute
        config: Agent configuration
        **kwargs: Operation-specific arguments

    Returns:
        OperationResult with success, output, metadata

    Raises:
        ValueError: If operation type unknown
    """
    handler = OPERATION_HANDLERS.get(operation)
    if not handler:
        raise ValueError(
            f"Unknown operation: {operation}\n"
            f"Available operations: {list(OPERATION_HANDLERS.keys())}"
        )

    return await handler(provider=provider, config=config, **kwargs)


# Example operation implementation
# backend/agents/operations/audit.py
async def audit_operation(
    provider: Provider,
    config: AgentConfig,
    file_path: Path | None = None,
    directory: Path | None = None,
    pattern: str | None = None,
    **kwargs: Any,
) -> OperationResult:
    """Execute audit operation.

    Args:
        provider: Provider instance
        config: Agent configuration
        file_path: Optional single file to audit
        directory: Optional directory to audit
        pattern: Optional file pattern (e.g., '*.py')
        **kwargs: Additional arguments

    Returns:
        OperationResult with audit findings
    """
    # Build audit instruction
    instruction = _build_audit_instruction(file_path, directory, pattern)

    # Execute with provider
    result = await provider.execute(
        instruction=instruction,
        config=config,
        cwd=directory or Path.cwd(),
    )

    # Parse audit output
    findings = _parse_audit_output(result.stdout)

    return OperationResult(
        success=result.success,
        output=result.stdout,
        metadata={
            "findings_count": len(findings),
            "execution_time": result.execution_time,
            "provider": result.provider,
        },
    )
```

---

## Provider Registry and Auto-Registration

### 13. Provider Registry

```python
# backend/agents/providers/registry.py
from backend.agents.core.factory import ProviderFactory
from backend.agents.providers.models import CLIProvider
from backend.agents.providers.claude.provider import ClaudeProvider
from backend.agents.providers.gemini.provider import GeminiProvider


def register_all_providers() -> None:
    """Register all available providers with factory.

    Called on module import to auto-register providers.
    """
    ProviderFactory.register(CLIProvider.CLAUDE, ClaudeProvider)
    ProviderFactory.register(CLIProvider.GEMINI, GeminiProvider)


# Auto-register on import
register_all_providers()
```

---

## Usage Examples

### 14. Basic Usage

```python
# Example 1: Simple execution with default config
from backend.agents.core.factory import ProviderFactory
from backend.agents.core.presets import AgentConfigPresets

config = AgentConfigPresets.audit_runner()
async with ProviderFactory.create(config) as provider:
    result = await provider.execute(
        instruction="Audit the file example.py for code quality issues",
        config=config,
    )
    print(result.stdout)


# Example 2: Multi-provider comparison
from backend.agents.providers.models import CLIProvider

configs = [
    AgentConfig(provider=CLIProvider.CLAUDE, enable_streaming=True),
    AgentConfig(provider=CLIProvider.GEMINI, enable_streaming=True),
]

for config in configs:
    async with ProviderFactory.create(config) as provider:
        result = await provider.execute(
            instruction="Explain the factory pattern",
            config=config,
        )
        print(f"{config.provider.value}: {result.execution_time:.2f}s")


# Example 3: Using operations facade
from backend.agents.operations.facade import agent_operation
from pathlib import Path

config = AgentConfigPresets.audit_runner()
async with ProviderFactory.create(config) as provider:
    result = await agent_operation(
        provider=provider,
        operation="audit",
        config=config,
        directory=Path("backend/agents"),
        pattern="*.py",
    )
    print(f"Audit findings: {result.metadata['findings_count']}")


# Example 4: Capability validation
from backend.agents.core.protocols import StreamingCapable

config = AgentConfig(provider=CLIProvider.GEMINI, enable_streaming=True)
provider = ProviderFactory.create(config)

if isinstance(provider, StreamingCapable):
    print("Provider supports streaming")
    async with provider:
        async for chunk in provider.execute_streaming(...):
            print(chunk.content, end="", flush=True)
```

---

## Migration Plan

### Phase 1: Core Infrastructure (Week 1)

**Tasks**:
1. Create `backend/agents/core/` directory structure
2. Implement `exceptions.py` with structured errors
3. Implement `protocols.py` with capability protocols
4. Implement `base.py` with Provider ABC
5. Implement `config.py` and `presets.py`
6. Implement `models.py` (ExecutionResult, StreamChunk)
7. Implement `factory.py` with registry pattern
8. Write unit tests for all core components

**Success Criteria**:
- [ ] All core modules <200 lines
- [ ] 90%+ test coverage
- [ ] Factory pattern validated with mock providers
- [ ] Protocol validation working

### Phase 2: Provider Extraction (Week 2)

**Tasks**:
1. Create `providers/claude/` package
2. Extract ClaudeProvider from agent_cli.py:322-1208
3. Split into provider.py, streaming.py, hooks.py, tools.py
4. Convert all blocking I/O to async/await
5. Implement lifecycle methods (connect, disconnect, health_check)
6. Implement capability methods
7. Write comprehensive tests (streaming, hooks, tools)

**Success Criteria**:
- [ ] ClaudeProvider fully async
- [ ] All existing Claude functionality preserved
- [ ] <300 lines per module
- [ ] First-output markers working
- [ ] Hook file management working

### Phase 3: Gemini Implementation (Week 3)

**Tasks**:
1. Create `providers/gemini/` package
2. Implement GeminiProvider with async/await
3. Implement GeminiStreamingExecutor with JSON parsing
4. Implement GeminiMessageParser
5. Implement GeminiToolMapper (Claude->Gemini names)
6. Write comprehensive tests (streaming, parsing, auth)
7. Document Gemini-specific behavior

**Success Criteria**:
- [ ] GeminiProvider fully async
- [ ] Streaming JSON parsing working
- [ ] Tool mapping validated
- [ ] Auth checking working (API key + gcloud)
- [ ] First-output markers working

### Phase 4: Operations Facade (Week 4)

**Tasks**:
1. Create `operations/` directory
2. Implement facade.py with unified interface
3. Extract audit operation from scripts/automation/audit.py
4. Extract task operation from scripts/automation/tasks.py
5. Extract sync operation from scripts/automation/sync.py
6. Extract docs operation (if exists)
7. Write integration tests

**Success Criteria**:
- [ ] Facade pattern working
- [ ] All operations accessible via agent_operation()
- [ ] Operations composable
- [ ] Provider-agnostic

### Phase 5: Hook Registry (Week 5)

**Tasks**:
1. Create `hooks/` directory structure
2. Implement HookValidator ABC
3. Implement hook registry with factory
4. Split validators into separate modules
5. Add protocol-based validator capabilities
6. Integrate with provider execution
7. Write comprehensive tests

**Success Criteria**:
- [ ] All validators split into <300 line modules
- [ ] Registry pattern working
- [ ] Hook validation integrated with provider execution
- [ ] TodoValidatorHook preserved

### Phase 6: Integration & Testing (Week 6)

**Tasks**:
1. Update all 11 import sites across codebase
2. Update CLI entry point
3. Run full test suite
4. Run real workload validation
5. Performance benchmarking
6. Documentation updates
7. Migration guide

**Success Criteria**:
- [ ] All tests passing
- [ ] Zero regression on Claude functionality
- [ ] Gemini provider working end-to-end
- [ ] Performance comparable or better
- [ ] Complete documentation

### Phase 7: Cleanup (Week 7)

**Tasks**:
1. Archive `/scripts/automation/` (keep as backup)
2. Update repository documentation
3. Update CI/CD pipelines
4. Add deprecation warnings to old imports
5. Final code review
6. Deployment

**Success Criteria**:
- [ ] Old code archived (not deleted)
- [ ] All references updated
- [ ] CI/CD green
- [ ] Documentation complete

---

## Testing Strategy

### Unit Tests

```
tests/unit/backend/agents/
├── core/
│   ├── test_factory.py              # Factory pattern, registration
│   ├── test_config.py               # Config validation
│   ├── test_protocols.py            # Protocol validation
│   ├── test_exceptions.py           # Structured errors
│   └── test_models.py               # Result models
├── providers/
│   ├── claude/
│   │   ├── test_provider.py         # Lifecycle, execution
│   │   ├── test_streaming.py        # First-output markers
│   │   ├── test_hooks.py            # Hook file management
│   │   └── test_tools.py            # Tool restrictions
│   └── gemini/
│       ├── test_provider.py         # Lifecycle, auth checking
│       ├── test_streaming.py        # JSON parsing, first-output
│       ├── test_parser.py           # Message assembly
│       └── test_tools.py            # Tool mapping
├── operations/
│   ├── test_facade.py               # Facade pattern
│   ├── test_audit.py
│   ├── test_tasks.py
│   └── test_sync.py
└── hooks/
    ├── test_registry.py             # Hook registry
    └── validators/
        ├── test_malicious_behavior.py
        ├── test_command_guard.py
        └── test_todo.py
```

### Integration Tests

```
tests/integration/backend/agents/
├── test_claude_e2e.py               # Claude end-to-end
├── test_gemini_e2e.py               # Gemini end-to-end
├── test_multi_provider.py           # Multi-provider execution
├── test_operations_e2e.py           # Operations facade
└── test_hooks_e2e.py                # Hook validation
```

---

## Success Metrics

### Code Quality
- [ ] **Zero `if provider == ...` checks** - All routing through factory
- [ ] **100% async operations** - No blocking I/O in hot path
- [ ] **<300 lines per module** - No monolithic files
- [ ] **90%+ test coverage** - All critical paths tested

### Architecture
- [ ] **Protocol compliance** - All providers implement required protocols
- [ ] **Composable operations** - Can chain operations via facade
- [ ] **Pluggable providers** - Add new provider without editing factory
- [ ] **Context manager support** - Proper resource cleanup with `async with`

### Functionality
- [ ] **Zero regression** - Existing Claude functionality preserved
- [ ] **Gemini working** - Full Gemini provider implementation
- [ ] **Streaming working** - Both Claude and Gemini streaming
- [ ] **Hooks working** - Hook validation integrated

### Performance
- [ ] **Comparable execution time** - No significant slowdown
- [ ] **Memory efficient** - No memory leaks
- [ ] **Concurrent execution** - Multiple operations can run concurrently

---

**END OF SPECIFICATION V2**
