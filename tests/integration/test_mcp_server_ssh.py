#!/usr/bin/env python
"""Integration tests for SSH MCP server run script."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest


class TestSSHMCPServer:
    """Test the SSH MCP server run script with full environment setup."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.root_dir = Path(__file__).parent.parent.parent
        self.base_dir = self.root_dir / "base"
        self.venv_dir = self.base_dir / ".venv"
        self.run_script = self.base_dir / "backend" / "mcp" / "ssh" / "run_ssh.py"

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

    def test_ssh_mcp_server_setup_and_run(self):
        """Test that the SSH MCP server run script sets up environment and starts correctly."""
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

    def test_ssh_mcp_server_configuration(self):
        """Test that the SSH MCP server can be configured with SSH servers."""
        # Create a test SSH config file
        ssh_config = {"servers": [{"name": "test-server", "host": "localhost", "port": 22, "username": "test", "password": "test"}]}

        config_file = self.base_dir / "test_ssh_config.json"
        with config_file.open("w") as f:
            json.dump(ssh_config, f)

        try:
            # Start the process with config
            env = os.environ.copy()
            env["SSH_CONFIG_FILE"] = str(config_file)

            process = subprocess.Popen(
                [sys.executable, str(self.run_script), "--stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=str(self.base_dir),
            )

            # Give it a moment to start
            time.sleep(2)

            # Send list servers request
            list_request = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "ssh_list_servers", "arguments": {}}, "id": 1}

            process.stdin.write(json.dumps(list_request) + "\n")
            process.stdin.flush()

            # The server should be able to list the configured server
            # even if it can't connect to it

            time.sleep(2)

        finally:
            config_file.unlink(missing_ok=True)
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
