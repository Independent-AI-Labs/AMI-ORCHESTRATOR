"""
Adapter for the sample worker.
"""

from orchestrator.acp.agent import ACPAgent
from orchestrator.acp.protocol import (
    AIRequest,
    AIResponse,
    TaskCompleted,
    TaskFailed,
    TaskRequest,
    TaskType,
)
from orchestrator.workers.sample_worker import sample_function


class SampleAdapter(ACPAgent):
    """Adapter for the sample worker."""

    def handle_task_request(self, task_request: TaskRequest) -> None:
        """Handle a task request from the orchestrator."""
        if task_request.task_type == TaskType.AI_REQUEST:
            ai_request = AIRequest(**task_request.parameters)
            # Placeholder for actual AI processing for sample worker
            print(f"Sample worker handling AI request: {ai_request.task_type}")
            ai_response = AIResponse(
                status="success", output_data={"message": f"Sample worker processed AI request {ai_request.task_type}."}, confidence_score=0.80
            )
            task_completed = TaskCompleted(task_id=task_request.task_id, result=ai_response)
            self.send_task_completed(task_completed)
        elif task_request.task_type == TaskType.GENERIC_TASK:
            try:
                result = sample_function(**task_request.parameters)
                task_completed = TaskCompleted(task_id=task_request.task_id, result={"greeting": result})
                self.send_task_completed(task_completed)
            except ValueError as e:
                task_failed = TaskFailed(task_id=task_request.task_id, error_message=str(e))
                self.send_task_failed(task_failed)
        else:
            task_failed = TaskFailed(task_id=task_request.task_id, error_message=f"Unknown task type: {task_request.task_type}")
            self.send_task_failed(task_failed)

    def send_task_completed(self, task_completed: TaskCompleted) -> None:
        """Send a task completed message to the orchestrator."""
        # In a real implementation, this would send the message over Redis
        print(f"Task {task_completed.task_id} completed with result: {task_completed.result}")

    def send_task_failed(self, task_failed: TaskFailed) -> None:
        """Send a task failed message to the orchestrator."""
        # In a real implementation, this would send the message over Redis
        print(f"Task {task_failed.task_id} failed with error: {task_failed.error_message}")
