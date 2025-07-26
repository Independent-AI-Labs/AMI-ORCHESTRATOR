"""
Adapter for the sample worker.
"""

from orchestrator.acp.agent import ACPAgent
from orchestrator.acp.protocol import TaskCompleted, TaskFailed, TaskRequest
from orchestrator.workers.sample_worker import sample_function


class SampleAdapter(ACPAgent):
    """Adapter for the sample worker."""

    def handle_task_request(self, task_request: TaskRequest) -> None:
        """Handle a task request from the orchestrator."""
        try:
            result = sample_function(**task_request.parameters)
            task_completed = TaskCompleted(task_id=task_request.task_id, result={"greeting": result})
            self.send_task_completed(task_completed)
        except ValueError as e:
            task_failed = TaskFailed(task_id=task_request.task_id, error_message=str(e))
            self.send_task_failed(task_failed)

    def send_task_completed(self, task_completed: TaskCompleted) -> None:
        """Send a task completed message to the orchestrator."""
        # In a real implementation, this would send the message over Redis
        print(f"Task {task_completed.task_id} completed with result: {task_completed.result}")

    def send_task_failed(self, task_failed: TaskFailed) -> None:
        """Send a task failed message to the orchestrator."""
        # In a real implementation, this would send the message over Redis
        print(f"Task {task_failed.task_id} failed with error: {task_failed.error_message}")
