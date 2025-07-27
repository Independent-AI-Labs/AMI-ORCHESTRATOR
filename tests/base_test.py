"""
Base test case for the orchestrator.
"""

import unittest
from unittest.mock import MagicMock

from orchestrator.bpmn.engine import BpmnEngine
from orchestrator.core.dgraph_client import DgraphClient
from orchestrator.core.prometheus_client import PrometheusClient
from orchestrator.core.redis_client import RedisClient
from orchestrator.core.security import SecurityManager
from orchestrator.core.worker_manager import WorkerManager


class BaseTestCase(unittest.TestCase):
    """Base class for test cases."""

    def setUp(self):
        """Set up the test case."""
        self.dgraph_client = MagicMock(spec=DgraphClient)
        self.redis_client = MagicMock(spec=RedisClient)
        self.security_manager = MagicMock(spec=SecurityManager)
        self.prometheus_client = MagicMock(spec=PrometheusClient)
        self.worker_manager = MagicMock(spec=WorkerManager)
        self.bpmn_engine = BpmnEngine(
            self.dgraph_client,
            self.security_manager,
            self.redis_client,
            self.prometheus_client,
            self.worker_manager,
        )
