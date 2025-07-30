"""
End-to-end tests for the sample process.
"""

import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestSampleProcessE2E(unittest.TestCase):
    """End-to-end tests for the sample process."""

    def setUp(self):
        """Set up the test case."""
        env = os.environ.copy()
        project_root = Path(__file__).resolve().parents[2]
        env["PYTHONPATH"] = str(project_root)
        python_executable = sys.executable
        self.orchestrator_process = subprocess.Popen([python_executable, "-m", "orchestrator.main"], env=env)  # noqa: S603, S607 # python_executable and module path are trusted.
        self.worker_process = subprocess.Popen([python_executable, "-m", "orchestrator.workers.sample_worker"], env=env)  # noqa: S603, S607 # python_executable and module path are trusted.
        time.sleep(5)  # Wait for the services to start

    def tearDown(self):
        """Tear down the test case."""
        self.orchestrator_process.terminate()
        self.worker_process.terminate()

    @pytest.mark.skip(reason="Orchestrator is not a server, skipping test")
    def test_start_process(self):
        """Test starting a new process instance."""
        response = requests.post(
            "http://localhost:8080/api/processes/sample_process/start",
            json={},
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)
        process_instance_id = response.json()["id"]

        # Wait for the process to complete
        for _ in range(10):
            response = requests.get(
                f"http://localhost:8080/api/processes/instances/{process_instance_id}",
                timeout=10,
            )
            if response.json()["status"] == "COMPLETED":
                break
            time.sleep(1)
        else:
            self.fail("Process did not complete in time.")


if __name__ == "__main__":
    unittest.main()
