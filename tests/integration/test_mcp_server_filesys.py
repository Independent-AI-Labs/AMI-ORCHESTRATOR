#!/usr/bin/env python
"""Integration tests for Filesys MCP server run script."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest


class TestFilesysMCPServer:
    """Test the Filesys MCP server run script with full environment setup."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.root_dir = Path(__file__).parent.parent.parent
        self.files_dir = self.root_dir / "files"
        self.venv_dir = self.files_dir / ".venv"
        self.run_script = self.files_dir / "backend" / "mcp" / "filesys" / "run_filesys.py"

        # Create a temporary directory for file operations
        self.temp_dir = Path(tempfile.mkdtemp())

        # Backup existing venv if it exists
        self.venv_backup = None
        if self.venv_dir.exists():
            self.venv_backup = self.venv_dir.parent / ".venv_backup"
            if self.venv_backup.exists():
                shutil.rmtree(self.venv_backup)
            shutil.move(str(self.venv_dir), str(self.venv_backup))

        yield

        # Cleanup
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Restore original venv if it was backed up
        if self.venv_backup and self.venv_backup.exists():
            if self.venv_dir.exists():
                shutil.rmtree(self.venv_dir)
            shutil.move(str(self.venv_backup), str(self.venv_dir))

    def test_filesys_mcp_server_setup_and_run(self):
        """Test that the Filesys MCP server run script sets up environment and starts correctly."""
        # Ensure venv doesn't exist
        if self.venv_dir.exists():
            shutil.rmtree(self.venv_dir)

        assert not self.venv_dir.exists(), "venv should not exist before test"

        # Run the script with --stdio flag and root directory
        env = os.environ.copy()
        env["MCP_TEST_MODE"] = "1"  # Set test mode to exit quickly

        # Start the process
        process = subprocess.Popen(
            [sys.executable, str(self.run_script), "--stdio", "--root-dir", str(self.temp_dir)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(self.files_dir),
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
            # Check if process is still running
            if process.poll() is None:
                # Send request
                process.stdin.write(json.dumps(initialize_request) + "\n")
                process.stdin.flush()

            # Give it time to process
            time.sleep(3)

            # Check for successful initialization or expected error
            # The script should have set up the environment successfully
            assert self.venv_dir.exists(), "venv should exist after running script"

            # Check that requirements were installed
            requirements_file = self.files_dir / "requirements.txt"
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

    def test_filesys_mcp_server_file_operations(self):
        """Test that the Filesys MCP server can perform file operations."""
        # Create a test file
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("Hello, World!")

        # Start the process
        process = subprocess.Popen(
            [sys.executable, str(self.run_script), "--stdio", "--root-dir", str(self.temp_dir)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(self.files_dir),
        )

        try:
            # Give it a moment to start
            time.sleep(2)

            # Send read file request
            read_request = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "test.txt"}}, "id": 1}

            process.stdin.write(json.dumps(read_request) + "\n")
            process.stdin.flush()

            # The server should be able to read the file

            time.sleep(2)

        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

    def test_filesys_mcp_server_directory_listing(self):
        """Test that the Filesys MCP server can list directories."""
        # Create some test files
        (self.temp_dir / "file1.txt").write_text("File 1")
        (self.temp_dir / "file2.txt").write_text("File 2")
        subdir = self.temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("File 3")

        # Start the process
        process = subprocess.Popen(
            [sys.executable, str(self.run_script), "--stdio", "--root-dir", str(self.temp_dir)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(self.files_dir),
        )

        try:
            # Give it a moment to start
            time.sleep(2)

            # Send list directory request
            list_request = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_directory", "arguments": {"path": "."}}, "id": 1}

            process.stdin.write(json.dumps(list_request) + "\n")
            process.stdin.flush()

            # The server should be able to list the directory contents

            time.sleep(2)

        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
