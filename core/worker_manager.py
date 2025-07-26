"""
Worker Manager for the Orchestrator.
"""
import multiprocessing
import threading
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from orchestrator.acp.protocol import Resource
from orchestrator.core.redis_client import RedisClient


class WorkerManager:
    """Manages the lifecycle of workers and agents."""

    def __init__(self, redis_client: RedisClient):
        """Initialize the worker manager."""
        self.redis_client = redis_client
        self.workers: dict[str, dict] = {}
        self.resource_pools: dict[Resource, list[str]] = {resource: [] for resource in Resource}
        self._thread_pools: dict[Resource, ThreadPoolExecutor] = defaultdict(lambda: ThreadPoolExecutor(max_workers=threading.cpu_count()))
        self._process_pools: dict[Resource, ProcessPoolExecutor] = defaultdict(lambda: ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()))

    def register_worker(self, worker_id: str, capabilities: list, resource_capabilities: list[Resource] = None):
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
