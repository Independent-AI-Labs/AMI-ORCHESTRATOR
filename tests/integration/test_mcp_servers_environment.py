#!/usr/bin/env python
"""Integration tests for MCP server run scripts environment setup."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


class TestMCPServersEnvironment:
    """Test that all MCP server run scripts properly set up their environments."""

    def test_dataops_mcp_server_environment_setup(self):
        """Test that the DataOps MCP server run script sets up its environment."""
        root_dir = Path(__file__).parent.parent.parent
        base_dir = root_dir / "base"
        venv_dir = base_dir / ".venv"
        run_script = base_dir / "backend" / "mcp" / "dataops" / "run_dataops.py"

        # Skip if script doesn't exist
        if not run_script.exists():
            pytest.skip(f"Run script not found: {run_script}")

        # Backup and remove existing venv
        venv_backup = None
        if venv_dir.exists():
            venv_backup = venv_dir.parent / ".venv_backup_dataops"
            if venv_backup.exists():
                shutil.rmtree(venv_backup)
            shutil.move(str(venv_dir), str(venv_backup))

        try:
            # Ensure venv doesn't exist
            assert not venv_dir.exists(), "venv should not exist before test"

            # Run the script with --help to trigger environment setup
            result = subprocess.run([sys.executable, str(run_script), "--help"], capture_output=True, text=True, timeout=30, cwd=str(base_dir), check=False)

            # Check that venv was created
            assert venv_dir.exists(), f"venv should be created by run script. stderr: {result.stderr}"

            # Check that it's a valid venv
            venv_python = venv_dir / "Scripts" / "python.exe"
            if not venv_python.exists():
                venv_python = venv_dir / "bin" / "python"

            assert venv_python.exists(), "venv should have python executable"

        finally:
            # Restore original venv
            if venv_backup and venv_backup.exists():
                if venv_dir.exists():
                    shutil.rmtree(venv_dir)
                shutil.move(str(venv_backup), str(venv_dir))

    def test_ssh_mcp_server_environment_setup(self):
        """Test that the SSH MCP server run script sets up its environment."""
        root_dir = Path(__file__).parent.parent.parent
        base_dir = root_dir / "base"
        venv_dir = base_dir / ".venv"
        run_script = base_dir / "backend" / "mcp" / "ssh" / "run_ssh.py"

        # Skip if script doesn't exist
        if not run_script.exists():
            pytest.skip(f"Run script not found: {run_script}")

        # Backup and remove existing venv
        venv_backup = None
        if venv_dir.exists():
            venv_backup = venv_dir.parent / ".venv_backup_ssh"
            if venv_backup.exists():
                shutil.rmtree(venv_backup)
            shutil.move(str(venv_dir), str(venv_backup))

        try:
            # Ensure venv doesn't exist
            assert not venv_dir.exists(), "venv should not exist before test"

            # Run the script with --help to trigger environment setup
            result = subprocess.run([sys.executable, str(run_script), "--help"], capture_output=True, text=True, timeout=30, cwd=str(base_dir), check=False)

            # Check that venv was created
            assert venv_dir.exists(), f"venv should be created by run script. stderr: {result.stderr}"

            # Check that it's a valid venv
            venv_python = venv_dir / "Scripts" / "python.exe"
            if not venv_python.exists():
                venv_python = venv_dir / "bin" / "python"

            assert venv_python.exists(), "venv should have python executable"

        finally:
            # Restore original venv
            if venv_backup and venv_backup.exists():
                if venv_dir.exists():
                    shutil.rmtree(venv_dir)
                shutil.move(str(venv_backup), str(venv_dir))

    def test_chrome_mcp_server_environment_setup(self):
        """Test that the Chrome MCP server run script sets up its environment."""
        root_dir = Path(__file__).parent.parent.parent
        browser_dir = root_dir / "browser"
        venv_dir = browser_dir / ".venv"
        run_script = browser_dir / "backend" / "mcp" / "chrome" / "run_chrome.py"

        # Skip if script doesn't exist
        if not run_script.exists():
            pytest.skip(f"Run script not found: {run_script}")

        # Backup and remove existing venv
        venv_backup = None
        if venv_dir.exists():
            venv_backup = venv_dir.parent / ".venv_backup_chrome"
            if venv_backup.exists():
                shutil.rmtree(venv_backup)
            shutil.move(str(venv_dir), str(venv_backup))

        try:
            # Ensure venv doesn't exist
            assert not venv_dir.exists(), "venv should not exist before test"

            # Run the script with --help to trigger environment setup
            result = subprocess.run([sys.executable, str(run_script), "--help"], capture_output=True, text=True, timeout=30, cwd=str(browser_dir), check=False)

            # Check that venv was created
            assert venv_dir.exists(), f"venv should be created by run script. stderr: {result.stderr}"

            # Check that it's a valid venv
            venv_python = venv_dir / "Scripts" / "python.exe"
            if not venv_python.exists():
                venv_python = venv_dir / "bin" / "python"

            assert venv_python.exists(), "venv should have python executable"

        finally:
            # Restore original venv
            if venv_backup and venv_backup.exists():
                if venv_dir.exists():
                    shutil.rmtree(venv_dir)
                shutil.move(str(venv_backup), str(venv_dir))

    def test_filesys_mcp_server_environment_setup(self):
        """Test that the Filesys MCP server run script sets up its environment."""
        root_dir = Path(__file__).parent.parent.parent
        files_dir = root_dir / "files"
        venv_dir = files_dir / ".venv"
        run_script = files_dir / "backend" / "mcp" / "filesys" / "run_filesys.py"

        # Skip if script doesn't exist
        if not run_script.exists():
            pytest.skip(f"Run script not found: {run_script}")

        # Backup and remove existing venv
        venv_backup = None
        if venv_dir.exists():
            venv_backup = venv_dir.parent / ".venv_backup_filesys"
            if venv_backup.exists():
                shutil.rmtree(venv_backup)
            shutil.move(str(venv_dir), str(venv_backup))

        try:
            # Ensure venv doesn't exist
            assert not venv_dir.exists(), "venv should not exist before test"

            # Run the script with --help to trigger environment setup
            result = subprocess.run([sys.executable, str(run_script), "--help"], capture_output=True, text=True, timeout=30, cwd=str(files_dir), check=False)

            # Check that venv was created
            assert venv_dir.exists(), f"venv should be created by run script. stderr: {result.stderr}"

            # Check that it's a valid venv
            venv_python = venv_dir / "Scripts" / "python.exe"
            if not venv_python.exists():
                venv_python = venv_dir / "bin" / "python"

            assert venv_python.exists(), "venv should have python executable"

        finally:
            # Restore original venv
            if venv_backup and venv_backup.exists():
                if venv_dir.exists():
                    shutil.rmtree(venv_dir)
                shutil.move(str(venv_backup), str(venv_dir))
