import json
import os
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path
from subprocess import Popen

import pytest

from orchestrator.mcp.mcp_server_manager import MCPServerManager

# Define paths relative to the project root
SERVER_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "mcp" / "servers" / "localfs" / "local_file_server.py"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class MCPError(Exception):
    """Custom exception for MCP errors."""

    def __init__(self, error_data):
        self.error_data = error_data
        message = f"MCP Error: {error_data.get('message', 'Unknown error')} (Code: {error_data.get('code', 'N/A')})"
        super().__init__(message)


class MCPClient:
    """A simple client to communicate with the MCP server via JSON-RPC."""

    def __init__(self, process: Popen, root_dir: Path):
        self.process = process
        self.request_id = 0
        self.root_dir = root_dir
        self._initialize_server()

    def _send_request(self, method: str, params: dict):
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params,
        }
        request_str = json.dumps(request) + "\n"
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.write(request_str.encode("utf-8"))
            self.process.stdin.flush()

    def _read_response(self):
        buffer = ""
        while True:
            if not self.process.stdout or self.process.stdout.closed:
                raise EOFError("Server process stdout closed unexpectedly.")
            line = self.process.stdout.readline()
            if not line:
                time.sleep(0.1)
                if self.process.poll() is not None:
                    raise EOFError("Server process closed unexpectedly.")
                continue
            decoded_line = line.decode("utf-8").strip()
            if not decoded_line:
                continue
            buffer += decoded_line
            try:
                response = json.loads(buffer)
                if "error" in response:
                    raise MCPError(response["error"])
                return response
            except json.JSONDecodeError:
                if not buffer.strip().startswith("{"):
                    buffer = ""
                # pylint: disable=unnecessary-pass

    def _send_and_read(self, method: str, params: dict):
        self._send_request(method, params)
        return self._read_response()

    def _initialize_server(self):
        response = self._send_and_read("initialize", {})
        assert response["jsonrpc"] == "2.0"  # nosec B101
        assert response["id"] == self.request_id  # nosec B101
        assert "result" in response  # nosec B101

    def list_tools(self):
        response = self._send_and_read("tools/list", {})
        return response["result"]["tools"]

    def call_tool(self, tool_name: str, **tool_args):
        print(f"DEBUG: Calling tool: {tool_name} with args: {tool_args}")
        response = self._send_and_read("tools/call", {"name": tool_name, "arguments": tool_args})
        # The actual result is nested inside the response
        return response["result"]["content"][0]["text"]


@pytest.fixture(scope="module")
def client(tmp_path_factory) -> Generator[MCPClient, None, None]:
    """Pytest fixture to provide an MCPClient instance for testing."""
    # Create a unique root directory for this test session
    test_root_dir = tmp_path_factory.mktemp("mcp_test_root")
    manager = MCPServerManager(str(SERVER_SCRIPT_PATH), str(test_root_dir))
    process = None
    try:
        manager.stop_server()
        process = manager.start_server_for_testing(cwd=str(test_root_dir), capture_stderr=True)
        time.sleep(1)
        if process.poll() is not None:
            stderr_output = process.stderr.read().decode(errors="ignore") if process.stderr else ""
            raise RuntimeError(f"MCP server failed to start. Exit code: {process.poll()}\n{stderr_output}")
        client = MCPClient(process, test_root_dir)
        yield client
    finally:
        if process:
            stdout, stderr = process.communicate(timeout=5)
            if stdout:
                print(f"\n--- MCP Server Stdout ---\n{stdout.decode(errors='ignore')}\n-------------------------", file=sys.stderr)
            if stderr:
                print(f"\n--- MCP Server Stderr ---\n{stderr.decode(errors='ignore')}\n-------------------------", file=sys.stderr)
            if process.poll() is None:
                try:
                    if sys.platform == "win32":
                        subprocess.run(  # noqa: S603, S607
                            ["taskkill", "/F", "/T", "/PID", str(process.pid)],  # noqa: S603, S607
                            # `taskkill` is a trusted system executable, and `process.pid` is an integer, not untrusted input.
                            check=False,
                            capture_output=True,
                            shell=False,
                        )
                    else:
                        try:
                            # pylint: disable=no-member
                            pgid = os.getpgid(process.pid)
                            os.killpg(pgid, signal.SIGTERM)  # pylint: disable=no-member
                        except OSError:
                            pass  # Process already gone
                    process.wait(timeout=5)
                except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
                    process.kill()


@pytest.fixture
def read_only_dir(client: MCPClient) -> Generator[Path, None, None]:
    """Creates a temporary read-only directory for permission tests within the client's root_dir."""
    dir_path = Path(client.root_dir) / "temp_read_only_dir"
    dir_path.mkdir(parents=True, exist_ok=True)

    # Create a file inside to test write permissions
    (dir_path / "test.txt").write_text("test")

    # Set read-only permissions on the file
    if sys.platform == "win32":
        (dir_path / "test.txt").chmod(stat.S_IREAD)
    else:
        (dir_path / "test.txt").chmod(stat.S_IREAD | stat.S_IEXEC)

    yield dir_path

    # Cleanup is handled by tmp_path_factory, but ensure write permissions are restored for robust cleanup
    if sys.platform == "win32":
        (dir_path / "test.txt").chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
    else:
        (dir_path / "test.txt").chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)


def test_mcp_replace_string_outside_root_error(client: MCPClient):
    """Tests edit_file_replace_string error for a file outside the allowed root directory."""
    outside_file = client.root_dir.parent / "outside_replace.txt"
    try:
        outside_file.write_text("original content")
        with pytest.raises(MCPError) as excinfo:
            client.call_tool("edit_file_replace_string", file_path=str(outside_file), old_string="original", new_string="new")
        assert "is outside the allowed root directory" in str(excinfo.value)
        assert str(outside_file) in str(excinfo.value)
    finally:
        if outside_file.exists():
            outside_file.unlink()


@pytest.mark.skipif(sys.platform == "win32", reason="This test is unreliable on Windows due to os.chmod behavior on directories.")
def test_mcp_create_directory_permission_error(client: MCPClient, read_only_dir: Path):
    """Tests create_directory error for permission denied."""
    # Attempt to create a directory inside the read-only directory
    invalid_path = read_only_dir / "new_dir"
    with pytest.raises(MCPError, match=r"Permission denied"):
        client.call_tool("create_directory", directory_path=str(invalid_path))
