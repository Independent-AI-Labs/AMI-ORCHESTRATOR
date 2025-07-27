"""
Unit tests for the BpmnEngine class.
"""

import unittest
from unittest.mock import patch

from tests.base_test import BaseTestCase


class TestBpmnEngine(BaseTestCase):
    """Unit tests for the BpmnEngine class."""

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
