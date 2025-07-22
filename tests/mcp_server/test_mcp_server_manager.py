import os
import time
import pytest
import subprocess
from orchestrator.mcp.mcp_server_manager import MCPServerManager, PID_FILE, LOG_FILE

# Define paths relative to the project root
SERVER_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "servers", "local_file_server.py"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")) # AMI-SDA root

@pytest.fixture(autouse=True)
def cleanup_pid_and_log_files():
    """Ensure PID and log files are cleaned up before and after each test."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    yield
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

def test_mcp_server_manager_start_stop():
    manager = MCPServerManager(SERVER_SCRIPT, PROJECT_ROOT)

    # Test starting the server
    manager.start_server()
    time.sleep(1)  # Give server time to write PID file
    assert os.path.exists(PID_FILE)
    with open(PID_FILE, "r") as f:
        pid = int(f.read().strip())
    assert pid > 0

    # Check if the process is actually running using the manager's method
    assert manager.is_process_running(pid)

    # Test stopping the server
    manager.stop_server()
    time.sleep(1) # Give server time to terminate
    assert not os.path.exists(PID_FILE)

    # Check if the process is actually stopped using the manager's method
    assert not manager.is_process_running(pid)

def test_mcp_server_manager_start_already_running():
    manager = MCPServerManager(SERVER_SCRIPT, PROJECT_ROOT)

    # Manually create a PID file to simulate already running server
    with open(PID_FILE, "w") as f:
        f.write("12345") # Dummy PID

    # Attempt to start again, should print message and not raise error
    manager.start_server()
    assert os.path.exists(PID_FILE) # PID file should still exist

def test_mcp_server_manager_stop_not_running():
    manager = MCPServerManager(SERVER_SCRIPT, PROJECT_ROOT)

    # Attempt to stop when no PID file exists, should print message and not raise error
    manager.stop_server()
    assert not os.path.exists(PID_FILE) # PID file should not be created