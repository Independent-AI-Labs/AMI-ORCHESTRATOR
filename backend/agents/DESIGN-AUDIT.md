# AGENT FRAMEWORK DESIGN AUDIT

**Date**: 2025-11-07
**Status**: Architecture Review & Pattern Analysis

---

## Executive Summary

Audit of SPEC-AGENTS.md against established patterns in `/base`, `/files`, `/nodes` modules reveals **significant gaps** in architecture design. The current SPEC copies the monolithic anti-patterns from `/scripts/automation` instead of following proven enterprise patterns from mature modules.

### Critical Findings

1. **❌ NO FACTORY PATTERN** - Spec uses simple `if/else` instead of registry-based factory
2. **❌ NO DAO/BASE CLASS PATTERN** - Provider ABC lacks standard interface methods
3. **❌ NO FACADE PATTERN** - No unified tool consolidation layer
4. **❌ WEAK SEPARATION OF CONCERNS** - Mixing execution, parsing, and I/O in single methods
5. **❌ MISSING ASYNC SUPPORT** - No async/await for I/O operations
6. **❌ NO PROPER ERROR HIERARCHY** - Exceptions lack context managers and structured handling
7. **❌ MISSING PROTOCOL PATTERN** - No provider capability negotiation
8. **❌ NO REGISTRY AUTO-DISCOVERY** - Manual provider registration instead of plugin system

---

## Best Practices from Established Modules

### Pattern 1: Factory with Registry (from `base/backend/dataops/core/factory.py`)

**GOOD CODE** (DAOFactory):
```python
class DAOFactory:
    """Factory for creating DAO instances based on storage type."""

    _registry: ClassVar[dict[StorageType, type[Any]]] = {}

    @classmethod
    def register(cls, storage_type: StorageType, dao_class: type[Any]) -> None:
        """Register a DAO implementation for a storage type."""
        cls._registry[storage_type] = dao_class

    @classmethod
    def create(cls, config: StorageConfig, collection_name: str, **kwargs: Any) -> Any:
        """Create a DAO instance based on storage configuration."""
        dao_class = cls._registry.get(config.storage_type)
        if not dao_class:
            raise ValueError(f"No DAO registered for storage type: {config.storage_type.value}")
        return dao_class(config, collection_name, **kwargs)

# Auto-register on import
def register_all_daos() -> None:
    DAOFactory.register(StorageType.GRAPH, DgraphDAO)
    DAOFactory.register(StorageType.VECTOR, PgVectorDAO)
    DAOFactory.register(StorageType.RELATIONAL, PostgreSQLDAO)

register_all_daos()
```

**BAD CODE** (Current SPEC):
```python
def get_agent_cli(config: AgentConfig | None = None) -> AgentCLI:
    if provider == CLIProvider.GEMINI:
        return GeminiAgentCLI()
    return ClaudeAgentCLI()
```

**PROBLEM**:
- Hard-coded `if/else` doesn't scale
- Adding new provider requires editing factory code
- No plugin discovery
- No capability validation

**SOLUTION**:
```python
class ProviderFactory:
    """Factory for creating CLI provider instances."""

    _registry: ClassVar[dict[CLIProvider, type[Provider]]] = {}

    @classmethod
    def register(cls, provider_type: CLIProvider, provider_class: type[Provider]) -> None:
        """Register a provider implementation."""
        cls._registry[provider_type] = provider_class

    @classmethod
    def create(cls, config: AgentConfig) -> Provider:
        """Create provider instance with validation."""
        provider_class = cls._registry.get(config.provider)
        if not provider_class:
            raise ValueError(f"No provider registered for: {config.provider}")

        # Validate provider capabilities
        if config.enable_streaming and not provider_class.supports_streaming():
            raise ValueError(f"Provider {config.provider} doesn't support streaming")

        return provider_class(config)
```

---

### Pattern 2: Base DAO Pattern (from `base/backend/dataops/core/dao.py`)

**GOOD CODE** (BaseDAO):
```python
class BaseDAO[T: "StorageModel"](ABC):
    """Abstract base class for all DAOs with complete CRUD interface."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to storage backend"""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to storage backend"""

    @abstractmethod
    async def create(self, instance: T) -> str:
        """Create new record, return ID"""

    @abstractmethod
    async def find_by_id(self, item_id: str) -> T | None:
        """Find record by ID"""

    # ... 15+ standardized methods
```

**BAD CODE** (Current SPEC Provider ABC):
```python
class Provider(ABC):
    @abstractmethod
    def build_command(...) -> list[str]: ...

    @abstractmethod
    def execute_streaming(...) -> tuple[str, dict]: ...

    @abstractmethod
    def execute_blocking(...) -> tuple[str, dict]: ...
```

**PROBLEM**:
- Missing lifecycle methods (`connect`, `disconnect`, `health_check`)
- No resource management (context manager support)
- Missing capability queries (`supports_streaming`, `max_context_size`)
- No connection pooling hooks
- Missing async support

**SOLUTION**:
```python
class Provider(ABC):
    """Abstract provider with complete lifecycle management."""

    @abstractmethod
    async def connect(self) -> None:
        """Initialize provider connection/resources."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanup provider resources."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health and availability."""

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether provider supports streaming execution."""

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether provider supports tool use."""

    @abstractmethod
    def max_context_size(self) -> int:
        """Maximum context size in tokens."""

    @abstractmethod
    async def execute(
        self,
        instruction: str,
        config: AgentConfig,
        stdin: str | None = None,
        cwd: Path | None = None,
    ) -> ExecutionResult:
        """Execute with provider (streaming auto-detected from config)."""

    # Context manager support for resource cleanup
    async def __aenter__(self) -> Provider:
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.disconnect()
```

---

### Pattern 3: Facade Pattern (from `files/backend/mcp/filesys/tools/facade/`)

**GOOD CODE** (FilesysFacade):
```python
# files/backend/mcp/filesys/tools/facade/filesystem.py

ACTION_HANDLERS: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    "list": _handle_list,
    "create": _handle_create,
    "find": _handle_find,
    "read": _handle_read,
    "write": _handle_write,
    "delete": _handle_delete,
    "modify": _handle_modify,
    "replace": _handle_replace,
}

async def files_tool(root_dir: Path, action: Literal["list", "create", ...], **kwargs: Any) -> dict[str, Any]:
    """Unified facade for all filesystem operations."""
    handler = ACTION_HANDLERS.get(action)
    if not handler:
        return {"error": f"Unknown action: {action}"}
    return await handler(root_dir=root_dir, **kwargs)
```

**Structure**:
```
tools/
├── facade/                    # Unified entry points
│   ├── filesystem.py          # files_tool(action=...)
│   ├── git.py                 # git_tool(action=...)
│   └── python.py              # python_tool(action=...)
├── filesystem_tools.py        # Individual implementations
├── git_tools.py
└── python_tools.py
```

**BAD CODE** (Current SPEC - No Facade):
```
executors/
├── audit.py                   # Monolithic AuditEngine
├── tasks.py                   # Monolithic TaskExecutor
├── sync.py                    # Monolithic SyncExecutor
└── docs.py                    # Monolithic DocsExecutor
```

**PROBLEM**:
- No unified interface
- Each executor duplicates provider interaction logic
- Can't compose operations
- Hard to test individual pieces

**SOLUTION**:
```
backend/agents/
├── core/
│   └── facade.py              # Unified agent operations facade
├── operations/                # Individual operation implementations
│   ├── audit.py
│   ├── tasks.py
│   ├── sync.py
│   └── docs.py
└── executors/                 # High-level orchestrators
    ├── batch.py               # Batch execution engine
    └── workflow.py            # Multi-step workflow engine
```

With facade:
```python
async def agent_operation(
    provider: Provider,
    operation: Literal["audit", "task", "sync", "docs"],
    config: AgentConfig,
    **kwargs: Any,
) -> OperationResult:
    """Unified facade for all agent operations."""
    handler = OPERATION_HANDLERS.get(operation)
    return await handler(provider=provider, config=config, **kwargs)
```

---

### Pattern 4: Async/Await Throughout (from all `/base` modules)

**GOOD CODE** (All `/base` modules):
```python
class FileSubprocess:
    async def run(
        self,
        cmd: list[str],
        input_text: str | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Async subprocess execution with file-based I/O."""
        process = await asyncio.create_subprocess_exec(...)
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            raise
```

**BAD CODE** (Current SPEC - Sync Everywhere):
```python
class GeminiProvider(Provider):
    def execute_streaming(...) -> tuple[str, dict]:
        """Blocking streaming execution."""
        process = subprocess.Popen(...)
        while True:
            line = process.stdout.readline()  # BLOCKING
```

**PROBLEM**:
- Can't run multiple operations concurrently
- Blocks entire thread on I/O
- No cancellation support
- Can't integrate with async frameworks

**SOLUTION**:
```python
class GeminiProvider(Provider):
    async def execute(
        self,
        instruction: str,
        config: AgentConfig,
        stdin: str | None = None,
    ) -> ExecutionResult:
        """Async execution with proper resource management."""
        async with self._create_process(instruction, config, stdin) as process:
            if config.enable_streaming:
                return await self._execute_streaming(process, config)
            return await self._execute_blocking(process, config)

    async def _execute_streaming(self, process, config) -> ExecutionResult:
        """Async streaming with asyncio subprocess."""
        async for line in self._read_lines_async(process):
            # Process streaming JSON
            ...
```

---

### Pattern 5: Structured Error Handling (from `/base/backend/dataops/core/exceptions.py`)

**GOOD CODE** (Structured Exceptions):
```python
class StorageError(Exception):
    """Base exception for storage operations."""

    def __init__(self, message: str, storage_type: StorageType | None = None, **context: Any):
        super().__init__(message)
        self.storage_type = storage_type
        self.context = context

    def to_dict(self) -> dict[str, Any]:
        """Convert to structured dict for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "storage_type": self.storage_type.value if self.storage_type else None,
            **self.context,
        }
```

**BAD CODE** (Current SPEC - Simple Exceptions):
```python
class AgentError(Exception):
    """Base exception for all agent execution errors."""
    # Just inherits from Exception, no context
```

**SOLUTION**:
```python
class AgentError(Exception):
    """Base exception with structured context."""

    def __init__(
        self,
        message: str,
        provider: CLIProvider | None = None,
        session_id: str | None = None,
        **context: Any,
    ):
        super().__init__(message)
        self.provider = provider
        self.session_id = session_id
        self.context = context
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Structured error for logging/monitoring."""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "provider": self.provider.value if self.provider else None,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            **self.context,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.to_dict()})"
```

---

### Pattern 6: Protocol-Based Capabilities (Missing from SPEC)

**GOOD PATTERN** (from `/base/backend/llms/` - implied):
```python
from typing import Protocol

class StreamingCapable(Protocol):
    """Protocol for providers supporting streaming."""

    def supports_streaming(self) -> bool: ...
    async def execute_streaming(self, ...) -> AsyncIterator[StreamChunk]: ...

class ToolCapable(Protocol):
    """Protocol for providers supporting tools."""

    def supports_tools(self) -> bool: ...
    def list_available_tools(self) -> list[str]: ...
    def map_tool_name(self, canonical: str) -> str: ...

class VisionCapable(Protocol):
    """Protocol for providers supporting image inputs."""

    def supports_vision(self) -> bool: ...
    def max_image_size(self) -> int: ...
```

**USAGE**:
```python
def validate_provider_config(provider: Provider, config: AgentConfig) -> None:
    """Validate provider supports requested capabilities."""
    if config.enable_streaming:
        if not isinstance(provider, StreamingCapable):
            raise ValueError(f"Provider {provider} doesn't support streaming")

    if config.allowed_tools:
        if not isinstance(provider, ToolCapable):
            raise ValueError(f"Provider {provider} doesn't support tools")
```

---

## Revised Architecture

### Directory Structure (Following `/base` patterns)

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
│   └── models.py                    # Result models (ExecutionResult, etc.)
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
├── operations/                      # Individual operations (like tools/)
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

## Key Design Principles to Follow

### 1. **Single Responsibility**
Each module does ONE thing:
- `providers/claude/provider.py` - Claude provider implementation
- `providers/claude/streaming.py` - ONLY streaming logic
- `providers/claude/hooks.py` - ONLY hook file management

### 2. **Dependency Inversion**
High-level modules depend on abstractions:
```python
# Good - depends on ABC
from backend.agents.core.base import Provider

async def execute_operation(provider: Provider, ...) -> Result:
    ...

# Bad - depends on concrete implementation
from backend.agents.providers.claude import ClaudeProvider
```

### 3. **Open/Closed Principle**
Open for extension (new providers), closed for modification (factory doesn't change):
```python
# Add new provider by registering, not editing factory
ProviderFactory.register(CLIProvider.OPENAI, OpenAIProvider)
```

### 4. **Interface Segregation**
Multiple specific protocols instead of one fat interface:
```python
# Good - specific capabilities
class StreamingCapable(Protocol): ...
class ToolCapable(Protocol): ...

# Bad - everything in one ABC
class Provider(ABC):
    def supports_everything(self): ...
```

### 5. **Liskov Substitution**
Any `Provider` can be used anywhere a `Provider` is expected:
```python
async def run_with_any_provider(provider: Provider, config: AgentConfig):
    # Works with Claude, Gemini, or future providers
    result = await provider.execute(instruction="...", config=config)
```

---

## Critical Changes Required to SPEC

### Change 1: Provider Factory with Registry

**BEFORE**:
```python
def get_agent_cli(config: AgentConfig | None = None) -> AgentCLI:
    if provider == CLIProvider.GEMINI:
        return GeminiAgentCLI()
    return ClaudeAgentCLI()
```

**AFTER**:
```python
# backend/agents/providers/registry.py
class ProviderFactory:
    _registry: ClassVar[dict[CLIProvider, type[Provider]]] = {}

    @classmethod
    def register(cls, provider_type: CLIProvider, provider_class: type[Provider]) -> None:
        cls._registry[provider_type] = provider_class

    @classmethod
    def create(cls, config: AgentConfig) -> Provider:
        provider_class = cls._registry.get(config.provider)
        if not provider_class:
            raise ValueError(f"Unknown provider: {config.provider}")
        return provider_class(config)

def register_all_providers() -> None:
    ProviderFactory.register(CLIProvider.CLAUDE, ClaudeProvider)
    ProviderFactory.register(CLIProvider.GEMINI, GeminiProvider)

register_all_providers()
```

### Change 2: Async Provider Interface

**BEFORE**:
```python
class Provider(ABC):
    @abstractmethod
    def execute_streaming(...) -> tuple[str, dict]: ...
```

**AFTER**:
```python
class Provider(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def execute(
        self,
        instruction: str,
        config: AgentConfig,
        stdin: str | None = None,
        cwd: Path | None = None,
    ) -> ExecutionResult: ...

    @abstractmethod
    def supports_streaming(self) -> bool: ...

    # Context manager support
    async def __aenter__(self) -> Provider:
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.disconnect()
```

### Change 3: Operations Facade

**BEFORE**:
```python
# Monolithic executors
class AuditEngine:
    def audit_file(...): ...
    def audit_directory(...): ...

class TaskExecutor:
    def execute_task(...): ...
```

**AFTER**:
```python
# backend/agents/operations/facade.py
async def agent_operation(
    provider: Provider,
    operation: Literal["audit", "task", "sync", "docs"],
    config: AgentConfig,
    **kwargs: Any,
) -> OperationResult:
    """Unified operation facade."""
    handler = OPERATION_HANDLERS[operation]
    return await handler(provider=provider, config=config, **kwargs)

# Usage
async with ProviderFactory.create(config) as provider:
    result = await agent_operation(
        provider=provider,
        operation="audit",
        config=config,
        file_path="example.py",
    )
```

### Change 4: Structured Errors

**BEFORE**:
```python
class AgentError(Exception):
    """Base exception for all agent execution errors."""
```

**AFTER**:
```python
class AgentError(Exception):
    def __init__(
        self,
        message: str,
        provider: CLIProvider | None = None,
        session_id: str | None = None,
        **context: Any,
    ):
        super().__init__(message)
        self.provider = provider
        self.session_id = session_id
        self.context = context

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "provider": self.provider.value if self.provider else None,
            "session_id": self.session_id,
            **self.context,
        }
```

---

## Testing Strategy (Following `/base` patterns)

### Unit Tests Structure
```
tests/unit/backend/agents/
├── core/
│   ├── test_factory.py              # Factory pattern tests
│   ├── test_config.py
│   ├── test_protocols.py            # Protocol validation tests
│   └── test_exceptions.py           # Structured error tests
├── providers/
│   ├── claude/
│   │   ├── test_provider.py
│   │   ├── test_streaming.py
│   │   └── test_hooks.py
│   └── gemini/
│       ├── test_provider.py
│       ├── test_streaming.py        # CRITICAL - first-output markers
│       ├── test_parser.py           # JSON parsing
│       └── test_tools.py            # Tool mapping
├── operations/
│   ├── test_facade.py               # Facade pattern tests
│   ├── test_audit.py
│   └── test_tasks.py
└── hooks/
    ├── test_registry.py             # Hook registry tests
    └── validators/
        └── test_*.py
```

---

## Migration Strategy

### Phase 1: Core Infrastructure
1. Create `core/` with proper patterns (factory, protocols, async base)
2. Extract `core/exceptions.py` with structured errors
3. Build `core/factory.py` with registry
4. Define `core/protocols.py` for capabilities

### Phase 2: Provider Refactoring
1. Create `providers/claude/` package
2. Split monolithic ClaudeAgentCLI into:
   - `provider.py` - main implementation
   - `streaming.py` - streaming logic
   - `hooks.py` - hook file management
   - `tools.py` - tool restrictions
3. Implement `providers/gemini/` with same structure
4. Add async/await throughout
5. Implement provider protocols

### Phase 3: Operations Layer
1. Create `operations/` with individual operation implementations
2. Build `operations/facade.py` for unified interface
3. Refactor executors to use facade

### Phase 4: Hook Registry
1. Create `hooks/registry.py` with validator factory
2. Split validators into separate modules under `hooks/validators/`
3. Add protocol-based validator capabilities

### Phase 5: Integration
1. Wire up CLI entry point to use facade
2. Update all 11 import sites
3. Add comprehensive tests
4. Validate with real workloads

---

## Success Metrics

- [ ] **Zero `if provider == ...` checks** - All routing through factory
- [ ] **100% async operations** - No blocking I/O in hot path
- [ ] **Protocol compliance** - All providers implement required protocols
- [ ] **Composable operations** - Can chain operations via facade
- [ ] **Pluggable providers** - Add new provider without editing factory
- [ ] **Context manager support** - Proper resource cleanup with `async with`
- [ ] **Structured errors** - All exceptions have `to_dict()` for logging
- [ ] **<300 lines per module** - No monolithic files
- [ ] **90%+ test coverage** - All critical paths tested
- [ ] **Zero regression** - Existing Claude functionality preserved

---

**END OF DESIGN AUDIT**
