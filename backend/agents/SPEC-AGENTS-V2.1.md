# AMI Agents Service Specification v2.1

**Status:** Proposal - BPMN-Native Architecture (Revised)
**Replaces:** SPEC-AGENTS.md v1.0, SPEC-AGENTS-V2.md v2.0
**Author:** AMI Orchestrator Docs Team
**Date:** 2025-11-02
**Changes from v2.0:** Corrected codebase underutilization, removed duplicate models, added base infrastructure integration

---

## Executive Summary

This specification proposes a **BPMN-native architecture** built on **proven Base module infrastructure** and the **ami-agent CLI** execution engine.

### Key Changes from v2.0

**Corrections:**
1. **Use existing base BPMN models** - Don't duplicate `Process`, `ProcessInstance`, `Task`
2. **Leverage SecuredModelMixin** - Multi-tenancy, ACL, audit trails already built-in
3. **Follow FastMCP patterns** - Use `FastMCPServerBase` from base module
4. **Use base path utilities** - `setup_imports()`, `find_module_root()`
5. **Extend existing config** - Add to `scripts/config/automation.yaml`
6. **Reference ChatGoogleCodeAssist** - Google provider already integrated
7. **Show complete worker pool usage** - Hibernation, health checks, metrics
8. **Use UnifiedCRUD** - Standard persistence pattern

### Core Architecture

1. **ami-agent CLI** as agent execution engine (proven, internal)
2. **Base BPMN models** for process definitions (`base/backend/dataops/models/bpmn.py`)
3. **BPMN Process Engine** for graph traversal and task dispatch
4. **Base worker pools** for scalable async execution
5. **FastMCP server** following base module patterns
6. **LangChain as optional integration** for advanced use cases

---

## 1. Mission & Scope

- Deliver BPMN-native agent orchestration under `backend/agents/`
- **Reuse base infrastructure** (BPMN models, worker pools, FastMCP, UnifiedCRUD)
- Transform Python workflows (`tasks.py`, `docs.py`, `audit.py`) into BPMN process definitions
- Enable visual process modeling, versioning, and governance
- Provide LangChain integration as optional enhancement

---

## 2. Design Principles

**Base-First Architecture**
- **Use existing BPMN models** from `base/backend/dataops/models/bpmn.py`
  - `Process`, `ProcessInstance`, `Task`, `Gateway`, `Event`, `SequenceFlow`
- **Inherit security** from `SecuredModelMixin` (multi-tenancy, ACL, audit trails)
- **Use UnifiedCRUD** for all persistence operations
- **Follow FastMCP patterns** from `base/backend/mcp/fastmcp_server_base.py`
- **Integrate base worker pools** for async task execution
- **Use base path utilities** (`base/scripts/env/paths.py`)
- **Extend automation config** (`scripts/config/automation.yaml`)
- **Standardize on loguru** for structured logging

**BPMN as Process Language**
- Workflows = BPMN 2.0 process graphs stored in DataOps
- Tasks → ami-agent CLI executions
- Gateways → branching logic
- Events → process lifecycle triggers

**Separation of Concerns**
- **Execution:** ami-agent CLI (proven)
- **Orchestration:** BPMN engine (scalable, versioned)
- **Integration:** Optional LangChain layer

**Security & Compliance**
- All models inherit `SecuredModelMixin`
  - `owner_id`, `acl`, `created_by`, `modified_by`, `accessed_by`
  - `classification` (INTERNAL/PUBLIC/CONFIDENTIAL/RESTRICTED)
  - `tenant_isolation_level` (shared/dedicated/isolated)
  - `check_permission()` for RBAC
- Process execution audit trails via DataOps
- Agent session logs via ami-agent hooks

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│        FastMCP Server (AgentsMCPServer)                      │
│        Extends: base.backend.mcp.fastmcp_server_base         │
│        Tools: agents_execute_process, agents_get_instance    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              BPMN Process Engine                             │
│  - Load Process from UnifiedCRUD                             │
│  - Manage ProcessInstance state                              │
│  - Dispatch Tasks to worker pools + ami-agent                │
│  - Evaluate Gateways (parallel/exclusive/inclusive)          │
│  - Persist state via UnifiedCRUD                             │
└────────────┬───────────────────────┬────────────────────────┘
             │                       │
┌────────────▼────────┐  ┌──────────▼─────────────────────────┐
│  Base Worker Pools  │  │       ami-agent CLI                 │
│  UVProcessPool      │  │  - AgentConfig presets              │
│  WorkerPoolManager  │  │  - run_print / run_interactive      │
│  Task queueing      │  │  - Hooks validation                 │
│  Hibernation        │  │  - Streaming execution              │
└────────────┬────────┘  │  - Session management               │
             │            └──────────┬─────────────────────────┘
             │                       │
┌────────────▼───────────────────────▼─────────────────────────┐
│           DataOps (UnifiedCRUD + StorageModel)                │
│  - Process, ProcessInstance, Task (base BPMN models)          │
│  - AgentSession (new: links Task → ami-agent session_id)      │
│  - Graph, Document, Timeseries backends                       │
│  - SecuredModelMixin (multi-tenancy, ACL, audit)              │
└───────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│           Optional: LangChain Integration Layer              │
│  - Use base.backend.llms.providers.ChatGoogleCodeAssist      │
│  - Supervisor/worker graphs (if needed)                      │
│  - Advanced RAG (if needed)                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Directory Structure

```
backend/agents/
├── __init__.py
├── models/
│   └── agent_session.py        # AgentSession model (only new model needed)
├── processes/                   # BPMN process definitions (JSON)
│   ├── task_execution.bpmn.json
│   ├── docs_maintenance.bpmn.json
│   ├── code_audit.bpmn.json
│   └── git_sync.bpmn.json
├── prompts/                     # Agent instruction files
│   ├── task_worker.txt
│   ├── task_moderator.txt
│   ├── docs_worker.txt
│   ├── audit.txt
│   └── consolidate.txt
├── bpmn_engine.py               # BPMN process execution engine
├── mcp_server.py                # FastMCP server (extends FastMCPServerBase)
├── integrations/
│   └── langchain/               # Optional LangChain integration
│       ├── __init__.py
│       └── graph_executor.py
└── scripts/
    └── run_agents_fastmcp.py    # Server startup script
```

---

## 5. Data Model - Use Base BPMN Models

### Existing Models (DO NOT DUPLICATE)

**From `base/backend/dataops/models/bpmn.py`:**

| Model | Purpose | Key Fields | Storage |
|-------|---------|-----------|---------|
| `Process` | BPMN process definition | `name`, `version`, `flow_nodes`, `sequence_flows`, `is_latest` | graph, document, inmem |
| `ProcessInstance` | Runtime process execution | `process_id`, `state`, `tokens`, `variables`, `active_tasks` | graph, timeseries, inmem |
| `Task` | BPMN task with execution state | `task_type`, `implementation`, `state`, `retry_count`, `timeout_seconds`, `started_at`, `completed_at` | graph, document |
| `Gateway` | BPMN gateway | `gateway_type` (exclusive, parallel, inclusive) | graph, document |
| `Event` | BPMN event | `event_type` (start, end, intermediate, boundary), `event_definition` | graph, document |
| `SequenceFlow` | Flow connector | `source_ref`, `target_ref`, `condition_expression`, `tokens_passed` | graph, inmem |
| `ProcessMetrics` | Execution metrics | `instances_started`, `instances_completed`, `avg_duration_ms` | timeseries |

**All models inherit `SecuredModelMixin`:**
- `owner_id`, `acl` (list[ACLEntry])
- `created_by`, `modified_by`, `accessed_by`
- `classification` (DataClassification)
- `tenant_isolation_level`
- `check_permission(context, permission)` method

### New Model (Only Addition Needed)

#### AgentSession

**Location:** `backend/agents/models/agent_session.py`

```python
from datetime import datetime
from pydantic import Field
from base.backend.dataops.models.base_model import StorageModel
from base.backend.dataops.models.storage_config import StorageConfig
from base.backend.dataops.core.storage_types import StorageType

class AgentSession(StorageModel):
    """ami-agent CLI execution metadata linked to BPMN Task"""

    session_id: str  # Claude Code session ID
    task_uid: str | None = None  # Link to Task.uid

    # Configuration
    agent_config_preset: str  # worker, moderator, etc.
    enable_hooks: bool = True
    enable_streaming: bool = True
    timeout: int | None = None

    # Execution
    transcript_path: str | None = None  # Path to .jsonl transcript
    status: str = "running"  # running, completed, failed, timeout

    # Metrics
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: datetime | None = None
    duration_ms: int | None = None
    token_usage: dict[str, int] = Field(default_factory=dict)  # input, output, total
    cost_usd: float | None = None

    class Meta:
        storage_configs = {
            "document": StorageConfig(storage_type=StorageType.DOCUMENT),
            "timeseries": StorageConfig(storage_type=StorageType.TIMESERIES),
        }
        path = "agent_sessions"
        indexes = [
            {"field": "session_id", "type": "hash"},
            {"field": "task_uid", "type": "hash"},
            {"field": "status", "type": "hash"},
        ]
```

**Usage:**
```python
from base.backend.dataops.core.unified_crud import UnifiedCRUD

crud = UnifiedCRUD()

# Create agent session linked to BPMN task
session = AgentSession(
    session_id=uuid7(),
    task_uid=task.uid,
    agent_config_preset="task_worker",
)
await crud.create(session)

# Update after execution
session.status = "completed"
session.ended_at = datetime.now()
session.duration_ms = 5420
session.token_usage = {"input": 1200, "output": 800, "total": 2000}
session.cost_usd = 0.015
await crud.update(session)
```

---

## 6. BPMN → ami-agent Mapping

| BPMN Task Type | ami-agent Mode | AgentConfig Preset | Use Case |
|----------------|----------------|-------------------|----------|
| `TaskType.SERVICE` | `--print` | `task_worker` | Execute agent with full tools, timeout=None, streaming |
| `TaskType.SCRIPT` | `--print` (Bash tool) | `worker` | Run shell scripts via agent |
| `TaskType.USER` | `--interactive` | `interactive` | Human-in-loop approval/input |
| `TaskType.BUSINESS_RULE` | `--print` | `task_moderator`, `completion_moderator` | Validate outputs, check completion markers |
| `TaskType.SEND` | `--print` | `worker` | Send notifications |
| `TaskType.RECEIVE` | Event-driven | N/A | Wait for external signal |
| `TaskType.CALL_ACTIVITY` | Subprocess | Recursive process execution |

---

## 7. BPMN Process Engine Implementation

### Setup Base Infrastructure

```python
# backend/agents/bpmn_engine.py

import sys
from pathlib import Path

# Use base path utilities
from base.scripts.env.paths import setup_imports
ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from base.backend.dataops.core.unified_crud import UnifiedCRUD
from base.backend.dataops.models.bpmn import (
    Process, ProcessInstance, Task, Gateway, Event,
    SequenceFlow, TaskType, TaskStatus, GatewayType
)
from base.backend.workers.manager import WorkerPoolManager
from base.backend.workers.types import PoolConfig, PoolType
from scripts.automation.agent_cli import AgentConfigPresets, get_agent_cli
from loguru import logger

class BPMNProcessEngine:
    """Execute BPMN processes using base worker pools and ami-agent CLI"""

    def __init__(self):
        self.crud = UnifiedCRUD()
        self.cli = get_agent_cli()
        self.pool_manager = WorkerPoolManager()

        # Configure worker pool
        self.pool_config = PoolConfig(
            name="bpmn_workers",
            pool_type=PoolType.UV_PROCESS,
            min_workers=2,
            max_workers=8,
            enable_hibernation=True,
            health_check_interval=30,
        )

    async def initialize(self):
        """Initialize worker pool"""
        await self.pool_manager.create_pool(self.pool_config)
        logger.info("bpmn_engine_initialized", pool=self.pool_config.name)

    async def execute_process(
        self,
        process_uid: str,
        context: dict[str, Any],
        tenant_id: str,
    ) -> ProcessInstance:
        """Execute a BPMN process definition.

        Args:
            process_uid: Process UID from DataOps
            context: Initial process variables
            tenant_id: Tenant for multi-tenancy

        Returns:
            ProcessInstance with execution state
        """
        # Load Process from DataOps using UnifiedCRUD
        process = await self.crud.read(Process, process_uid)
        logger.info("process_loaded", process_name=process.name, version=process.version)

        # Create ProcessInstance using base model
        instance = ProcessInstance(
            process_id=process.uid,
            process_version=process.version,
            state="active",
            variables=context,
            start_time=datetime.now(),
        )

        # Persist using UnifiedCRUD
        instance_uid = await self.crud.create(instance)
        logger.info("process_instance_created", instance_uid=instance_uid)

        # Find start event
        start_event = await self._find_start_event(process)

        # Execute process graph
        await self._execute_from_node(instance, start_event)

        # Update instance
        instance.state = "completed"
        instance.end_time = datetime.now()
        instance.duration_ms = int(
            (instance.end_time - instance.start_time).total_seconds() * 1000
        )
        await self.crud.update(instance)

        return instance

    async def _execute_task(
        self,
        instance: ProcessInstance,
        task: Task,
    ) -> dict[str, Any]:
        """Execute BPMN task via ami-agent CLI"""

        task.state = TaskStatus.ACTIVE
        task.started_at = datetime.now()
        await self.crud.update(task)

        try:
            if task.task_type == TaskType.SERVICE:
                result = await self._execute_service_task(instance, task)
            elif task.task_type == TaskType.BUSINESS_RULE:
                result = await self._execute_business_rule_task(instance, task)
            else:
                raise ValueError(f"Unsupported task type: {task.task_type}")

            # Update task
            task.state = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.duration_ms = int(
                (task.completed_at - task.started_at).total_seconds() * 1000
            )
            await self.crud.update(task)

            # Update process variables
            instance.variables.update(result)
            await self.crud.update(instance)

            return result

        except Exception as e:
            task.state = TaskStatus.FAILED
            await self.crud.update(task)
            raise

    async def _execute_service_task(
        self,
        instance: ProcessInstance,
        task: Task,
    ) -> dict[str, Any]:
        """Execute service task via ami-agent in worker pool"""

        # Get agent preset from task attributes
        preset_name = task.attributes.get("agent_preset", "task_worker")
        agent_preset = getattr(AgentConfigPresets, preset_name)

        # Create agent session
        session_id = uuid7()
        agent_config = agent_preset(session_id)
        agent_config.enable_streaming = True  # Always enable streaming

        # Create AgentSession record linked to Task
        from backend.agents.models.agent_session import AgentSession
        session = AgentSession(
            session_id=session_id,
            task_uid=task.uid,
            agent_config_preset=preset_name,
            enable_hooks=agent_config.enable_hooks,
            enable_streaming=agent_config.enable_streaming,
            timeout=agent_config.timeout,
        )
        await self.crud.create(session)

        # Execute via worker pool
        pool = await self.pool_manager.get_pool(self.pool_config.name)

        result = await pool.submit_task(
            task_id=task.uid,
            callable=self.cli.run_print,
            instruction_file=Path(task.implementation),
            stdin=json.dumps(instance.variables),
            agent_config=agent_config,
        )

        output, metadata = result

        # Update AgentSession
        session.status = "completed"
        session.ended_at = datetime.now()
        session.duration_ms = int(
            (session.ended_at - session.started_at).total_seconds() * 1000
        )
        if metadata:
            session.token_usage = metadata.get("usage", {})
            session.cost_usd = metadata.get("cost_usd")
        await self.crud.update(session)

        return {"output": output, "metadata": metadata}
```

---

## 8. MCP Server - Follow Base Patterns

**Location:** `backend/agents/mcp_server.py`

```python
from base.backend.mcp.fastmcp_server_base import FastMCPServerBase
from backend.agents.bpmn_engine import BPMNProcessEngine
from loguru import logger

class AgentsMCPServer(FastMCPServerBase):
    """MCP server for BPMN agent orchestration

    Follows FastMCP patterns from base/backend/mcp/fastmcp_server_base.py
    """

    def __init__(self):
        super().__init__(name="agents", version="1.0.0")
        self.engine = BPMNProcessEngine()

    def _register_tools(self):
        """Register MCP tools following base patterns"""

        @self.mcp.tool()
        async def agents_execute_process(
            process_uid: str,
            context: dict,
            tenant_id: str,
        ) -> dict:
            """Execute a BPMN process

            Args:
                process_uid: Process UID from DataOps
                context: Initial process variables
                tenant_id: Tenant identifier

            Returns:
                Process execution result with instance_uid and status
            """
            await self.engine.initialize()

            instance = await self.engine.execute_process(
                process_uid=process_uid,
                context=context,
                tenant_id=tenant_id,
            )

            return {
                "instance_uid": instance.uid,
                "status": instance.state,
                "started_at": instance.start_time.isoformat(),
                "variables": instance.variables,
            }

        @self.mcp.tool()
        async def agents_get_instance(instance_uid: str) -> dict:
            """Get process instance state

            Args:
                instance_uid: ProcessInstance UID

            Returns:
                Instance state including status and variables
            """
            from base.backend.dataops.core.unified_crud import UnifiedCRUD
            from base.backend.dataops.models.bpmn import ProcessInstance

            crud = UnifiedCRUD()
            instance = await crud.read(ProcessInstance, instance_uid)

            return {
                "instance_uid": instance.uid,
                "process_id": instance.process_id,
                "status": instance.state,
                "variables": instance.variables,
                "started_at": instance.start_time.isoformat(),
                "ended_at": instance.end_time.isoformat() if instance.end_time else None,
            }
```

**Startup script:** `backend/agents/scripts/run_agents_fastmcp.py`

```python
#!/usr/bin/env python3
"""Run Agents FastMCP server - follows base pattern"""

import sys
from pathlib import Path
from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from backend.agents.mcp_server import AgentsMCPServer

if __name__ == "__main__":
    server = AgentsMCPServer()

    # Default to stdio transport (follows base/scripts/run_dataops_fastmcp.py pattern)
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    server.run(transport=transport)
```

---

## 9. Configuration Management - Extend Existing

**Add to `scripts/config/automation.yaml`:**

```yaml
# Existing: tasks, docs, audit, sync sections...

# New: BPMN agent orchestration
agents:
  # Process storage
  process_definitions_path: "backend/agents/processes"
  prompts_path: "backend/agents/prompts"

  # Worker pool
  worker_pool:
    name: "bpmn_workers"
    min_workers: 2
    max_workers: 8
    enable_hibernation: true
    health_check_interval: 30

  # Default agent config
  default_preset: "task_worker"
  enable_streaming: true  # Always enable for monitoring

  # MCP server
  mcp:
    transport: "stdio"
    port: 8080  # For HTTP transport
```

**Usage:**

```python
from scripts.automation.config import get_config

config = get_config()

# Access agents config
processes_path = config.get("agents.process_definitions_path")
worker_config = config.get("agents.worker_pool")
```

---

## 10. LangChain Integration (Optional) - Use Base Provider

**Reference existing provider:** `base/backend/llms/providers/google_code_assist.py`

```python
# backend/agents/integrations/langchain/provider_router.py

from base.backend.llms.providers.google_code_assist import ChatGoogleCodeAssist

class MultiProviderRouter:
    """Multi-provider routing using base ChatGoogleCodeAssist"""

    def __init__(self, user_email: str):
        # Use existing base provider (OAuth + API key fallback)
        self.google_code_assist = ChatGoogleCodeAssist(
            user_email=user_email,
            model="gemini-1.5-pro",
            use_oauth=True,  # Uses base/backend/opsec/auth/auth_service.py
        )

    async def invoke(self, messages: list, **kwargs) -> str:
        """Invoke LLM via base provider"""
        return await self.google_code_assist.ainvoke(messages, **kwargs)
```

**No need to recreate:**
- OAuth authentication (already in `base/backend/opsec/auth/`)
- Provider abstraction (already in `ChatGoogleCodeAssist`)
- Token refresh (already handled)

---

## 11. Migration Strategy

### Phase 1: Foundation (Week 1-2)

1. **Create AgentSession model**
   - `backend/agents/models/agent_session.py`
   - Register with DataOps model registry

2. **Implement BPMNProcessEngine**
   - Use UnifiedCRUD for all persistence
   - Integrate base worker pools
   - Link Tasks to AgentSessions

3. **Create example process**
   - Convert `tasks.py` → `task_execution.bpmn.json`
   - Use existing `Process`, `Task`, `Gateway` models

4. **Integration tests**
   - Load process via UnifiedCRUD
   - Execute with ami-agent
   - Verify AgentSession tracking

### Phase 2: MCP Server (Week 3)

1. **Implement AgentsMCPServer**
   - Extend `FastMCPServerBase`
   - Follow `DataOpsMCPServer` pattern
   - Register tools

2. **Create startup script**
   - Follow `run_dataops_fastmcp.py` pattern
   - Support stdio/sse/http transports

3. **Add to config**
   - Extend `automation.yaml` with `agents:` section

### Phase 3: Workflow Migration (Week 4-5)

1. **Convert workflows**
   - `docs.py` → `docs_maintenance.bpmn.json`
   - `audit.py` → `code_audit.bpmn.json`
   - `sync.py` → `git_sync.bpmn.json`

2. **Side-by-side testing**
   - Run old Python vs new BPMN
   - Compare outputs
   - Verify metrics

### Phase 4: LangChain (Optional, Week 6)

1. **Create integration module**
   - Reference `ChatGoogleCodeAssist`
   - Don't recreate provider
   - Add only if advanced features needed

---

## 12. Benefits Summary

| Aspect | Before (Python) | After (BPMN + Base) |
|--------|-----------------|---------------------|
| **Models** | Duplicated in spec | Reuse base BPMN models |
| **Security** | Not mentioned | SecuredModelMixin (ACL, audit, multi-tenancy) |
| **Persistence** | Custom code | UnifiedCRUD standard pattern |
| **MCP Server** | Custom implementation | FastMCPServerBase pattern |
| **Worker Pools** | Thread pools | Base UVProcessPool (hibernation, health checks) |
| **Config** | New env vars | Extend automation.yaml |
| **LLM Provider** | New abstraction | ChatGoogleCodeAssist (already OAuth-enabled) |
| **Path Utilities** | Hardcoded | setup_imports(), find_module_root() |
| **Logging** | Custom | loguru (base standard) |

---

## Appendix: Example Process Definition

**File:** `backend/agents/processes/task_execution.bpmn.json`

```json
{
  "process_uid": "proc_task_exec_v1",
  "name": "Task Execution with Validation",
  "version": "1.0.0",
  "process_type": "private",
  "is_executable": true,

  "flow_nodes": [
    {
      "uid": "start_event",
      "type": "Event",
      "event_type": "start",
      "outgoing_flows": ["flow_1"]
    },
    {
      "uid": "task_worker",
      "type": "Task",
      "task_type": "service",
      "name": "Execute Task Worker",
      "implementation": "backend/agents/prompts/task_worker.txt",
      "attributes": {
        "agent_preset": "task_worker"
      },
      "incoming_flows": ["flow_1"],
      "outgoing_flows": ["flow_2"]
    },
    {
      "uid": "gateway_check",
      "type": "Gateway",
      "gateway_type": "exclusive",
      "name": "Check Completion",
      "incoming_flows": ["flow_2"],
      "outgoing_flows": ["flow_pass", "flow_feedback"]
    },
    {
      "uid": "task_moderator",
      "type": "Task",
      "task_type": "businessRule",
      "name": "Validate Output",
      "implementation": "backend/agents/prompts/task_moderator.txt",
      "attributes": {
        "agent_preset": "task_moderator"
      },
      "incoming_flows": ["flow_pass"],
      "outgoing_flows": ["flow_end"]
    },
    {
      "uid": "end_event",
      "type": "Event",
      "event_type": "end",
      "incoming_flows": ["flow_end"]
    }
  ],

  "sequence_flows": [
    {
      "uid": "flow_1",
      "source_ref": "start_event",
      "target_ref": "task_worker"
    },
    {
      "uid": "flow_2",
      "source_ref": "task_worker",
      "target_ref": "gateway_check"
    },
    {
      "uid": "flow_pass",
      "source_ref": "gateway_check",
      "target_ref": "task_moderator",
      "condition_expression": "'WORK DONE' in variables['worker_output']"
    },
    {
      "uid": "flow_end",
      "source_ref": "task_moderator",
      "target_ref": "end_event"
    }
  ]
}
```

---

**End of Specification v2.1**

Status: **Proposal - Revised for Base Integration**
Approvers: Architecture Team, Base Module Maintainers
Next Steps: Prototype Phase 1 (AgentSession + BPMNProcessEngine)
