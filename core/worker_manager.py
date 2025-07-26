"""
Worker Manager for the Orchestrator.
"""

from orchestrator.core.redis_client import RedisClient


class WorkerManager:
    """Manages the lifecycle of workers and agents."""

    def __init__(self, redis_client: RedisClient):
        """Initialize the worker manager."""
        self.redis_client = redis_client
        self.workers: dict[str, dict] = {}

    def register_worker(self, worker_id: str, capabilities: list):
        """Register a new worker."""
        self.workers[worker_id] = {"capabilities": capabilities}
        print(f"Worker {worker_id} registered with capabilities: {capabilities}")

    def get_workers(self):
        """Get the list of registered workers."""
        return self.workers
