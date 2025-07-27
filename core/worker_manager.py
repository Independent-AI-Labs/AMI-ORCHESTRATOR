"""
Worker Manager for the Orchestrator.
"""

import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from orchestrator.bpmn.models import Resource, TaskResourceMetrics
from orchestrator.core.redis_client import RedisClient


class WorkerManager:
    """Manages the lifecycle of workers and agents."""

    def __init__(self, redis_client: RedisClient):
        """Initialize the worker manager."""
        self.redis_client = redis_client
        self.workers: dict[str, dict] = {}
        self.resource_pools: dict[Resource, list[str]] = {resource: [] for resource in Resource}
        self._thread_pools: dict[Resource, ThreadPoolExecutor] = defaultdict(lambda: ThreadPoolExecutor(max_workers=os.cpu_count()))
        self._process_pools: dict[Resource, ProcessPoolExecutor] = defaultdict(lambda: ProcessPoolExecutor(max_workers=os.cpu_count()))

    def register_worker(self, worker_id: str, capabilities: list, resource_capabilities: list[Resource] | None = None):
        """Register a new worker."""
        if resource_capabilities is None:
            resource_capabilities = [Resource.GENERIC]

        self.workers[worker_id] = {"capabilities": capabilities, "resource_capabilities": resource_capabilities}
        for resource in resource_capabilities:
            self.resource_pools[resource].append(worker_id)
        print(f"Worker {worker_id} registered with capabilities: {capabilities} and resources: {resource_capabilities}")

    def get_thread_pool(self, resource: Resource) -> ThreadPoolExecutor:
        """Get the thread pool for a given resource."""
        return self._thread_pools[resource]

    def get_process_pool(self, resource: Resource) -> ProcessPoolExecutor:
        """Get the process pool for a given resource."""
        return self._process_pools[resource]

    def shutdown_pools(self):
        """Shutdown all thread and process pools."""
        for pool in self._thread_pools.values():
            pool.shutdown(wait=True)
        for pool in self._process_pools.values():
            pool.shutdown(wait=True)

    def get_workers(self):
        """Get the list of registered workers."""
        return self.workers

    def allocate_resources(self, estimated_resources: TaskResourceMetrics) -> bool:
        """Conceptual: Allocate resources based on estimated requirements."""
        # This would involve checking available resources and making allocation decisions.
        print(f"Attempting to allocate resources: {estimated_resources.usage.cpu_hours} CPU hours")
        # For now, always succeed.
        return True

    def update_resource_metrics(self, worker_id: str, actual_resources: TaskResourceMetrics):
        """Conceptual: Update resource usage and cost metrics for a completed task."""
        cost_str = f", cost: {actual_resources.cost.monetary_cost}" if actual_resources.cost else ""
        print(f"Worker {worker_id} reported actual resource usage: {actual_resources.usage.cpu_hours} CPU hours{cost_str}")
        # In a real system, this would update a persistent store or monitoring system.
