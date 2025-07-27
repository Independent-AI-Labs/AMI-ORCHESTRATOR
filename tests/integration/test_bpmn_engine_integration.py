"""
Integration tests for the BpmnEngine class.
"""

import os
import unittest

from tests.base_test import BaseTestCase


class TestBpmnEngineIntegration(BaseTestCase):
    """Integration tests for the BpmnEngine class."""

    def test_start_process(self):
        """Test the start_process method."""

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        process_definition_path = os.path.join(project_root, "orchestrator", "bpmn", "definitions", "sample_process.json")
        self.bpmn_engine.start_process(process_definition_path, "admin")


if __name__ == "__main__":
    unittest.main()
