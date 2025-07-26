# Development Plan: OpenAMI Orchestrator - The Intelligent Process Automation Engine

## 1. Vision: The Core of OpenAMI

Its purpose is to serve as a multi-purpose, enterprise-grade reasoning engine. It is designed to model, execute, and monitor complex business processes in a manner that is robust, compliant, scalable, and intelligent. By leveraging industry standards like BPMN 2.0 and a graph-based architecture, the Orchestrator provides a transparent and auditable platform for automating even the most dynamic and long-running business scenarios.

### Core Principles:

- **Auditability & Compliance:** Every action, decision, and state change is immutably logged, creating a comprehensive audit trail that can be used to meet strict compliance requirements.
- **Resilience & Fault Tolerance:** The system is designed to be highly available and to gracefully handle failures, with built-in mechanisms for retries, rollbacks, and human-in-the-loop escalations.
- **Scalability & Performance:** The architecture is horizontally scalable by design, allowing for the independent scaling of all components to meet any workload demand.
- **Extensibility & Interoperability:** A standardized Agent-Coordinator Protocol (ACP) allows for the seamless integration of any service, from internal microservices and legacy systems to third-party APIs and advanced AI models.
- **Intelligence & Adaptability:** The Orchestrator is more than a static workflow engine; it is a reasoning engine that can use AI to make decisions, adapt processes in real-time, and automate complex, non-deterministic tasks.

## 2. Architectural Blueprint

The OpenAMI Orchestrator is built on a decoupled, event-driven architecture that ensures scalability and resilience.

```mermaid
graph TD
    subgraph "Interfaces & APIs"
        A[REST API] -- Requests --> B
        B[BPMN Process Controller]
        U[Admin & Monitoring UI]
    end

    subgraph "Orchestrator Core"
        B -- Commands --> C{Event Bus: Redis Streams}
        D[BPMN Engine] -- Consumes & Publishes --> C
        E[Worker & Agent Manager] -- Manages --> F((Agent Fleet (via ACP)))
        E -- Consumes & Publishes --> C
        G[State & Audit Controller] -- Writes --> H
    end

    subgraph "State & Data Plane"
        H[(Dgraph: Process State & Audit Log)]
    end

    subgraph "Agent Ecosystem (via ACP)"
        F -- Consumes & Publishes --> C
        F -- Adapters --> I[Gemini AI Agent]
        F -- Adapters --> J[Local Files Worker]
        F -- Adapters --> K[Internal API Worker]
        F -- Adapters --> L[Human Task Manager]
    end

    D -- Reads/Writes State --> G
    U -- Reads State --> G

    style H fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style C fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    style F fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
```

## 3. Phased Development Plan

This plan breaks down the development into logical phases, starting with a solid foundation and progressively adding more advanced capabilities.

### Phase 1: Foundational Infrastructure & Security Core (In Progress)

*   **Goal:** Establish a secure, auditable, and persistent foundation.
*   **Current Status:**
    *   Dgraph Client: Basic client implemented, but `create_process_instance` and `create_human_task` are placeholders.
    *   Redis Setup: Client implemented for messaging and dead-letter queue.
    *   Security Kernel: `SecurityManager` exists, but authorization logic (e.g., `is_authorized_for_human_task`) is not fully implemented.
    *   Initial Orchestrator Service: Flask API is set up.
    *   Testing: Unit, integration, and E2E tests are passing.
*   **Tasks to Complete:**
    1.  **Dgraph Persistence:** Fully implement `create_process_instance` and `create_human_task` in `DgraphClient` to ensure proper process and human task persistence.
    2.  **Process Definition Storage:** Implement `store_process_definition` in `ProcessLoader` to persistently store BPMN definitions in Dgraph.
    3.  **Security Implementation:** Complete the `SecurityManager` implementation, including robust authorization logic.
    4.  **Testing:** Write comprehensive unit and integration tests for all components in this phase.

### Phase 2: Core BPMN Engine & State Machine (In Progress)

*   **Goal:** Implement the fundamental BPMN execution logic and integrate with workers.
*   **Current Status:**
    *   BPMN Process Loader: Loads definitions from JSON files.
    *   BPMN Engine Core: Handlers for `startEvent`, `exclusiveGateway`, `serviceTask`, `humanTask`, `intermediateCatchEvent` (timer and message events), and `endEvent` are present.
    *   State Persistence: Placeholder calls to Dgraph client exist.
    *   Service Task Execution: Currently simulated; actual worker integration is pending.
    *   Expression Evaluation: Simplified evaluators are in place.
    *   Testing: Unit, integration, and E2E tests are passing.
*   **Tasks to Complete:**
    1.  **Worker Integration:** Modify `_handle_service_task` to send `TaskRequest` messages to appropriate workers (e.g., `sample_worker`, `gemini_cli_adapter`) via Redis. Implement a mechanism to receive `TaskCompleted` or `TaskFailed` messages from workers and update the process state accordingly.
    2.  **Robust Expression Language:** Replace the simplified `evaluate_condition` and `evaluate_expression` with a proper expression language.
    3.  **Real-time Process Status:** Implement the actual logic for the `/api/processes/instances/<process_instance_id>` endpoint in `api.py` to fetch real-time process status from Dgraph.
    4.  **Testing:** Write comprehensive unit and integration tests for the BPMN engine, process loader, and worker integration.

### Phase 3: The Agent-Coordinator Protocol (ACP) & First Worker (Planned)

*   **Goal:** Define the agent communication standard and integrate the first simple worker.
*   **Current Status:** ACP definition (`acp/protocol.py`) is complete. A `sample_worker.py` exists.
*   **Tasks:**
    1.  **Generic Agent Interface:** Create a Python abstract base class (`ACPAgent`) that defines the standard methods all agent adapters must implement.
    2.  **Worker Manager Enhancements:** Enhance the `WorkerManager` to handle agent registration, health checks, and capability discovery via ACP.
    3.  **First Adapter:** Implement a simple adapter for a basic Python function worker, proving the end-to-end flow from a `serviceTask` in BPMN to a worker and back.
    4.  **Testing:** Write unit and integration tests for the ACP, worker manager, and sample adapter.

### Phase 4: Advanced Business Logic & Human-in-the-Loop (Planned)

*   **Goal:** Enable complex business rules and human interaction.
*   **Tasks:**
    1.  **BPMN Gateways:** Implement support for `exclusiveGateway` (if/else) and `parallelGateway` (fork/join) to enable complex routing.
    2.  **Human Task Integration:** Add support for the `humanTask` BPMN element. This includes creating tasks that are assigned to users/roles and pausing the workflow until a human provides input via an API or UI.
    3.  **Timers and Events:** Implement `timerEvent` (for delays, timeouts, and escalations) and `messageEvent` (for inter-process communication).
    4.  **RBAC Enforcement:** Fully integrate the RBAC model, ensuring that human tasks can only be actioned by authorized users.
    5.  **Testing:** Write unit and integration tests for all new BPMN elements and the RBAC enforcement.

### Phase 5: Intelligent Agents & Dynamic Process Execution (Planned)

*   **Goal:** Infuse the orchestrator with AI-driven decision-making capabilities.
*   **Current Status:** A placeholder `GeminiCliAdapter` exists.
*   **Tasks:**
    1.  **Gemini CLI Adapter:** Develop a sophisticated adapter for the `gemini-cli` agent, exposing its capabilities (code analysis, refactoring, etc.) as addressable tools within the ACP.
    2.  **Dynamic Routing:** Enhance the `exclusiveGateway` to make routing decisions based on the data returned by an AI agent.
    3.  **Content-Based Correlation:** Implement the ability to correlate events and messages based on their content, allowing for highly dynamic and adaptive workflows.
    4.  **Testing:** Write unit and integration tests for the Gemini CLI adapter and the dynamic routing logic.

### Phase 6: Enterprise Readiness, Scalability & Compliance (Planned)

*   **Goal:** Prepare the system for production deployment in mission-critical environments.
*   **Tasks:**
    1.  **Containerization & Orchestration:** Package all components as Docker containers and create Helm charts for Kubernetes deployment.
    2.  **High Availability:** Configure active-active or active-passive setups for all core components.
    3.  **Dead-Letter & Escalation Queues:** Implement robust error handling, automatically routing failed tasks to a DLQ for analysis and triggering human escalation workflows when necessary.
    4.  **Comprehensive Monitoring:** Integrate with Prometheus and Grafana to create dashboards for monitoring system health, process throughput, and agent performance.
    5.  **Compliance Reporting:** Build tools to easily query and export the audit log to satisfy compliance and reporting requirements.
    6.  **Testing:** Write end-to-end tests for the entire system, including the containerized deployment.

## 4. Security & Compliance by Design

Security and compliance are not afterthoughts; they are core design principles.

-   **Authentication & Authorization:** All API endpoints will be protected by OAuth2/OIDC. Role-Based Access Control (RBAC) will govern all actions, from initiating a process to completing a human task.
-   **Secret Management:** All secrets (API keys, passwords, certificates) will be stored in a secure vault (e.g., HashiCorp Vault, Kubernetes Secrets) and never in code or configuration files.
-   **Immutable Audit Log:** Every event and state change will be cryptographically signed and stored in an append-only log in Dgraph, creating an unbreakable chain of evidence.
-   **Data Encryption:** All data will be encrypted both in transit (TLS) and at rest.

## 5. Testing & Validation Strategy

-   **Unit Tests:** Each module and function will be rigorously unit-tested.
-   **Integration Tests:** Tests will cover the interaction between components, such as the BPMN Engine's interaction with the Dgraph client and the Worker Manager's interaction with the ACP.
-   **End-to-End (E2E) Tests:** These tests will execute complete BPMN process definitions, simulating real-world business scenarios involving multiple agents, gateways, and human tasks.
-   **Chaos Engineering:** In later phases, we will introduce chaos engineering principles to test the system's resilience by deliberately injecting failures (e.g., killing a worker, dropping network packets) and verifying that the system recovers gracefully.

## 6. Technology Stack

-   **Core Language:** Python 3.10+
-   **Process Engine:** Custom BPMN 2.0 engine (Python)
-   **Graph Database:** Dgraph (for process state, audit log, and relationships)
-   **Message Broker:** Redis Streams (for event-driven communication)
-   **Containerization:** Docker
-   **Orchestration:** Kubernetes (with Helm for deployment)
-   **Authentication/Authorization:** OAuth2/OIDC, Custom RBAC implementation
-   **Secret Management:** HashiCorp Vault (or Kubernetes Secrets)
-   **Monitoring & Alerting:** Prometheus, Grafana
-   **Logging:** Structured logging (e.g., ELK stack or similar)
-   **API Framework:** FastAPI (for REST API)
-   **UI Framework:** React/Next.js (for Admin & Monitoring UI)

## 7. Deployment Strategy

-   **Development Environment:** Docker Compose for local development, providing an isolated and reproducible environment with all dependencies (Dgraph, Redis).
-   **Staging Environment:** A Kubernetes cluster mirroring production, used for integration testing, performance tuning, and pre-production validation.
-   **Production Environment:** A highly available Kubernetes cluster, deployed across multiple availability zones/regions for disaster recovery. Automated CI/CD pipelines will handle deployments.
-   **Hybrid Cloud/On-Premise:** Designed to be deployable in various environments, from public cloud (AWS, GCP, Azure) to on-premise data centers, leveraging Kubernetes as the abstraction layer.
-   **Infrastructure as Code (IaC):** Terraform or Pulumi will be used to define and manage the underlying infrastructure for all environments.

## 8. Monitoring & Observability

-   **Metrics:** Comprehensive metrics will be collected from all components (BPMN engine, Dgraph, Redis, agents, adapters) including:
    -   Process instance counts (active, completed, failed)
    -   Task execution times and throughput
    -   Agent availability and performance
    -   Resource utilization (CPU, memory, network I/O) for all containers/pods
    -   Queue lengths and message processing rates for Redis Streams
    -   Database query performance and connection pool statistics
-   **Logging:** Structured logging will be implemented across all components, with logs centralized in a robust logging solution (e.g., ELK stack, Splunk, Datadog). Log levels will be configurable.
-   **Tracing:** Distributed tracing (e.g., OpenTelemetry) will be implemented to provide end-to-end visibility of requests flowing through the system, aiding in debugging and performance optimization.
-   **Alerting:** Critical metrics will have predefined alert thresholds, triggering notifications via PagerDuty, Slack, or email for operational teams.
-   **Dashboards:** Grafana dashboards will provide real-time visualization of all key metrics and system health.
