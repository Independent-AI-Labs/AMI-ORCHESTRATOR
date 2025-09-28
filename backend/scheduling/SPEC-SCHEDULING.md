# AMI Scheduling Service Specification

## 1. Mission & Scope
- Provide a unified process and event scheduling service that interprets BPMN 2.0 models from Base DataOps, orchestrates worker execution via the shared worker pools, and exposes lifecycle control through a dedicated MCP server.
- Replace ad-hoc timers and per-module cron scripts with a policy-aware scheduler that supports long-running business processes, near-real-time signals, and compliance-driven audit requirements.
- Operate as a first-class backend module (mounted under `backend/scheduling/`) with documentation and tooling in the new top-level `scheduling/` package.

## 2. Design Principles & Alignment
- **Single Source of Truth:** BPMN definitions (`base.backend.dataops.models.bpmn.Process`) and instances remain the canonical representation. The scheduler consumes these models directly through `UnifiedCRUD`.
- **Base Patterns Reuse:** Leverage Base worker pools (`base.backend.workers.*`) for execution and the existing FastMCP transport conventions described in `base/docs/MCP_SERVERS.md`.
- **Compliance-first:** Emit auditable records compatible with the compliance backend (`compliance/docs/research/COMPLIANCE_BACKEND_SPEC.md`) and the consolidated EU AI Act/ISO requirements.
- **Extensibility:** Support domain modules (Nodes, Streams, Domains) through modular adapters rather than bespoke schedulers.
- **Fault Tolerance:** Emphasise idempotent job handling, persistent state, and deterministic recovery after restarts.

## 3. High-level Architecture
1. **Scheduler MCP Server** – FastMCP service exposing tooling for process registration, instance lifecycle, event publication, and monitoring.
2. **Process Registry** – Abstraction over Base DataOps to manage BPMN process definitions, versions, and metadata (graph + document storage).
3. **Runtime Orchestrator** – Coordinates process instances, token flow, and task state transitions following BPMN semantics.
4. **Temporal Queueing Layer** – Maintains timers, cron-like schedules, SLAs, and delayed jobs using a hierarchical time-wheel backed by durable storage (timeseries + in-memory heap).
5. **Worker Dispatch Layer** – Translates ready BPMN tasks into `TaskInfo` payloads for Base worker pools (thread/process/async). Handles pooling, back-pressure, retries.
6. **Event Gateway** – Normalises external triggers (webhooks, message brokers, DataOps events) into BPMN intermediate events; replaces the removed `backend/events` skeleton.
7. **Observability & Audit** – Structured logging, metrics (`ProcessMetrics`), and audit hooks publishing to Compliance backend sinks.

The service runs as an async application (FastAPI + FastMCP tooling) with optional background runners managed by the Node setup automation.

## 4. Data Model Extensions
While reusing existing models wherever possible, the scheduler introduces the following persisted structures (all defined with `StorageModel` subclasses):

| Model | Purpose | Storage Targets |
| --- | --- | --- |
| `ScheduleDefinition` | Connects BPMN `Process` to scheduling metadata (cron, calendar, SLAs, activation windows). | `document`, `graph` |
| `ScheduledEvent` | Tracks future triggers (timer events, deadlines) with deterministic ordering. | `timeseries`, `inmem` |
| `ExecutionWindow` | Records resource windows and blackout periods for worker pools. | `document` |
| `WorkerBinding` | Captures mapping between BPMN lanes/roles and worker pool configs. | `graph`, `document` |
| `ProcessAuditRecord` | Lightweight envelope referencing Compliance backend audit collection. | `document`, `timeseries` |

All models include `tenant_id`, `correlation_key`, and `data_classification` fields to maintain compliance parity. They reference Base enums (`EventType`, `TaskStatus`) to keep the vocabulary consistent.

## 5. BPMN Execution Semantics
- **Definition Intake:** BPMN XML is parsed upstream using Base utilities (`create_process_from_bpmn` once implemented). The scheduler requires validated `Process`, `Task`, `Gateway`, `Event`, and `SequenceFlow` records stored through DataOps.
- **Instance Lifecycle:**
  1. `created` – Process instance inserted (optionally by external request via MCP).
  2. `active` – Tokens dispatched according to start events; tasks created as `TaskStatus.READY`.
  3. `waiting` – Intermediate events (message, timer, signal) pending external triggers.
  4. `completed` / `terminated` / `suspended` – Terminal states recorded with `ProcessMetrics` updates.
- **Token Engine:** Deterministic DFS/BFS execution that respects gateway semantics (exclusive, parallel, event-based). Token state stored alongside `ProcessInstance.tokens` to allow replay.
- **Correlation Keys:** Scheduler enforces `business_key` uniqueness per active instance when BPMN requires correlation, enabling idempotent external signalling.
- **Compensation & SLA:** Tasks flagged `is_for_compensation` schedule compensating activities, while SLA timers are registered in the Temporal Queueing Layer.

## 6. Scheduling Semantics
- **Trigger Types:**
  - Cron / interval timers (`EventDefinition.TIMER`).
  - Absolute deadlines (ISO8601 timestamps).
  - Data-driven triggers (DataOps query watchers or Streams events).
  - Manual / ad-hoc triggers via MCP (`scheduler_trigger_event`).
- **Queue Implementation:**
  - Primary queue: persistent min-heap keyed by `scheduled_for` timestamp, backed by `ScheduledEvent` records.
  - In-memory cache: wheel-of-time buckets for near-term execution (<5 minutes) refreshed on each service tick.
  - Failover: upon restart, heap reconstructed from `ScheduledEvent` documents.
- **Prioritisation:** Events inherit priority from BPMN task `priority` or SLA criticality; ties broken by creation time.
- **Retry Policy:** Configurable per task (default `max_retries=3`, exponential backoff). Failures escalate via `ProcessAuditRecord` and compliance hooks.
- **Calendar Awareness:** `ExecutionWindow` defines allowed execution times (e.g., weekdays 9–5). The scheduler defers events during blackout windows unless flagged `override_window`.

## 7. Worker Orchestration
- Use `WorkerPoolManager` to allocate pools derived from `WorkerBinding`. For example, a “data-prep” lane binds to a process pool with GPU profile.
- Each ready task materialises a `TaskInfo` object with metadata (`func`, `args`, `timeout`, `priority`). A dispatcher coroutine submits the task to the allocated pool.
- Worker telemetry feeds back into `ProcessMetrics` and compliance dashboards. Metrics such as duration, failure rates, and resource usage populate `PoolStats` and `ProcessMetrics.task_metrics`.
- Hibernation and TTL follow Base defaults; scheduler persists worker state if `PoolConfig.enable_persistence`.

## 8. MCP Server Contract
Expose the following FastMCP tools (naming mirrors existing conventions):

| Tool | Description | Key Arguments |
| --- | --- | --- |
| `scheduler_define_process` | Register or update a BPMN process + schedule metadata. | `process_payload`, `schedule_definition`, `activate` |
| `scheduler_start_instance` | Instantiate a process immediately. | `process_id`, `business_key`, `variables` |
| `scheduler_trigger_event` | Publish external event (message/signal) into an instance. | `instance_id`/`business_key`, `event_type`, `payload` |
| `scheduler_pause_instance` | Suspend execution and timers. | `instance_id`, optional `reason` |
| `scheduler_resume_instance` | Resume suspended instance. | `instance_id` |
| `scheduler_cancel_instance` | Terminate instance with compensation handling. | `instance_id`, `reason`, `compensate` |
| `scheduler_get_metrics` | Retrieve aggregated metrics and SLAs. | `process_id`, `time_window` |
| `scheduler_list_events` | Inspect pending timers/deadlines. | `process_id`/`instance_id`, `states` |

Responses follow FastMCP conventions (`content` array with JSON/text blocks). Tool invocations must enforce RBAC and tenant scoping; the server reuses Base authentication middleware once the compliance backend finalises token issuance.

## 9. Service Interfaces & Deployment
- **Internal API:** Async Python services (FastAPI routers) consumed by the MCP server handlers and optional REST/gRPC gateways.
- **Config:** `.env` keys prefixed with `AMI_SCHEDULER_` (e.g., `AMI_SCHEDULER_DEFAULT_POOL`, `AMI_SCHEDULER_TICK_INTERVAL`). Config loading uses Base `PathFinder` and `EnvironmentSetup` helpers.
- **Process Execution Runtime:** Deployable as a standalone service (managed via Node setup automation) or embedded in orchestration nodes. Container image inherits from Base uv runtime with optional compute profiles.
- **Scaling:** Horizontal sharding by tenant or process group; leader election required for timer ownership (candidate implementation: PostgreSQL advisory locks or Redis Redlock).

## 10. Observability & Compliance Hooks
- Structured logs with correlation IDs and `business_key` tagging.
- Metrics emitted to Prometheus-compatible endpoint (`process_events_total`, `scheduler_queue_depth`, `worker_retry_total`).
- Audit pipeline:
  1. Mutating MCP calls create `ProcessAuditRecord` documents.
  2. Records forwarded to compliance backend via its MCP subscriber or direct HTTP ingestion.
  3. High-severity events (SLA breach, repeated failure) surface notifications to the Streams module.
- Data retention policies align with consolidated ISO 27001/42001 controls (minimum 1 year for scheduling logs, configurable per tenant).

## 11. Integration Roadmap
1. **Phase 0 – Foundations**
   - Implement new DataOps models (`ScheduleDefinition`, `ScheduledEvent`, etc.).
   - Build scheduler runtime skeleton with persistent queue and worker dispatch stub.
2. **Phase 1 – BPMN Execution**
   - Implement token engine covering start/end events, user/service tasks, gateways.
   - Wire MCP server tools and enforce tenant-aware RBAC.
3. **Phase 2 – External Integrations**
   - Add connectors for DataOps change feeds, Streams events, and Node-managed services.
   - Integrate compliance audit pipeline and metrics exporters.
4. **Phase 3 – Resilience & Scale**
   - Introduce horizontal sharding, leader election, SLA analytics, and predictive capacity planning.
5. **Phase 4 – Advanced Features**
   - Support adaptive scheduling (AI-driven prioritisation), scenario simulation, and integration with UX orchestration dashboards.

## 12. Open Questions & Future Notes
- **BPMN XML Parser Availability:** `create_process_from_bpmn` remains unimplemented; evaluate third-party parsers or build in-house tooling.
- **Distributed Timer Ownership:** Need a consensus-backed mechanism (Postgres advisory locks vs. a dedicated coordinator) before multi-replica deployments.
- **Secrets Handling:** Worker bindings may need secret material (API tokens); coordinate with `base/SPEC-SECRETS-BROKER.md` to ensure secrets are fetched via the broker rather than embedded in schedules.
- **Compliance Backend Interface:** Finalise audit payload schema once the compliance backend API stabilises to avoid double-writing logs.
- **UX/Operator Console:** Determine whether operator dashboards live in the UX module or via third-party observability tools.

---
Author: AMI Orchestrator Docs Team  
Status: Draft (seeking review)  
Last Updated: 2025-09-27
