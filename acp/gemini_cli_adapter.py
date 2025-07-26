"""
Adapter for the Gemini CLI agent.
"""

from orchestrator.acp.agent import ACPAgent
from orchestrator.acp.protocol import TaskCompleted, TaskFailed, TaskRequest


class GeminiCliAdapter(ACPAgent):
    """Adapter for the Gemini CLI agent."""

    def handle_task_request(self, task_request: TaskRequest) -> None:
        """Handle a task request from the orchestrator."""
        # This is a placeholder for the actual implementation.
        print(f"Handling task request for Gemini CLI: {task_request.task_name}")
        # In a real implementation, this would involve calling the Gemini CLI
        # with the provided parameters and returning the result.
        pass

    def send_task_completed(self, task_completed: TaskCompleted) -> None:
        """Send a task completed message to the orchestrator."""
        # In a real implementation, this would send the message over Redis
        print(
            f"Task {task_completed.task_id} completed with result: {task_completed.result}"
        )

    def send_task_failed(self, task_failed: TaskFailed) -> None:
        """Send a task failed message to the orchestrator."""
        # In a real implementation, this would send the message over Redis
        print(
            f"Task {task_failed.task_id} failed with error: {task_failed.error_message}"
        )
