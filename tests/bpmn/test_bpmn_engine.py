"""
Unit tests for the BpmnEngine class.
"""

import unittest
from unittest.mock import MagicMock, patch

from orchestrator.bpmn.engine import BpmnEngine
from orchestrator.core.dgraph_client import DgraphClient
from orchestrator.core.prometheus_client import PrometheusClient
from orchestrator.core.redis_client import RedisClient
from orchestrator.core.security import SecurityManager


class TestBpmnEngine(unittest.TestCase):
    """Unit tests for the BpmnEngine class."""

    def setUp(self):
        """Set up the test case."""
        self.dgraph_client = MagicMock(spec=DgraphClient)
        self.redis_client = MagicMock(spec=RedisClient)
        self.security_manager = MagicMock(spec=SecurityManager)
        self.prometheus_client = MagicMock(spec=PrometheusClient)
        self.bpmn_engine = BpmnEngine(
            self.dgraph_client,
            self.security_manager,
            self.redis_client,
            self.prometheus_client,
        )

    @patch("builtins.open")
    @patch("json.load")
    def test_start_process(self, mock_json_load, mock_open):
        """Test the start_process method."""
        mock_json_load.return_value = {
            "id": "sample_process",
            "name": "Sample Process",
            "nodes": [
                {"id": "start", "type": "startEvent"},
                {"id": "end", "type": "endEvent"},
            ],
            "edges": [{"from": "start", "to": "end"}],
        }
        self.bpmn_engine.start_process("path/to/process.json", "admin")
        self.dgraph_client.create_process_instance.assert_called_once()


if __name__ == "__main__":
    unittest.main()
