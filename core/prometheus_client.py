"""
Prometheus client for the Orchestrator.
"""

from prometheus_client import Counter, start_http_server

from orchestrator.core.config import Config


class PrometheusClient:
    """Prometheus client for the Orchestrator."""

    def __init__(self):
        """Initialize the Prometheus client."""
        self.port = Config.PROMETHEUS_PORT
        self.process_starts = Counter(
            "process_starts", "Total number of started processes"
        )
        self.process_failures = Counter(
            "process_failures", "Total number of failed processes"
        )

    def start_server(self):
        """Start the Prometheus HTTP server."""
        start_http_server(self.port)
        print(f"Prometheus server started on port {self.port}")

    def increment_process_starts(self):
        """Increment the process starts counter."""
        self.process_starts.inc()

    def increment_process_failures(self):
        """Increment the process failures counter."""
        self.process_failures.inc()
