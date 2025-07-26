# Next Steps

## Current Status & Completed Tasks

*   **Formalized AI Agent Interface & Data Exchange:** Defined `AIRequest`, `AIResponse`, `TaskType`, and `Resource` enums in `orchestrator/acp/protocol.py`. Updated `TaskRequest` and `TaskCompleted` to support AI-specific data.
*   **Enhanced Worker Manager for Parallelization:** Implemented `WorkerManager` in `orchestrator/core/worker_manager.py` with support for process and thread-pool based parallelization, and grouping/per I/O resource worker pools.
*   **Gemini CLI Integration:** Aligned the orchestrator's `/acp` integration with the Gemini CLI's `--experimental-acp` feature, including updates to `orchestrator/acp/protocol.py`, `orchestrator/acp/gemini_acp_protocol.py`, `orchestrator/acp/gemini_cli_adapter.py`, `orchestrator/acp/sample_adapter.py`, and `orchestrator/acp/agent.py`. Added comprehensive unit tests for the `GeminiCliAdapter` in `orchestrator/tests/acp/test_gemini_cli_adapter.py` to ensure correct JSON-RPC communication and proper cleanup of subprocesses and threads.
*   **BPMN Engine Integration with Worker Pools:** Modified `orchestrator/bpmn/engine.py` to integrate with the `WorkerManager`, allowing service tasks to specify `taskType` and `resourceType` for potential execution in dedicated pools.
*   **API Integration:** Updated `orchestrator/api.py` to correctly instantiate and pass the `WorkerManager` to the `BpmnEngine`.
*   **Test Updates:** Updated unit and integration tests (`orchestrator/tests/bpmn/test_bpmn_engine.py`, `orchestrator/tests/integration/test_bpmn_engine_integration.py`) to accommodate the `WorkerManager` dependency.

## Next Development Tasks

### Core Functionality

*   **Dgraph Persistence:** Fully implement `create_process_instance` and `create_human_task` in `orchestrator/core/dgraph_client.py` to ensure proper process and human task persistence.
*   **Process Definition Storage:** Implement `store_process_definition` in `orchestrator/bpmn/process_loader.py` to persistently store BPMN definitions in Dgraph.
*   **Security Implementation:** Complete the `SecurityManager` implementation, including robust authentication and authorization logic.
*   **Full Worker Integration & Asynchronous Execution:**
    *   Modify `_handle_service_task` in `orchestrator/bpmn/engine.py` to *actually* submit `TaskRequest` messages to appropriate workers (e.g., `sample_worker`, `gemini_cli_adapter`) via Redis or directly to the `WorkerManager`'s pools.
    *   Implement a mechanism to asynchronously receive `TaskCompleted` or `TaskFailed` messages from workers and update the process state accordingly. This will likely involve callbacks or a dedicated result handling component.
    *   Replace current simulated results in `_handle_service_task`, `_execute_ai_task`, and `_execute_generic_task` with actual calls to worker pools.
*   **Robust Expression Language:** Replace the simplified `evaluate_condition` and `evaluate_expression` in `orchestrator/bpmn/engine.py` with a proper expression language for complex conditional logic.
*   **Real-time Process Status:** Implement the actual logic for the `/api/processes/instances/<process_instance_id>` endpoint in `orchestrator/api.py` to fetch real-time process status from Dgraph.

### Testing & Validation

*   **Comprehensive Unit Tests:**
    *   Add dedicated unit tests for `WorkerManager` to cover pool creation, task submission, and shutdown.
    *   Expand unit tests for `BpmnEngine` to thoroughly test the new `taskType` and `resourceType` handling within `_handle_service_task`, including scenarios for AI and generic tasks.
    *   Ensure comprehensive test coverage for `orchestrator/acp/protocol.py` (dataclasses, enums).
*   **Integration Tests:**
    *   Develop integration tests that simulate end-to-end task execution using the `WorkerManager`'s pools and actual worker adapters (even if simplified).
    *   Test the interaction between `BpmnEngine`, `WorkerManager`, and the Redis message queue for task distribution and result handling.
*   **End-to-End (E2E) Tests:**
    *   Create E2E tests that define BPMN processes utilizing both AI and generic service tasks, verifying their execution through the new parallelization mechanisms.
    *   Test various resource types (e.g., `GPU`, `DGRAPH`) to ensure tasks are routed to the correct pools.

### Future Enhancements

*   **Dynamic Resource Allocation:** Implement more sophisticated logic for dynamic allocation of tasks to worker pools based on real-time load and resource availability.
*   **Fault Tolerance for Worker Pools:** Enhance error handling and recovery mechanisms for tasks executed within thread and process pools.
*   **Monitoring & Observability:** Integrate metrics and logging for worker pool utilization, task queue lengths, and task execution times.

## Development Guidelines Reminder

As outlined in `orchestrator/GEMINI.md`, all development should adhere to the following principles:

1.  **Plan and Confirm:** Thoroughly plan the approach, identify affected files, understand existing patterns, and consider potential impacts. Confirm the plan with relevant stakeholders or by performing self-verification steps.
2.  **Create/Update Tests:** Write tests that validate new functionality *before* writing new code.
3.  **Implement Feature (Atomic Changes):** Focus on small, self-contained, atomic changes.
4.  **Run All Tests (Frequent Validation):** Validate frequently after each atomic change, and run the entire test suite before submitting.
5.  **Update Documentation:** Keep all relevant documentation up-to-date.
