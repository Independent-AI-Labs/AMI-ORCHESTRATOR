# AMI Agents Service - Final Unified Specification

**Status:** Approved Architecture
**Date:** 2025-11-07
**Supersedes:** SPEC-AGENTS.md, SPEC-AGENTS-V2.md, SPEC-AGENTS-V2.1.md

---

## Executive Summary

This specification defines a **BPMN-native agent orchestration service** in `/backend/agents` that consolidates and refactors existing `/scripts/automation` workflows into a production-grade BPMN process engine.

### Core Requirements

1. **REFACTOR WITHOUT DELETION** - `/scripts/automation` remains untouched as the proven execution engine (`ami-agent` CLI)
2. **BPMN-NATIVE WORKFLOWS** - All workflows (tasks, hooks, audit, docs, sync) expressed as BPMN process definitions
3. **BASE MODULE INTEGRATION** - Leverage existing `base/backend/dataops/models/bpmn.py` and `base/backend/workers`
4. **NO MCP (FUTURE WORK)** - Focus on core engine, defer MCP integration

### Key Architecture Decisions

**✅ KEEP**: `scripts/automation/agent_cli.py` - Battle-tested Claude CLI wrapper with streaming, hooks, privilege dropping
**✅ KEEP**: Hook validators - Malicious behavior, code quality, bash guard, response scanner, todo validator
**✅ REUSE**: Base BPMN models - `Process`, `ProcessInstance`, `Task`, `Gateway`, `Event`, `SequenceFlow`
**✅ REUSE**: Base worker pools - `WorkerPoolManager`, `UVProcessPool` for async execution
**✅ BUILD**: BPMN engine - Graph traversal, token flow, task dispatch to `ami-agent`
**✅ BUILD**: Process definitions - Convert Python workflows to BPMN JSON graphs

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                   backend/agents/                             │
│                   BPMN Process Engine                         │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  BPMNProcessEngine                                   │     │
│  │  - Load Process (via UnifiedCRUD)                    │     │
│  │  - Execute graph traversal (token flow)              │     │
│  │  - Dispatch Tasks to worker pools                    │     │
│  │  - Evaluate Gateways (exclusive/parallel)            │     │
│  │  - Handle Events (start/end/error)                   │     │
│  │  - Persist state (ProcessInstance)                   │     │
│  └────────┬────────────────────────────┬─────────────────┘     │
│           │                            │                       │
│  ┌────────▼─────────┐       ┌─────────▼────────────────┐     │
│  │ Base Worker Pool │       │ scripts/automation/       │     │
│  │ UVProcessPool    │       │ agent_cli.py              │     │
│  │ - Async tasks    │       │ (ami-agent CLI)           │     │
│  │ - Hibernation    │       │ - ClaudeAgentCLI          │     │
│  │ - Health checks  │       │ - run_print()             │     │
│  └──────────────────┘       │ - Streaming execution     │     │
│                             │ - Hook file management    │     │
│                             │ - Privilege dropping      │     │
│                             └───────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
                               ▲
                               │ Uses
                               │
┌──────────────────────────────┴───────────────────────────────┐
│              base/backend/dataops/models/bpmn.py              │
│  - Process, ProcessInstance, Task, Gateway, Event             │
│  - SequenceFlow, Pool, Lane, DataObject                       │
│  - All models inherit SecuredModelMixin (multi-tenancy, ACL)  │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
backend/agents/
├── __init__.py                    # Public API exports
├── README.md                      # Framework documentation
│
├── models/
│   ├── __init__.py
│   └── agent_session.py           # ONLY new model needed
│                                   # Links BPMN Task → ami-agent session_id
│
├── processes/                      # BPMN process definitions (JSON)
│   ├── task_execution.bpmn.json   # Worker + moderator pattern
│   ├── hook_validation.bpmn.json  # Hook validator workflows
│   ├── code_audit.bpmn.json       # Parallel file audits
│   ├── docs_maintenance.bpmn.json # Docs update/archive/delete
│   └── git_sync.bpmn.json         # Git commit/push workflow
│
├── prompts/                        # Agent instruction files
│   ├── task_worker.txt            # Task execution worker
│   ├── task_moderator.txt         # Task completion validator
│   ├── audit_file.txt             # File audit instruction
│   ├── consolidate_patterns.txt   # Pattern extraction
│   ├── docs_worker.txt            # Docs maintenance
│   └── sync_worker.txt            # Git operations
│
├── engine.py                       # BPMNProcessEngine implementation
├── executor.py                     # Task → ami-agent executor
├── gateway_evaluator.py            # Gateway expression evaluation
├── token_manager.py                # Token flow management
│
└── utils/
    ├── __init__.py
    ├── process_loader.py           # Load/validate BPMN JSON
    └── expression_eval.py          # Safe expression evaluation for conditions
```

**NOT CREATED** (already exists, reuse as-is):
- `scripts/automation/agent_cli.py` - ClaudeAgentCLI
- `scripts/automation/hooks.py` - All hook validators
- `scripts/automation/config.py`, `logger.py`, `validators.py`
- `base/backend/dataops/models/bpmn.py` - All BPMN models
- `base/backend/workers/` - Worker pools

---

## 3. Data Model

### 3.1 Reuse Base BPMN Models

**FROM `base/backend/dataops/models/bpmn.py`** (DO NOT DUPLICATE):

| Model | Purpose | Storage |
|-------|---------|---------|
| `Process` | BPMN process definition with version control | graph, document, inmem |
| `ProcessInstance` | Runtime execution state, tokens, variables | graph, timeseries, inmem |
| `Task` | BPMN task with retry, timeout, dependencies | graph, document |
| `Gateway` | Exclusive/parallel/inclusive branching | graph, document |
| `Event` | Start/end/error/timer events | graph, document |
| `SequenceFlow` | Connectors with conditions | graph, inmem |

**All inherit `SecuredModelMixin`:**
- `owner_id`, `acl` (RBAC)
- `created_by`, `modified_by`, `accessed_by`
- `classification` (INTERNAL/PUBLIC/CONFIDENTIAL)
- `tenant_isolation_level`

### 3.2 New Model: AgentSession

**Location:** `backend/agents/models/agent_session.py`

Links BPMN Task execution to ami-agent CLI session for audit trail.

```python
from datetime import datetime
from pydantic import Field
from base.backend.dataops.models.base_model import StorageModel
from base.backend.dataops.models.storage_config import StorageConfig
from base.backend.dataops.core.storage_types import StorageType


class AgentSession(StorageModel):
    """Links BPMN Task → ami-agent CLI execution.

    Provides audit trail for agent operations within BPMN workflows.
    """

    # Core identifiers
    session_id: str  # Claude Code session ID (UUID7)
    task_uid: str | None = None  # Link to Task.uid in BPMN graph
    process_instance_uid: str | None = None  # Link to ProcessInstance

    # Configuration
    agent_preset: str  # "task_worker", "audit", "completion_moderator", etc.
    model: str = "claude-sonnet-4-5"
    allowed_tools: list[str] | None = None  # None = all tools
    enable_hooks: bool = True
    enable_streaming: bool = True
    timeout: int | None = None

    # Execution
    instruction_file: str | None = None  # Path to instruction .txt file
    stdin_data: str | None = None  # Input data passed to agent
    cwd: str | None = None  # Working directory

    # Output
    stdout: str | None = None  # Agent output
    stderr: str | None = None  # Error output
    exit_code: int | None = None

    # State
    status: str = "created"  # created, running, completed, failed, timeout

    # Timing
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
    first_output_ms: int | None = None  # First output latency (hang detection)

    # Metrics
    token_usage: dict[str, int] = Field(default_factory=dict)  # input, output, total
    cost_usd: float | None = None

    # Audit
    transcript_path: str | None = None  # Path to .jsonl transcript
    audit_log_path: str | None = None  # Path to streaming audit log

    class Meta:
        storage_configs = {
            "document": StorageConfig(storage_type=StorageType.DOCUMENT),
            "timeseries": StorageConfig(storage_type=StorageType.TIMESERIES),
        }
        path = "agent_sessions"
        indexes = [
            {"field": "session_id", "type": "hash"},
            {"field": "task_uid", "type": "hash"},
            {"field": "process_instance_uid", "type": "hash"},
            {"field": "status", "type": "hash"},
            {"field": "agent_preset", "type": "hash"},
        ]
```

---

## 4. BPMN Process Engine

### 4.1 Core Engine Implementation

**Location:** `backend/agents/engine.py`

```python
"""BPMN Process Engine - Graph traversal and task dispatch."""

from pathlib import Path
from datetime import datetime
from typing import Any

from base.backend.dataops.core.unified_crud import UnifiedCRUD
from base.backend.dataops.models.bpmn import (
    Process, ProcessInstance, Task, Gateway, Event, SequenceFlow,
    TaskType, TaskStatus, GatewayType, EventType
)
from base.backend.workers.manager import WorkerPoolManager
from base.backend.workers.types import PoolConfig, PoolType
from base.backend.utils.uuid_utils import uuid7

from scripts.automation.agent_cli import get_agent_cli, AgentConfigPresets
from backend.agents.models.agent_session import AgentSession
from backend.agents.executor import AgentTaskExecutor
from backend.agents.gateway_evaluator import GatewayEvaluator
from backend.agents.token_manager import TokenManager


class BPMNProcessEngine:
    """Execute BPMN processes using base worker pools and ami-agent CLI.

    Features:
    - Graph traversal with token-based execution
    - Task dispatch to ami-agent via worker pools
    - Gateway evaluation (exclusive/parallel/inclusive)
    - Event handling (start/end/error/timer)
    - State persistence via UnifiedCRUD
    """

    def __init__(self):
        self.crud = UnifiedCRUD()
        self.cli = get_agent_cli()  # ClaudeAgentCLI from scripts/automation
        self.pool_manager = WorkerPoolManager()

        # Configure worker pool
        self.pool_config = PoolConfig(
            name="bpmn_agents",
            pool_type=PoolType.UV_PROCESS,
            min_workers=2,
            max_workers=8,
            enable_hibernation=True,
            health_check_interval=30,
        )

        # Execution components
        self.task_executor = AgentTaskExecutor(self.cli, self.crud)
        self.gateway_evaluator = GatewayEvaluator()
        self.token_manager = TokenManager()

    async def initialize(self):
        """Initialize worker pool."""
        await self.pool_manager.create_pool(self.pool_config)

    async def execute_process(
        self,
        process_uid: str,
        variables: dict[str, Any] | None = None,
    ) -> ProcessInstance:
        """Execute BPMN process definition.

        Args:
            process_uid: Process UID from DataOps
            variables: Initial process variables

        Returns:
            ProcessInstance with final execution state
        """
        # Load Process from DataOps
        process = await self.crud.read(Process, process_uid)

        # Create ProcessInstance
        instance = ProcessInstance(
            process_id=process.uid,
            process_version=process.version,
            state="active",
            variables=variables or {},
            start_time=datetime.utcnow(),
        )
        instance_uid = await self.crud.create(instance)
        instance.uid = instance_uid

        # Find start event
        start_event = self._find_start_event(process)

        # Initialize token at start event
        await self.token_manager.create_token(instance, start_event.element_id)

        # Execute process graph
        await self._execute_from_node(instance, process, start_event)

        # Finalize instance
        instance.state = "completed"
        instance.end_time = datetime.utcnow()
        instance.duration_ms = int(
            (instance.end_time - instance.start_time).total_seconds() * 1000
        )
        await self.crud.update(instance)

        return instance

    async def _execute_from_node(
        self,
        instance: ProcessInstance,
        process: Process,
        node: Task | Gateway | Event,
    ):
        """Execute process graph starting from node.

        Implements token-based flow control with recursive traversal.
        """
        # Execute node based on type
        if isinstance(node, Task):
            await self._execute_task(instance, node)
        elif isinstance(node, Gateway):
            await self._evaluate_gateway(instance, process, node)
        elif isinstance(node, Event):
            await self._handle_event(instance, node)

        # Find outgoing flows
        outgoing_flows = self._get_outgoing_flows(process, node)

        # Follow flows based on gateway logic
        if isinstance(node, Gateway):
            if node.gateway_type == GatewayType.PARALLEL:
                # Parallel: follow ALL outgoing flows
                for flow in outgoing_flows:
                    target = self._get_node_by_id(process, flow.target_ref)
                    await self._execute_from_node(instance, process, target)
            else:
                # Exclusive/Inclusive: evaluate conditions
                enabled_flows = self.gateway_evaluator.evaluate_flows(
                    outgoing_flows,
                    instance.variables,
                    node.gateway_type
                )
                for flow in enabled_flows:
                    target = self._get_node_by_id(process, flow.target_ref)
                    await self._execute_from_node(instance, process, target)
        else:
            # Task/Event: follow single outgoing flow
            if outgoing_flows:
                flow = outgoing_flows[0]
                target = self._get_node_by_id(process, flow.target_ref)
                await self._execute_from_node(instance, process, target)

    async def _execute_task(self, instance: ProcessInstance, task: Task):
        """Execute BPMN task via ami-agent CLI.

        Task types mapped to ami-agent presets:
        - SERVICE: task_worker (full tools, hooks enabled)
        - BUSINESS_RULE: task_moderator / completion_moderator
        - SCRIPT: worker (for bash execution)
        - USER: interactive (human-in-loop)
        """
        # Update task state
        task.state = TaskStatus.ACTIVE
        task.started_at = datetime.utcnow()
        await self.crud.update(task)

        try:
            # Execute via worker pool + ami-agent
            result = await self.task_executor.execute(
                instance=instance,
                task=task,
                pool=await self.pool_manager.get_pool(self.pool_config.name),
            )

            # Update task state
            task.state = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.duration_ms = int(
                (task.completed_at - task.started_at).total_seconds() * 1000
            )
            await self.crud.update(task)

            # Update process variables
            instance.variables.update(result)
            await self.crud.update(instance)

        except Exception as e:
            task.state = TaskStatus.FAILED
            await self.crud.update(task)
            raise

    async def _evaluate_gateway(
        self,
        instance: ProcessInstance,
        process: Process,
        gateway: Gateway,
    ):
        """Evaluate gateway (no execution, just flow control)."""
        gateway.state = TaskStatus.ACTIVE
        await self.crud.update(gateway)

        # Gateway evaluation happens in _execute_from_node
        # Just mark as completed here
        gateway.state = TaskStatus.COMPLETED
        await self.crud.update(gateway)

    async def _handle_event(self, instance: ProcessInstance, event: Event):
        """Handle BPMN event."""
        if event.event_type == EventType.START:
            # Start events just pass through
            pass
        elif event.event_type == EventType.END:
            # End events terminate process
            instance.state = "completed"
            await self.crud.update(instance)
        elif event.event_type == EventType.ERROR:
            # Error events trigger error handling
            instance.state = "terminated"
            await self.crud.update(instance)

    def _find_start_event(self, process: Process) -> Event:
        """Find start event in process."""
        for node_id in process.flow_nodes:
            node = self._get_node_by_id(process, node_id)
            if isinstance(node, Event) and node.event_type == EventType.START:
                return node
        raise ValueError(f"No start event found in process {process.uid}")

    def _get_node_by_id(self, process: Process, node_id: str) -> Task | Gateway | Event:
        """Get flow node by ID (placeholder - actual impl queries CRUD)."""
        # In real implementation, query DataOps for the node
        # For now, assume nodes are loaded with process
        pass

    def _get_outgoing_flows(self, process: Process, node) -> list[SequenceFlow]:
        """Get outgoing sequence flows from node (placeholder)."""
        # In real implementation, query DataOps for flows
        pass
```

---

## 4.2 Task Executor (ami-agent Integration)

**Location:** `backend/agents/executor.py`

```python
"""Task execution via ami-agent CLI."""

from pathlib import Path
from typing import Any

from base.backend.dataops.core.unified_crud import UnifiedCRUD
from base.backend.dataops.models.bpmn import ProcessInstance, Task, TaskType
from base.backend.workers.base import WorkerPool
from base.backend.utils.uuid_utils import uuid7

from scripts.automation.agent_cli import AgentConfigPresets, AgentConfig
from backend.agents.models.agent_session import AgentSession


class AgentTaskExecutor:
    """Execute BPMN tasks via ami-agent CLI.

    Maps BPMN TaskType to AgentConfig presets and dispatches to worker pools.
    """

    def __init__(self, cli, crud: UnifiedCRUD):
        self.cli = cli  # ClaudeAgentCLI from scripts/automation
        self.crud = crud

    async def execute(
        self,
        instance: ProcessInstance,
        task: Task,
        pool: WorkerPool,
    ) -> dict[str, Any]:
        """Execute task via ami-agent in worker pool.

        Args:
            instance: ProcessInstance for context
            task: Task to execute
            pool: Worker pool for async execution

        Returns:
            Task output variables to merge into process state
        """
        # Get agent preset from task attributes
        preset_name = task.attributes.get("agent_preset", self._infer_preset(task))
        agent_config = self._create_agent_config(preset_name)

        # Create AgentSession record
        session_id = uuid7()
        session = AgentSession(
            session_id=session_id,
            task_uid=task.uid,
            process_instance_uid=instance.uid,
            agent_preset=preset_name,
            model=agent_config.model,
            allowed_tools=agent_config.allowed_tools,
            enable_hooks=agent_config.enable_hooks,
            enable_streaming=agent_config.enable_streaming,
            timeout=agent_config.timeout,
            instruction_file=task.implementation,  # Path to prompt .txt file
            status="running",
        )
        await self.crud.create(session)

        # Execute via worker pool
        result = await pool.submit_task(
            task_id=task.uid,
            callable=self.cli.run_print,
            instruction_file=Path(task.implementation),  # e.g., "backend/agents/prompts/task_worker.txt"
            stdin=self._prepare_stdin(instance, task),
            agent_config=agent_config,
            cwd=Path(task.attributes.get("cwd", ".")),
            audit_log_path=self._get_audit_log_path(session_id),
        )

        output, metadata = result

        # Update AgentSession
        session.status = "completed"
        session.stdout = output
        session.ended_at = datetime.utcnow()
        session.duration_ms = int(
            (session.ended_at - session.started_at).total_seconds() * 1000
        )
        if metadata:
            session.token_usage = metadata.get("usage", {})
            session.cost_usd = metadata.get("cost_usd")
        await self.crud.update(session)

        return {"output": output, "metadata": metadata}

    def _infer_preset(self, task: Task) -> str:
        """Infer agent preset from task type."""
        if task.task_type == TaskType.SERVICE:
            return "task_worker"
        elif task.task_type == TaskType.BUSINESS_RULE:
            return "task_moderator"
        elif task.task_type == TaskType.SCRIPT:
            return "worker"
        elif task.task_type == TaskType.USER:
            return "interactive"
        return "worker"

    def _create_agent_config(self, preset_name: str) -> AgentConfig:
        """Create agent config from preset."""
        preset_fn = getattr(AgentConfigPresets, preset_name)
        return preset_fn(session_id=uuid7())

    def _prepare_stdin(self, instance: ProcessInstance, task: Task) -> str:
        """Prepare stdin data for agent (process variables as JSON)."""
        import json
        return json.dumps({
            "process_variables": instance.variables,
            "task_attributes": task.attributes,
        })

    def _get_audit_log_path(self, session_id: str) -> Path:
        """Get audit log path for session."""
        return Path(f".cache/agent_sessions/{session_id}/audit.log")
```

---

## 5. BPMN Process Definitions

### 5.1 Task Execution Workflow

**File:** `backend/agents/processes/task_execution.bpmn.json`

Converts `scripts/automation/tasks.py` worker + moderator pattern to BPMN.

```json
{
  "process_uid": "proc_task_exec_v1",
  "name": "Task Execution with Validation",
  "version": "1.0.0",
  "is_executable": true,

  "flow_nodes": [
    {
      "uid": "start_1",
      "type": "Event",
      "event_type": "start",
      "name": "Task Started",
      "outgoing_flows": ["flow_1"]
    },
    {
      "uid": "task_worker",
      "type": "Task",
      "task_type": "service",
      "name": "Execute Task Worker",
      "implementation": "backend/agents/prompts/task_worker.txt",
      "attributes": {
        "agent_preset": "task_worker",
        "timeout": null
      },
      "incoming_flows": ["flow_1"],
      "outgoing_flows": ["flow_2"]
    },
    {
      "uid": "gateway_check",
      "type": "Gateway",
      "gateway_type": "exclusive",
      "name": "Check Completion Marker",
      "incoming_flows": ["flow_2"],
      "outgoing_flows": ["flow_done", "flow_feedback", "flow_retry"]
    },
    {
      "uid": "task_moderator",
      "type": "Task",
      "task_type": "businessRule",
      "name": "Validate Task Completion",
      "implementation": "backend/agents/prompts/task_moderator.txt",
      "attributes": {
        "agent_preset": "task_moderator"
      },
      "incoming_flows": ["flow_done"],
      "outgoing_flows": ["flow_end"]
    },
    {
      "uid": "task_feedback",
      "type": "Task",
      "task_type": "user",
      "name": "Handle Feedback Request",
      "implementation": "backend/agents/prompts/task_feedback.txt",
      "attributes": {
        "agent_preset": "interactive"
      },
      "incoming_flows": ["flow_feedback"],
      "outgoing_flows": ["flow_retry_loop"]
    },
    {
      "uid": "end_1",
      "type": "Event",
      "event_type": "end",
      "name": "Task Completed",
      "incoming_flows": ["flow_end", "flow_retry_fail"]
    }
  ],

  "sequence_flows": [
    {
      "uid": "flow_1",
      "source_ref": "start_1",
      "target_ref": "task_worker"
    },
    {
      "uid": "flow_2",
      "source_ref": "task_worker",
      "target_ref": "gateway_check"
    },
    {
      "uid": "flow_done",
      "source_ref": "gateway_check",
      "target_ref": "task_moderator",
      "condition_expression": "'WORK DONE' in variables['output']"
    },
    {
      "uid": "flow_feedback",
      "source_ref": "gateway_check",
      "target_ref": "task_feedback",
      "condition_expression": "'FEEDBACK:' in variables['output']"
    },
    {
      "uid": "flow_retry",
      "source_ref": "gateway_check",
      "target_ref": "end_1",
      "condition_expression": "variables.get('attempt_count', 0) >= 3"
    },
    {
      "uid": "flow_retry_loop",
      "source_ref": "task_feedback",
      "target_ref": "task_worker"
    },
    {
      "uid": "flow_end",
      "source_ref": "task_moderator",
      "target_ref": "end_1"
    }
  ]
}
```

### 5.2 Hook Validation Workflow

**File:** `backend/agents/processes/hook_validation.bpmn.json`

Converts hook validator pattern (PreToolUse, Stop) to BPMN subprocess.

```json
{
  "process_uid": "proc_hook_validation_v1",
  "name": "Hook Validation Subprocess",
  "version": "1.0.0",
  "is_executable": true,

  "flow_nodes": [
    {
      "uid": "start_hook",
      "type": "Event",
      "event_type": "start",
      "outgoing_flows": ["flow_parse"]
    },
    {
      "uid": "gateway_hook_type",
      "type": "Gateway",
      "gateway_type": "exclusive",
      "name": "Route by Hook Event",
      "incoming_flows": ["flow_parse"],
      "outgoing_flows": ["flow_pretool", "flow_stop", "flow_subagent"]
    },
    {
      "uid": "task_malicious_check",
      "type": "Task",
      "task_type": "businessRule",
      "name": "Malicious Behavior Check",
      "implementation": "scripts/automation/hooks.py:MaliciousBehaviorValidator",
      "incoming_flows": ["flow_pretool"],
      "outgoing_flows": ["flow_command_check"]
    },
    {
      "uid": "task_command_guard",
      "type": "Task",
      "task_type": "businessRule",
      "name": "Bash Command Guard",
      "implementation": "scripts/automation/hooks.py:CommandValidator",
      "incoming_flows": ["flow_command_check"],
      "outgoing_flows": ["flow_quality_check"]
    },
    {
      "uid": "gateway_tool_edit_write",
      "type": "Gateway",
      "gateway_type": "exclusive",
      "name": "Check if Edit/Write Tool",
      "incoming_flows": ["flow_quality_check"],
      "outgoing_flows": ["flow_quality_validate", "flow_quality_skip"]
    },
    {
      "uid": "task_quality_check",
      "type": "Task",
      "task_type": "businessRule",
      "name": "Code Quality Validation",
      "implementation": "scripts/automation/hooks.py:CoreQualityValidator",
      "incoming_flows": ["flow_quality_validate"],
      "outgoing_flows": ["flow_allow"]
    },
    {
      "uid": "task_response_scan",
      "type": "Task",
      "task_type": "businessRule",
      "name": "Response Scanner (WORK DONE check)",
      "implementation": "scripts/automation/hooks.py:ResponseScanner",
      "incoming_flows": ["flow_stop"],
      "outgoing_flows": ["flow_allow"]
    },
    {
      "uid": "end_hook",
      "type": "Event",
      "event_type": "end",
      "incoming_flows": ["flow_allow", "flow_quality_skip"]
    }
  ],

  "sequence_flows": [
    {
      "uid": "flow_parse",
      "source_ref": "start_hook",
      "target_ref": "gateway_hook_type"
    },
    {
      "uid": "flow_pretool",
      "source_ref": "gateway_hook_type",
      "target_ref": "task_malicious_check",
      "condition_expression": "variables['hook_event'] == 'PreToolUse'"
    },
    {
      "uid": "flow_stop",
      "source_ref": "gateway_hook_type",
      "target_ref": "task_response_scan",
      "condition_expression": "variables['hook_event'] == 'Stop'"
    },
    {
      "uid": "flow_command_check",
      "source_ref": "task_malicious_check",
      "target_ref": "task_command_guard"
    },
    {
      "uid": "flow_quality_check",
      "source_ref": "task_command_guard",
      "target_ref": "gateway_tool_edit_write"
    },
    {
      "uid": "flow_quality_validate",
      "source_ref": "gateway_tool_edit_write",
      "target_ref": "task_quality_check",
      "condition_expression": "variables['tool_name'] in ['Edit', 'Write']"
    },
    {
      "uid": "flow_quality_skip",
      "source_ref": "gateway_tool_edit_write",
      "target_ref": "end_hook",
      "is_default": true
    },
    {
      "uid": "flow_allow",
      "source_ref": "task_quality_check",
      "target_ref": "end_hook"
    }
  ]
}
```

### 5.3 Code Audit Workflow

**File:** `backend/agents/processes/code_audit.bpmn.json`

Converts `scripts/automation/audit.py` parallel execution to BPMN.

```json
{
  "process_uid": "proc_code_audit_v1",
  "name": "Parallel Code Audit",
  "version": "1.0.0",
  "is_executable": true,

  "flow_nodes": [
    {
      "uid": "start_audit",
      "type": "Event",
      "event_type": "start",
      "outgoing_flows": ["flow_scan"]
    },
    {
      "uid": "task_scan_files",
      "type": "Task",
      "task_type": "script",
      "name": "Scan Directory for Auditable Files",
      "implementation": "inline:scan_audit_files",
      "attributes": {
        "max_file_size": 1048576,
        "include_patterns": ["*.py", "*.ts", "*.js"],
        "exclude_patterns": ["*.test.*", "__pycache__/*"]
      },
      "incoming_flows": ["flow_scan"],
      "outgoing_flows": ["flow_parallel"]
    },
    {
      "uid": "gateway_parallel",
      "type": "Gateway",
      "gateway_type": "parallel",
      "name": "Audit Files in Parallel",
      "incoming_flows": ["flow_parallel"],
      "outgoing_flows": ["flow_audit_*"]
    },
    {
      "uid": "task_audit_file",
      "type": "Task",
      "task_type": "service",
      "name": "Audit Single File",
      "implementation": "backend/agents/prompts/audit_file.txt",
      "attributes": {
        "agent_preset": "audit"
      },
      "is_multi_instance": true,
      "multi_instance_collection": "files_to_audit",
      "incoming_flows": ["flow_audit_*"],
      "outgoing_flows": ["flow_collect"]
    },
    {
      "uid": "gateway_collect",
      "type": "Gateway",
      "gateway_type": "parallel",
      "name": "Collect Results",
      "gateway_direction": "converging",
      "incoming_flows": ["flow_collect"],
      "outgoing_flows": ["flow_consolidate"]
    },
    {
      "uid": "task_consolidate",
      "type": "Task",
      "task_type": "service",
      "name": "Consolidate Patterns from Failures",
      "implementation": "backend/agents/prompts/consolidate_patterns.txt",
      "attributes": {
        "agent_preset": "consolidate"
      },
      "incoming_flows": ["flow_consolidate"],
      "outgoing_flows": ["flow_end"]
    },
    {
      "uid": "end_audit",
      "type": "Event",
      "event_type": "end",
      "incoming_flows": ["flow_end"]
    }
  ],

  "sequence_flows": [
    {
      "uid": "flow_scan",
      "source_ref": "start_audit",
      "target_ref": "task_scan_files"
    },
    {
      "uid": "flow_parallel",
      "source_ref": "task_scan_files",
      "target_ref": "gateway_parallel"
    },
    {
      "uid": "flow_collect",
      "source_ref": "task_audit_file",
      "target_ref": "gateway_collect"
    },
    {
      "uid": "flow_consolidate",
      "source_ref": "gateway_collect",
      "target_ref": "task_consolidate"
    },
    {
      "uid": "flow_end",
      "source_ref": "task_consolidate",
      "target_ref": "end_audit"
    }
  ]
}
```

---

## 6. Implementation Plan

### Phase 1: Foundation (Week 1)

**Goal:** Core engine with single-task execution

1. **Create directory structure** (`backend/agents/`)
2. **Implement AgentSession model** with DataOps registration
3. **Implement BPMNProcessEngine skeleton** (graph traversal stub)
4. **Implement AgentTaskExecutor** (ami-agent integration)
5. **Create simple test process** (single task: start → service task → end)
6. **Integration test:** Load process, execute via ami-agent, verify AgentSession

**Success Criteria:**
- Can load BPMN process from DataOps
- Can execute single SERVICE task via ami-agent
- AgentSession created and updated correctly
- No changes to `/scripts/automation`

### Phase 2: Gateway Logic (Week 2)

**Goal:** Exclusive and parallel gateways

1. **Implement GatewayEvaluator** (condition expression evaluation)
2. **Implement TokenManager** (token flow tracking)
3. **Add exclusive gateway support** to engine
4. **Add parallel gateway support** to engine
5. **Create task_execution.bpmn.json** (worker + moderator + gateway)
6. **Integration test:** Execute task workflow with completion check

**Success Criteria:**
- Exclusive gateway correctly routes based on conditions
- Parallel gateway spawns multiple execution paths
- Task retry loop works via gateway feedback flow

### Phase 3: Workflow Migration (Week 3)

**Goal:** Convert existing workflows to BPMN

1. **Create hook_validation.bpmn.json** (hook validator chain)
2. **Create code_audit.bpmn.json** (parallel file audits)
3. **Create docs_maintenance.bpmn.json**
4. **Create git_sync.bpmn.json**
5. **Side-by-side testing:** Run old Python vs new BPMN
6. **Performance benchmarking**

**Success Criteria:**
- All workflows executable as BPMN processes
- Output matches existing Python implementation
- Performance within 10% of baseline

### Phase 4: Event Handling (Week 4)

**Goal:** Error events, timer events, compensation

1. **Implement error event handling** (try/catch flows)
2. **Implement timer events** (delayed execution)
3. **Add compensation handlers** (rollback logic)
4. **Add subprocess support** (call activity)
5. **Add event-based gateway** (message/signal routing)
6. **Integration tests for error handling**

**Success Criteria:**
- Error events correctly trigger error flows
- Timer events schedule delayed tasks
- Compensation handlers rollback on failure

### Phase 5: Production Readiness (Week 5)

**Goal:** Monitoring, metrics, documentation

1. **Add process metrics collection** (execution time, success rate)
2. **Add health checks** for engine and worker pools
3. **Create process definition validator** (BPMN schema validation)
4. **Add process versioning support** (v1 → v2 migration)
5. **Write comprehensive documentation**
6. **Create migration guide** (Python workflows → BPMN)

**Success Criteria:**
- Process metrics visible in DataOps
- Health checks passing
- Documentation complete
- Ready for production deployment

---

## 7. Testing Strategy

### Unit Tests

```
tests/unit/backend/agents/
├── models/
│   └── test_agent_session.py        # AgentSession model tests
├── test_engine.py                    # BPMNProcessEngine tests
├── test_executor.py                  # AgentTaskExecutor tests
├── test_gateway_evaluator.py        # Gateway condition evaluation
├── test_token_manager.py             # Token flow management
└── test_process_loader.py            # BPMN JSON validation
```

### Integration Tests

```
tests/integration/backend/agents/
├── test_single_task_execution.py    # Start → Task → End
├── test_task_workflow.py            # Worker + moderator + gateway
├── test_hook_validation.py          # Hook validator chain
├── test_code_audit.py               # Parallel file audits
├── test_error_handling.py           # Error events and compensation
└── test_timer_events.py             # Delayed execution
```

### Critical Test Cases

1. **Agent Session Tracking:** Verify AgentSession created/updated for every task execution
2. **Hook Integration:** Verify hooks still work via ami-agent (bash guard, quality check)
3. **Streaming Output:** Verify streaming audit logs written correctly
4. **Worker Pool:** Verify tasks execute asynchronously in worker pool
5. **Gateway Logic:** Verify exclusive/parallel/inclusive gateways route correctly
6. **Error Handling:** Verify error events trigger compensation handlers
7. **Process Metrics:** Verify execution metrics collected in timeseries storage

---

## 8. Migration from scripts/automation

### What STAYS (No Changes)

✅ `scripts/automation/agent_cli.py` - ClaudeAgentCLI (battle-tested, reuse as-is)
✅ `scripts/automation/hooks.py` - All hook validators
✅ `scripts/automation/config.py`, `logger.py`, `validators.py`
✅ `scripts/automation/transcript.py` - Transcript parsing for moderators
✅ Hook configuration files in `scripts/config/hooks.yaml`

### What MOVES (Refactored)

**Logic moved into BPMN:**
- `scripts/automation/tasks.py` → `processes/task_execution.bpmn.json`
- `scripts/automation/audit.py` → `processes/code_audit.bpmn.json`
- `scripts/automation/docs.py` → `processes/docs_maintenance.bpmn.json`
- `scripts/automation/sync.py` → `processes/git_sync.bpmn.json`

**Execution moved into engine:**
- Process orchestration → `BPMNProcessEngine`
- Task dispatch → `AgentTaskExecutor`
- Parallel execution → Worker pools (already in base)

### Migration Path

1. **Keep Python scripts running** (no changes yet)
2. **Build BPMN engine alongside** (Phase 1-2)
3. **Test BPMN workflows side-by-side** (Phase 3)
4. **Gradual cutover** (workflow by workflow)
5. **Archive Python scripts** (after full validation)

---

## 9. Future Work (Out of Scope)

**NOT INCLUDED in this spec:**

❌ **MCP Server Integration** - Future work, add `backend/agents/mcp_server.py` later
❌ **LangChain Integration** - Optional enhancement, not core requirement
❌ **Visual Process Designer** - BPMN JSON hand-authored for now
❌ **Multi-Provider Support** (Gemini CLI) - Keep ClaudeAgentCLI only for now
❌ **Advanced Event Types** - Message/signal events (Phase 4+)
❌ **Process Simulation** - Dry-run mode (future)

---

## 10. Benefits Summary

| Aspect | Before (Python) | After (BPMN) |
|--------|-----------------|--------------|
| **Workflow Definition** | Hardcoded Python | Declarative BPMN JSON |
| **Visualization** | None | Process graphs in DataOps |
| **Versioning** | Git commits | Process version control |
| **Parallel Execution** | Custom thread pools | Base worker pools + BPMN parallel gateway |
| **Error Handling** | Try/catch in Python | BPMN error events + compensation |
| **Audit Trail** | Log files | DataOps: ProcessInstance + AgentSession |
| **Reusability** | Copy/paste Python | Compose BPMN subprocesses |
| **Governance** | Code review | Process approval workflow |

---

## 11. Success Metrics

- ✅ **Zero changes to `/scripts/automation`** during Phase 1-3
- ✅ **All workflows executable as BPMN** by end of Phase 3
- ✅ **Performance within 10%** of baseline Python implementation
- ✅ **100% hook compatibility** - All validators work via ami-agent
- ✅ **AgentSession tracking** - Every task execution auditable in DataOps
- ✅ **Process metrics** - Execution time, success rate, retry count tracked
- ✅ **Worker pool efficiency** - 90%+ worker utilization during parallel execution

---

## END OF SPECIFICATION

**Status:** Ready for Implementation
**Owner:** Backend Team
**Timeline:** 5 weeks (Phase 1-5)
**Dependencies:** Base BPMN models (already exist), ami-agent CLI (already exists)
**Risk:** Low (no breaking changes to existing systems)
