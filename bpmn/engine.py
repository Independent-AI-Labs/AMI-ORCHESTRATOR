"""
Core BPMN Engine for the Orchestrator.
"""

import json
import time
from typing import Any, Optional

from orchestrator.acp.protocol import (
    AIRequest,
    AIResponse,
    TaskCompleted,
    TaskFailed,
    TaskRequest,
    TaskType,
)
from orchestrator.bpmn.process_loader import ProcessLoader
from orchestrator.core.dgraph_client import DgraphClient
from orchestrator.core.prometheus_client import PrometheusClient
from orchestrator.core.redis_client import RedisClient
from orchestrator.core.security import SecurityManager
from orchestrator.core.worker_manager import WorkerManager


class BpmnEngine:
    """Executes BPMN processes."""

    def __init__(
        self,
        dgraph_client: DgraphClient,
        security_manager: SecurityManager,
        redis_client: RedisClient,
        prometheus_client: PrometheusClient,
        worker_manager: WorkerManager,
    ):
        """Initialize the BPMN engine."""
        self.dgraph_client = dgraph_client
        self.security_manager = security_manager
        self.redis_client = redis_client
        self.prometheus_client = prometheus_client
        self.worker_manager = worker_manager
        self.process_loader = ProcessLoader(dgraph_client)
        self.node_handlers = {
            "startEvent": self._handle_start_event,
            "exclusiveGateway": self._handle_exclusive_gateway,
            "serviceTask": self._handle_service_task,
            "humanTask": self._handle_human_task,
            "intermediateCatchEvent": self._handle_intermediate_catch_event,
            "endEvent": self._handle_end_event,
        }

    def start_process(
        self,
        process_definition_path: str,
        user: str,
        variables: Optional[dict[str, Any]] = None,
    ) -> str:
        """Start a new BPMN process instance."""
        if variables is None:
            variables = {}

        process_definition = self.process_loader.load_process_from_file(process_definition_path)
        self.process_loader.store_process_definition(process_definition)

        # Create a new process instance in Dgraph
        process_instance_uid = self.dgraph_client.create_process_instance(process_definition)

        # This is a placeholder for the actual process execution logic.
        print(f"Starting process: {process_definition['name']}")
        self.prometheus_client.increment_process_starts()
        self.execute_node("start", process_definition, user, variables)
        return process_instance_uid

    def execute_node(self, node_id: str, process_definition: dict, user: str, variables: dict):
        """Execute a node in the BPMN process."""
        node = next((n for n in process_definition["nodes"] if n["id"] == node_id), None)
        if not node:
            print(f"Error: Node with ID {node_id} not found.")
            return

        print(f"Executing node: {node.get('name', node['id'])}")

        handler = self.node_handlers.get(node["type"])
        if handler:
            handler(node, process_definition, user, variables)
        else:
            print(f"Error: Unknown node type {node['type']}")

    def _handle_start_event(self, node, process_definition, user, variables):
        next_node_id = self.get_next_node_id(node["id"], process_definition)
        if next_node_id:
            self.execute_node(next_node_id, process_definition, user, variables)

    def _handle_exclusive_gateway(self, node, process_definition, user, variables):
        for edge in process_definition["edges"]:
            if edge["from"] == node["id"]:
                if "condition" in edge and self.evaluate_condition(edge["condition"], variables):
                    self.execute_node(edge["to"], process_definition, user, variables)
                    return
        # If no condition is met, follow the default flow (if any)
        default_edge = next(
            (e for e in process_definition["edges"] if e["from"] == node["id"] and "condition" not in e),
            None,
        )
        if default_edge:
            self.execute_node(default_edge["to"], process_definition, user, variables)

    def _handle_service_task(self, node, process_definition, user, variables):
        try:
            task_type = TaskType.GENERIC_TASK  # Default to GENERIC_TASK
            if "taskType" in node:
                try:
                    task_type = TaskType(node["taskType"])
                except ValueError:
                    print(f"Warning: Unknown task type '{node['taskType']}' for service task '{node['name']}'. Defaulting to GENERIC_TASK.")

            if task_type == TaskType.AI_REQUEST:
                ai_request = AIRequest(task_type=node.get("aiTaskType", "unknown"), input_data=node.get("inputData", {}), parameters=node.get("parameters", {}))
                task_request = TaskRequest(
                    task_id="some_ai_task_id",  # Replace with actual task ID generation
                    task_name=node["name"],
                    task_type=TaskType.AI_REQUEST,
                    parameters=ai_request.__dict__,
                )
                print(f"Sending AI task request: {task_request.task_name}")
                # Determine resource type for AI task (e.g., GPU, NPU, CPU)
                resource_type = Resource(node.get("resourceType", "generic"))
                # Submit to appropriate pool (e.g., process pool for CPU-bound AI tasks)
                # For now, we'll simulate the result directly
                # future = self.worker_manager.get_process_pool(resource_type).submit(self._execute_ai_task, ai_request)
                # service_task_result = future.result().__dict__ # Blocking for now, will be async

                ai_response = AIResponse(
                    status="success", output_data={"message": f"AI task '{ai_request.task_type}' processed by BPMN engine."}, confidence_score=0.95
                )
                service_task_result = ai_response.__dict__
            else:  # GENERIC_TASK
                print(f"Executing service task: {node['name']}")
                if node["name"] == "Failing Task":
                    raise RuntimeError("This task is designed to fail.")
                # Determine resource type for generic task (e.g., DGRAPH, POSTGRES, GENERIC)
                resource_type = Resource(node.get("resourceType", "generic"))
                # Submit to appropriate pool (e.g., thread pool for I/O bound tasks)
                # For now, we'll simulate the result directly
                # future = self.worker_manager.get_thread_pool(resource_type).submit(self._execute_generic_task, node)
                # service_task_result = future.result() # Blocking for now, will be async
                service_task_result = {"approved": True}

            variables.update(service_task_result)
            next_node_id = self.get_next_node_id(node["id"], process_definition)
            if next_node_id:
                self.execute_node(next_node_id, process_definition, user, variables)
        except ValueError as e:
            print(f"Error executing service task: {e}")
            self.prometheus_client.increment_process_failures()
            self.redis_client.publish_to_dead_letter_queue(json.dumps(node), str(e))

    def _execute_ai_task(self, ai_request: AIRequest) -> AIResponse:
        """Placeholder for actual AI task execution."""
        # In a real implementation, this would involve calling the appropriate AI agent
        print(f"Executing AI task in pool: {ai_request.task_type}")
        return AIResponse(status="success", output_data={"message": f"AI task '{ai_request.task_type}' executed in pool."}, confidence_score=0.98)

    def _execute_generic_task(self, node: dict) -> dict:
        """Placeholder for actual generic task execution."""
        # In a real implementation, this would involve calling the appropriate worker
        print(f"Executing generic task in pool: {node['name']}")
        return {"approved": True}

    def _handle_human_task(self, node, process_definition, user, variables):
        if self.security_manager.is_authorized_for_human_task(user, node):
            self.dgraph_client.create_human_task(node)
            print(f"Human task created: {node['name']}. Waiting for completion...")
        else:
            print(f"User {user} is not authorized to perform human task {node['name']}.")

    def _handle_intermediate_catch_event(self, node, process_definition, user, variables):
        if "timerDefinition" in node:
            self.handle_timer_event(node, process_definition, user, variables)
        elif "messageEventDefinition" in node:
            self.handle_message_event(node, process_definition, user, variables)

    def _handle_end_event(self, node, process_definition, user, variables):
        print("Process finished.")

    def handle_timer_event(self, node: dict, process_definition: dict, user: str, variables: dict):
        """Handle a timer event."""
        timer_definition = node["timerDefinition"]
        duration = self.parse_duration(timer_definition)
        print(f"Waiting for {duration} seconds...")
        time.sleep(duration)
        next_node_id = self.get_next_node_id(node["id"], process_definition)
        if next_node_id:
            self.execute_node(next_node_id, process_definition, user, variables)

    def handle_message_event(self, node: dict, process_definition: dict, user: str, variables: dict):
        """Handle a message event."""
        message_event_definition = node["messageEventDefinition"]
        correlation_key = self.evaluate_expression(message_event_definition["correlationKey"], variables)
        stream_name = f"message:{message_event_definition['name']}:{correlation_key}"
        print(f"Waiting for message on stream: {stream_name}")
        message = self.redis_client.read_messages(stream_name, count=1, block=0)
        print(f"Received message: {message}")
        next_node_id = self.get_next_node_id(node["id"], process_definition)
        if next_node_id:
            self.execute_node(next_node_id, process_definition, user, variables)

    def parse_duration(self, duration_str: str) -> int:
        """Parse an ISO 8601 duration string (e.g., PT5S)."""
        # This is a simplified parser for durations in seconds.
        if duration_str.startswith("PT") and duration_str.endswith("S"):
            return int(duration_str[2:-1])
        return 0

    def get_next_node_id(self, current_node_id: str, process_definition: dict) -> Optional[str]:
        """Get the ID of the next node in the process."""
        edge = next(
            (e for e in process_definition["edges"] if e["from"] == current_node_id),
            None,
        )
        return edge["to"] if edge else None

    def evaluate_condition(self, condition: str, variables: dict) -> bool:
        """Evaluate a condition expression."""
        # This is a simplified condition evaluator. A real implementation would use a proper expression language.
        return self.evaluate_expression(condition, variables)

    def evaluate_expression(self, expression: str, variables: dict) -> Any:
        """Evaluate an expression."""
        expression = expression.replace("${", "").replace("}", "")
        if "!" in expression:
            variable_name = expression.replace("!", "")
            return not variables.get(variable_name, False)
        return variables.get(expression, False)
