"""
End-to-end tests for the sample process.
"""

import os
import subprocess
import sys
import time
import unittest

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestSampleProcessE2E(unittest.TestCase):
    """End-to-end tests for the sample process."""

    def setUp(self):
        """Set up the test case."""
        env = os.environ.copy()
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        env["PYTHONPATH"] = project_root
        self.orchestrator_process = subprocess.Popen(["python", "-m", "orchestrator.main"], env=env)
        self.worker_process = subprocess.Popen(["python", "-m", "orchestrator.workers.sample_worker"], env=env)
        time.sleep(5)  # Wait for the services to start

    def tearDown(self):
        """Tear down the test case."""
        self.orchestrator_process.terminate()
        self.worker_process.terminate()

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
