# AMI Agents Service Specification

## 1. Mission & Scope
- Deliver the primary multi-agent orchestration layer for AMI, embedded under `backend/agents/`.
- Build directly on Base infrastructure (DataOps, worker pools, MCP tooling) while standardising on LangChain/LangGraph for agent workflows.
- Provide first-class support for Google Generative AI via LangChain, leveraging `base.backend.llms.providers.google_code_assist.ChatGoogleCodeAssist` and extending it where necessary.
- Expose the entire capability set as a dedicated MCP server responsible for agent provisioning, session routing, and conversation lifecycle management.

## 2. Design Principles
- **Base Alignment:** Reuse Base DataOps models, security helpers, PathFinder configuration, and worker pools. Any new models are defined with `StorageModel` and registered through UnifiedCRUD.
- **MCP-Native:** Agents service both consumes existing MCP servers (DataOps, SSH, Compliance) and exposes its own FastMCP interface for higher-level orchestration.
- **Session-Centric Architecture:** Treat every user/agent interaction as a persisted session with immutable conversation history and reproducible execution traces.
- **Composable Agent Graphs:** Prefer modular subgraphs (LangGraph) and toolkits over monolithic prompts to support future governance and testing.
- **Compliance-Ready:** Integrate audit capture, redaction, and policy enforcement consistent with consolidated EU AI Act and ISO 27001/42001 documentation.

## 3. High-Level Architecture
1. **Agent MCP Server** – FastMCP implementation providing tools for agent creation, configuration, session control, and message exchange.
2. **Session Manager** – Manages multi-tenant sessions, stores transcripts/metadata in DataOps (document + timeseries backends), and enforces retention policies.
3. **Agent Registry** – Catalog of agent templates, policies, and associated LangChain/LangGraph graphs backed by versioned StorageModels.
4. **Execution Engine** – Coordinates LangChain chains or LangGraph state machines, integrates tools (MCP tool calling, HTTP, function calling), and dispatches heavy tasks to Base worker pools.
5. **Tooling Gateway** – Wraps external MCP servers, local tools, and compliance hooks into LangChain `Tool` abstractions with typed schemas.
6. **LLM Provider Abstraction** – Extends Base `ChatGoogleCodeAssist` plus any additional providers (OpenAI, Anthropic) via plug-in strategy and environment-aware configuration.
7. **Observability & Audit Layer** – Structured logging, metrics emission, and audit record generation consumed by the compliance backend.

## 4. Dependencies & Integrations
- **Base Module:**
  - `base.backend.llms.providers.google_code_assist.ChatGoogleCodeAssist` as the default Google Generative AI connector, including its OAuth/token refresh flow.
  - Built-in helpers (`complete_code`, `review_code`, etc.) must be exposed to agents via LangChain tools so code-assist scenarios work out of the box.
  - `base/backend/workers` for async/parallel execution when agent graphs invoke background tasks.
  - `base/docs/MCP_SERVERS.md` conventions for FastMCP transport support.
- **LangChain / LangGraph:**
  - Install `langchain` and `langgraph` (or `langgraph-sdk`) scoped to the Agents module virtual environment.
  - Confirm `langchain_google_genai` dependency is present; if not, add to module requirements.

### Google Generative AI Alignment
- Mirror the official Node-based Gemini CLI (`https://github.com/google-gemini/gemini-cli`, see `packages/core/src/code_assist/server.ts`) which hits `https://cloudcode-pa.googleapis.com/v1internal:{method}`.
- Support the same methods: `generateContent`, `streamGenerateContent` (SSE), `countTokens`, `onboardUser`, `loadCodeAssist`, `getCodeAssistGlobalUserSetting`, and `setCodeAssistGlobalUserSetting`, while keeping space for `embedContent` once Google enables it.
- Reproduce the CLI's streaming contract (`alt=sse` with `data:` lines) and FinishReason handling when routing responses into LangGraph supervisors.
- Authenticate via a shared `OAuth2Client` connected to the Base `AuthProvider` store (per `TODO-AUTH.md`) with policy-governed switchover to API keys.
- Track API changes through the Code Assist documentation and the CLI's release notes (`GEMINI.md`), and add regression tests that exercise these endpoints end-to-end.

- **External MCP Servers:**
  - DataOps MCP for CRUD operations.
  - SSH MCP for remote execution.
  - Compliance MCP (future) for audit submission.
- **Storage Backends:**
  - Sessions in document store with optional vector embeddings for recall.
  - Timeseries for token usage, latency metrics.
  - Graph store to express relationships between agents, policies, and tools.

## 5. Data Model Blueprint
Define new StorageModels (under `backend/agents/models/`):

| Model | Purpose | Key Fields | Storage Targets |
| --- | --- | --- | --- |
| `AgentTemplate` | Versioned agent definition (prompt, graph topology, tool list). | `template_id`, `name`, `description`, `graph_manifest`, `tool_refs`, `policy_tags`, `version`, `is_default` | `document`, `graph` |
| `AgentInstance` | Runtime-specific configuration derived from template. | `instance_id`, `template_id`, `tenant_id`, `parameters`, `state_snapshot`, `created_by`, `status` | `document`, `inmem` |
| `AgentSession` | Conversation session metadata. | `session_id`, `instance_id`, `tenant_id`, `user_ids`, `channel`, `started_at`, `ended_at`, `status`, `labels` | `document`, `timeseries` |
| `MessageRecord` | Individual message or event within a session. | `message_id`, `session_id`, `sender`, `role`, `content`, `attachments`, `tool_calls`, `latency_ms` | `document`, `timeseries` |
| `ToolBinding` | Mapping between LangChain tool descriptors and MCP endpoints. | `binding_id`, `tool_name`, `mcp_server`, `mcp_tool`, `input_schema`, `output_schema`, `auth_scope` | `document`, `graph` |
| `SessionMetrics` | Aggregated metrics for dashboards. | `session_id`, `window`, `token_usage`, `completion_reason`, `satisfaction_score`, `policy_flags` | `timeseries` |

All models inherit Base security mixins (`tenant_id`, `data_classification`, `tags`) and integrate with compliance retention policies.

## 6. LangChain / LangGraph Research Summary
- **ReAct + Tool-Calling Agents:** Provide interpretability and works with LangChain `AgentExecutor`. Suitable for deterministic tool sequences.
- **ConversationGraph (LangGraph):** State-machine style for managing multi-turn conversations with branching logic; ideal for policy enforcement and guardrails.
- **Supervisor/Worker Graphs:** Hierarchical LangGraph pattern where a supervisor agent routes tasks to specialised worker subgraphs. Supports multi-agent collaboration, aligning with Open AMI objectives.
- **Memory Augmented Chains:** Use LangChain `ConversationBufferMemory`, `VectorStoreRetrieverMemory`, or custom DataOps-backed memory to persist context per session.
- **Evaluation & Guardrails:** Integrate LangChain `RunnableWithMessageHistory`, `Tracer` for observability, and `Guardrails` for content moderation.

> Recommendation: Adopt LangGraph as the core execution abstraction with compatibility adapters for legacy LangChain `AgentExecutor`. Provide scaffolding for supervisor-worker graphs to enable compliance handoffs (e.g., Risk Analyst agent, Ops agent).

## 7. Session & Conversation Management
- Each session references an `AgentInstance` and stores conversation state in `AgentSession` + `MessageRecord` models.
- Implement session lifecycle:
  1. `session_create` – instantiate `AgentSession`, optionally warm agent memory.
  2. `session_send` – append message, invoke execution engine, store response.
  3. `session_pause` / `session_resume` – toggle active flag, persist state snapshot.
  4. `session_close` – mark ended, flush metrics, emit audit entry.
- Support concurrent sessions per agent with optimistic locking or vector clocks to avoid race conditions.
- Provide streaming responses back to clients (MCP SSE transport) and record token-level telemetry.

## 8. MCP Server Contract
Expose new FastMCP tools (names subject to refinement):

| Tool | Description | Arguments |
| --- | --- | --- |
| `agents_create_template` | Register or update an `AgentTemplate`. | `template_payload` |
| `agents_list_templates` | Enumerate available templates with filters. | `filters` |
| `agents_spawn_instance` | Materialise an `AgentInstance` from template. | `template_id`, `parameters`, `tenant_id` |
| `agents_close_instance` | Tear down an instance, releasing resources. | `instance_id`, optional `reason` |
| `agents_start_session` | Create new session bound to an instance. | `instance_id`, `user_context`, `channel`, `metadata` |
| `agents_send_message` | Post user/input message and stream agent response. | `session_id`, `message`, optional `tool_hints` |
| `agents_get_session` | Fetch session state and history. | `session_id`, `include_messages`, `limit` |
| `agents_list_sessions` | List sessions by tenant/user/status. | `filters` |
| `agents_register_tool` | Bind a LangChain tool to an MCP endpoint or local callable. | `tool_binding_payload` |
| `agents_metrics` | Retrieve aggregated metrics for sessions/agents. | `filters`, `time_window` |

Responses follow FastMCP JSON schema, returning `content` blocks with JSON payloads. Streaming is handled by SSE or streamable HTTP transports as in Base MCP servers.

## 9. Tool Integration Strategy
- Wrap MCP servers as LangChain tools using standardized descriptors (`name`, `description`, `args_schema`). Implement helper to auto-generate Pydantic schemas from MCP tool metadata.
- Support local tools (e.g., Python callables) via LangChain `Tool` interface; ensure they comply with compliance policy tags.
- Provide secure credential access via the Secrets Broker (`base/SPEC-SECRETS-BROKER.md`). Tool bindings reference secrets by identifier, not raw values.

## 10. Execution Engine Details
- **Graph Runtime:** Use LangGraph `StateGraph` with nodes representing steps (LLM call, tool invocation, decision). Supervisory nodes enforce policies (e.g., content moderation, guardrails).
- **Concurrency:** For long-running tools, dispatch tasks to Base worker pools (`WorkerPoolManager`) with async callbacks to resume the graph when results arrive.
- **Memory:** Provide pluggable memory adapters (buffer, summary, vector store). Default to DataOps-backed memory with optional retrieval augmentation.
- **Resilience:** Implement multi-provider strategy (Google GenAI primary, with policy-gated switchover to open-source models) and strict selection rules.

## 11. Multi-Session Scaling & Persistence
- Sessions stored in document DB with indexes on `tenant_id`, `status`, `created_at`.
- Message history can be chunked (pagination) and optionally mirrored to a vector store for semantic search.
- Introduce session TTL with archival job managed by scheduling service.
- Provide rate limiting per tenant/user using Base security utilities.

## 12. Compliance & Governance
- Tag every message with `data_classification` and `policy_flags` (e.g., PII detected).
- Integrate with Compliance backend via MCP event hooks (`compliance_audit_ingest`).
- Support redaction policies before persisting or emitting transcripts.
- Maintain configurable logging retention aligned with ISO controls.

## 13. Deployment & Operations
- Package as async FastAPI application similar to scheduling service.
- Environment variables prefixed `AMI_AGENTS_` for configuration (default model, session TTL, rate limits).
- Provide scripts under `backend/agents/scripts/` for running the MCP server (`run_agents_fastmcp.py`).
- Node setup automation: extend `nodes/config/setup-service.yaml` with Agents service management (start/stop, health probes).
- Include smoke tests to validate MCP endpoints and LangGraph execution.

## 14. Roadmap
1. **Phase 0 – Foundations**
   - Scaffold module structure, add dependencies, implement base StorageModels, and create FastMCP skeleton with health endpoint.
   - Integrate Google Generative AI provider through LangChain.
2. **Phase 1 – Session Management**
   - Implement templates, instances, session CRUD, and message persistence.
   - Provide minimal LangGraph execution for single-tool conversation.
3. **Phase 2 – Tooling & Multi-Agent Graphs**
   - Implement tool bindings for DataOps and SSH MCP servers.
   - Add supervisor-worker graphs and memory adapters.
4. **Phase 3 – Observability & Compliance**
   - Add metrics, audit pipelines, and policy enforcement (safety filters, RBAC).
5. **Phase 4 – Advanced Features**
   - Introduce adaptive routing, persona marketplace, marketplace integration with UX, and simulation/testing harness.

## 15. Open Questions / Future Notes
- **LangGraph Runtime Licensing:** Confirm LangGraph usage terms for commercial deployment.
- **Streaming Contracts:** Decide on standard SSE payload schema for streaming responses across modules.
- **Testing Strategy:** Need systematic agent regression tests (prompt unit tests, replay harness) – coordinate with QA team.
- **Offline Execution:** Determine behaviour when MCP tool dependencies are unavailable; consider queueing or graceful degradation.
- **Policy Engine Integration:** Evaluate embedding Open Policy Agent or similar for dynamic guardrails rather than hard-coded checks.

---
Author: AMI Orchestrator Docs Team  
Status: Draft (seeking review)  
Last Updated: 2025-09-27
