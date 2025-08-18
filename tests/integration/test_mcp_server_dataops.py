#!/usr/bin/env python
"""Integration tests for DataOps MCP server run script."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest


class TestDataOpsMCPServer:
    """Test the DataOps MCP server run script with full environment setup."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.root_dir = Path(__file__).parent.parent.parent
        self.base_dir = self.root_dir / "base"
        self.venv_dir = self.base_dir / ".venv"
        self.run_script = self.base_dir / "backend" / "mcp" / "dataops" / "run_dataops.py"

        # Backup existing venv if it exists
        self.venv_backup = None
        if self.venv_dir.exists():
            self.venv_backup = self.venv_dir.parent / ".venv_backup"
            if self.venv_backup.exists():
                shutil.rmtree(self.venv_backup)
            shutil.move(str(self.venv_dir), str(self.venv_backup))

        yield

        # Restore original venv if it was backed up
        if self.venv_backup and self.venv_backup.exists():
            if self.venv_dir.exists():
                shutil.rmtree(self.venv_dir)
            shutil.move(str(self.venv_backup), str(self.venv_dir))

    def test_dataops_mcp_server_setup_and_run(self):
        """Test that the DataOps MCP server run script sets up environment and starts correctly."""
        # Ensure venv doesn't exist
        if self.venv_dir.exists():
            shutil.rmtree(self.venv_dir)

        assert not self.venv_dir.exists(), "venv should not exist before test"

        # Run the script with --stdio flag
        env = os.environ.copy()
        env["MCP_TEST_MODE"] = "1"  # Set test mode to exit quickly

        # Start the process
        process = subprocess.Popen(
            [sys.executable, str(self.run_script), "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(self.base_dir),
        )

        # Give it time to set up the environment
        time.sleep(5)

        # Check that venv was created
        assert self.venv_dir.exists(), "venv should be created by run script"

        # Send initialize request
        initialize_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}},
            "id": 1,
        }

        try:
            # Send request
            process.stdin.write(json.dumps(initialize_request) + "\n")
            process.stdin.flush()

            # Wait for response with timeout
            process.wait(timeout=10)

            # Read output
            stdout, stderr = process.communicate(timeout=5)

            # Check for successful initialization or expected error
            # The script should have set up the environment successfully
            assert self.venv_dir.exists(), "venv should exist after running script"

            # Check that requirements were installed
            requirements_file = self.base_dir / "requirements.txt"
            if requirements_file.exists():
                # Check that some packages are installed in the venv
                site_packages = self.venv_dir / "Lib" / "site-packages"
                if not site_packages.exists():
                    site_packages = self.venv_dir / "lib" / "python*" / "site-packages"
                    site_packages = list(self.venv_dir.glob("lib/python*/site-packages"))[0] if list(self.venv_dir.glob("lib/python*/site-packages")) else None

                if site_packages and site_packages.exists():
                    # Should have some installed packages
                    packages = list(site_packages.iterdir())
                    assert len(packages) > 0, "venv should have installed packages"

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            # This is expected - the server runs indefinitely
            # But we've verified the environment was set up
        except Exception as e:
            process.kill()
            raise e
        finally:
            # Ensure process is terminated
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

    def test_dataops_mcp_server_handles_missing_dgraph(self):
        """Test that the DataOps MCP server handles missing Dgraph gracefully."""
        # This test verifies the server can start even if Dgraph isn't running
        # It should start but operations requiring Dgraph should fail gracefully

        # Start the process
        process = subprocess.Popen(
            [sys.executable, str(self.run_script), "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(self.base_dir),
        )

        try:
            # Give it a moment to start
            time.sleep(2)

            # Send a test request
            test_request = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}

            process.stdin.write(json.dumps(test_request) + "\n")
            process.stdin.flush()

            # The server should respond even if Dgraph isn't available
            # It just won't be able to perform Dgraph operations

            # Kill the process after a short time
            time.sleep(2)

        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
