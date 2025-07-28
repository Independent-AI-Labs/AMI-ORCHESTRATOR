"""
Integration tests for the BpmnEngine class.
"""

import unittest
from pathlib import Path

from tests.base_test import BaseTestCase


class TestBpmnEngineIntegration(BaseTestCase):
    """Integration tests for the BpmnEngine class."""

    def test_start_process(self):
        """Test the start_process method."""

        project_root = Path(__file__).resolve().parents[3]
        process_definition_path = project_root / "orchestrator" / "bpmn" / "definitions" / "sample_process.json"
        self.bpmn_engine.start_process(str(process_definition_path), "admin")


if __name__ == "__main__":
    unittest.main()
