# Next Steps for Orchestrator

This document outlines the future improvements and tasks for the `orchestrator` component.

## Testing and Verification

*   **Goal:** Ensure the existing code is robust and reliable before adding more features.
*   **Tasks:**
    *   [x] **Write Unit Tests:** Write unit tests for all existing modules and functions.
    *   [x] **Write Integration Tests:** Write integration tests for the interaction between different components.
    *   [x] **Write End-to-End Tests:** Write end-to-end tests for the main business scenarios.

## Phase 1: Foundational Infrastructure & Security Core

*   **Goal:** Establish a secure, auditable, and persistent foundation.
*   **Tasks:**
    *   [x] Create core directories and files (`orchestrator/core`, `orchestrator/bpmn`, `orchestrator/main.py`).
    *   [x] Implement basic configuration management (`orchestrator/core/config.py`).
    *   [x] **Dgraph Client:** Develop a robust, transactional client for all Dgraph interactions in `orchestrator/core/dgraph_client.py`.
    *   [x] **Redis Client:** Implement a client for Redis Streams in `orchestrator/core/redis_client.py`.
    *   [x] **Dgraph Schema:** Design and implement a comprehensive Dgraph schema for process definitions, instances, tasks, a detailed audit log, and user/role definitions for RBAC.
    *   [x] **Security Kernel:** Implement the core of the security system, including API authentication (e.g., OAuth2) and a basic RBAC framework.
    *   [x] **Initial Orchestrator Service:** Create the basic service in `orchestrator/main.py` that connects to Dgraph and Redis, with secure configuration management for secrets and endpoints.
    *   [x] **Testing:** Write unit and integration tests for all components in this phase.

## Phase 2: Core BPMN Engine & State Machine

*   **Goal:** Implement the fundamental BPMN execution logic.
*   **Tasks:**
    *   [x] **BPMN Process Loader:** Create a service to parse and validate BPMN 2.0 JSON definitions, storing them in Dgraph.
    *   [x] **BPMN Engine Core:** Develop the engine to execute basic BPMN constructs: `startEvent`, `endEvent`, `sequenceFlow`, and `serviceTask`.
    *   [x] **State Persistence:** Ensure every state transition of a process instance or task is atomically persisted to Dgraph along with a corresponding entry in the immutable audit log.
    *   [x] **Testing:** Write unit and integration tests for the BPMN engine and process loader.

## Phase 3: The Agent-Coordinator Protocol (ACP) & First Worker

*   **Goal:** Define the agent communication standard and integrate the first simple worker.
*   **Tasks:**
    *   [x] **ACP Definition:** Formally define and version the ACP, specifying the JSON schemas for all interactions (`register_agent`, `request_task`, `task_completed`, `task_failed`).
    *   [x] **Generic Agent Interface:** Create a Python abstract base class (`ACPAgent`) that defines the standard methods all agent adapters must implement.
    *   [x] **Worker Manager:** Implement the service for managing the agent lifecycle (registration, health checks, capability discovery).
    *   [x] **First Adapter:** Implement a simple adapter for a basic Python function worker, proving the end-to-end flow from a `serviceTask` in BPMN to a worker and back.
    *   [x] **Testing:** Write unit and integration tests for the ACP, worker manager, and sample adapter.

## Phase 4: Advanced Business Logic & Human-in-the-Loop

*   **Goal:** Enable complex business rules and human interaction.
*   **Tasks:**
    *   [x] **BPMN Gateways:** Implement support for `exclusiveGateway` (if/else) and `parallelGateway` (fork/join) to enable complex routing.
    *   [x] **Human Task Integration:** Add support for the `humanTask` BPMN element. This includes creating tasks that are assigned to users/roles and pausing the workflow until a human provides input via an API or UI.
    *   [x] **Timers and Events:** Implement `timerEvent` (for delays, timeouts, and escalations) and `messageEvent` (for inter-process communication).
    *   [x] **RBAC Enforcement:** Fully integrate the RBAC model, ensuring that human tasks can only be actioned by authorized users.
    *   [x] **Testing:** Write unit and integration tests for all new BPMN elements and the RBAC enforcement.

## Phase 5: Intelligent Agents & Dynamic Process Execution

*   **Goal:** Infuse the orchestrator with AI-driven decision-making capabilities.
*   **Tasks:**
    *   [x] **Gemini CLI Adapter:** Develop a sophisticated adapter for the `gemini-cli` agent, exposing its capabilities (code analysis, refactoring, etc.) as addressable tools within the ACP.
    *   [x] **Dynamic Routing:** Enhance the `exclusiveGateway` to make routing decisions based on the data returned by an AI agent.
    *   [x] **Content-Based Correlation:** Implement the ability to correlate events and messages based on their content, allowing for highly dynamic and adaptive workflows.
    *   [x] **Testing:** Write unit and integration tests for the Gemini CLI adapter and the dynamic routing logic.

## Phase 6: Enterprise Readiness, Scalability & Compliance

*   **Goal:** Prepare the system for production deployment in mission-critical environments.
*   **Tasks:**
    *   [x] **Containerization & Orchestration:** Package all components as Docker containers and create Helm charts for Kubernetes deployment.
    *   [x] **High Availability:** Configure active-active or active-passive setups for all core components.
    *   [x] **Dead-Letter & Escalation Queues:** Implement robust error handling, automatically routing failed tasks to a DLQ for analysis and triggering human escalation workflows when necessary.
    *   [x] **Comprehensive Monitoring:** Integrate with Prometheus and Grafana to create dashboards for monitoring system health, process throughput, and agent performance.
    *   [x] **Compliance Reporting:** Build tools to easily query and export the audit log to satisfy compliance and reporting requirements.
    *   [x] **Testing:** Write end-to-end tests for the entire system, including the containerized deployment.
