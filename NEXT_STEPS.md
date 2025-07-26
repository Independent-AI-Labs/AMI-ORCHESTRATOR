# Next Steps

## Next Development Tasks (Phase 1 & 2 Completion)

- **Dgraph Persistence:** Fully implement `create_process_instance` and `create_human_task` in `orchestrator/core/dgraph_client.py` to ensure proper process and human task persistence.
- **Process Definition Storage:** Implement `store_process_definition` in `orchestrator/bpmn/process_loader.py` to persistently store BPMN definitions in Dgraph.
- **Security Implementation:** Complete the `SecurityManager` implementation, including robust authorization logic.
- **Worker Integration:** Modify `_handle_service_task` in `orchestrator/bpmn/engine.py` to send `TaskRequest` messages to appropriate workers (e.g., `sample_worker`, `gemini_cli_adapter`) via Redis. Implement a mechanism to receive `TaskCompleted` or `TaskFailed` messages from workers and update the process state accordingly.
- **Robust Expression Language:** Replace the simplified `evaluate_condition` and `evaluate_expression` in `orchestrator/bpmn/engine.py` with a proper expression language.
- **Real-time Process Status:** Implement the actual logic for the `/api/processes/instances/<process_instance_id>` endpoint in `orchestrator/api.py` to fetch real-time process status from Dgraph.
- **Comprehensive Testing:** Add comprehensive unit and integration tests for the Dgraph persistence, worker communication, and security components.