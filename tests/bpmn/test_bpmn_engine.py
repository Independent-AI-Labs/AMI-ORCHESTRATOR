"""
Unit tests for the BpmnEngine class.
"""

import unittest
from unittest.mock import patch

from orchestrator.tests.base_test import BaseTestCase


class TestBpmnEngine(BaseTestCase):
    """Unit tests for the BpmnEngine class."""

    @patch("pathlib.Path.read_text")
    def test_start_process(self, mock_read_text):
        """Test the start_process method."""
        mock_read_text.return_value = (
            '{"id": "sample_process", "name": "Sample Process", "nodes": ['
            '{"id": "start", "type": "startEvent"}, {"id": "end", "type": "endEvent"}], '
            '"edges": [{"from": "start", "to": "end"}]}'
        )
        self.bpmn_engine.start_process("path/to/process.json", "admin")
        self.dgraph_client.create_process_instance.assert_called_once()


if __name__ == "__main__":
    unittest.main()
