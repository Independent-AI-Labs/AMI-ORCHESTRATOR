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


import os


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

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        process_definition_path = os.path.join(project_root, "orchestrator", "bpmn", "definitions", "sample_process.json")
        self.bpmn_engine.start_process(process_definition_path, "admin")


if __name__ == "__main__":
    unittest.main()
