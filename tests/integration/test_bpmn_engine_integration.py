"""
Integration tests for the BpmnEngine class.
"""

import unittest

from orchestrator.bpmn.engine import BpmnEngine
from orchestrator.core.dgraph_client import DgraphClient
from orchestrator.core.prometheus_client import PrometheusClient
from orchestrator.core.redis_client import RedisClient
from orchestrator.core.security import SecurityManager


class TestBpmnEngineIntegration(unittest.TestCase):
    """Integration tests for the BpmnEngine class."""

    def setUp(self):
        """Set up the test case."""
        self.dgraph_client = DgraphClient()
        self.redis_client = RedisClient()
        self.security_manager = SecurityManager()
        self.prometheus_client = PrometheusClient()
        self.bpmn_engine = BpmnEngine(
            self.dgraph_client,
            self.security_manager,
            self.redis_client,
            self.prometheus_client,
        )

    def test_start_process(self):
        """Test the start_process method."""
        self.bpmn_engine.start_process(
            "orchestrator/bpmn/definitions/sample_process.json", "admin"
        )


if __name__ == "__main__":
    unittest.main()
