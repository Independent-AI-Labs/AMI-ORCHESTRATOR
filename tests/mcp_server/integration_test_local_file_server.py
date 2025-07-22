import base64
import json
import os
import stat
import subprocess
import sys
import time
import signal
import re
from pathlib import Path
from subprocess import Popen
from typing import Generator

import pytest

from orchestrator.mcp.mcp_server_manager import MCPServerManager

# Define paths relative to the project root
SERVER_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mcp", "servers", "local_file_server.py"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


class MCPError(Exception):
    """Custom exception for MCP errors."""
    def __init__(self, error_data):
        self.error_data = error_data
        message = f"MCP Error: {error_data.get('message', 'Unknown error')} (Code: {error_data.get('code', 'N/A')})"
        super().__init__(message)


class MCPClient:
    """A simple client to communicate with the MCP server via JSON-RPC."""

    def __init__(self, process: Popen):
        self.process = process
        self.request_id = 0
        self._initialize_server()

    def _send_request(self, method: str, params: dict):
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        request_str = json.dumps(request) + '\n'
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.write(request_str.encode('utf-8'))
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
            decoded_line = line.decode('utf-8').strip()
            if not decoded_line:
                continue
            buffer += decoded_line
            try:
                response = json.loads(buffer)
                if "error" in response:
                    raise MCPError(response["error"])
                return response
            except json.JSONDecodeError:
                if not buffer.strip().startswith('{'):
                    buffer = ""
                pass

    def _send_and_read(self, method: str, params: dict):
        self._send_request(method, params)
        return self._read_response()

    def _initialize_server(self):
        response = self._send_and_read("initialize", {})
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == self.request_id
        assert "result" in response

    def list_tools(self):
        response = self._send_and_read("tools/list", {})
        return response["result"]["tools"]

    def call_tool(self, tool_name: str, **tool_args):
        response = self._send_and_read("tools/call", {"name": tool_name, "arguments": tool_args})
        # The actual result is nested inside the response
        return response["result"]["content"][0]["text"]


@pytest.fixture(scope="module")
def mcp_server_client() -> Generator[MCPClient, None, None]:
    manager = MCPServerManager(SERVER_SCRIPT, PROJECT_ROOT)
    process = None
    try:
        manager.stop_server()
        process = manager.start_server_for_testing()
        time.sleep(1)
        if process.poll() is not None:
            stderr_output = process.stderr.read().decode(errors='ignore')
            raise RuntimeError(f"MCP server failed to start. Exit code: {process.poll()}\n{stderr_output}")
        client = MCPClient(process)
        yield client
    finally:
        if process and process.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], check=False, capture_output=True)
                else:
                    pgid = os.getpgid(process.pid)
                    os.killpg(pgid, signal.SIGTERM)
                process.wait(timeout=5)
            except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
                process.kill()


@pytest.fixture
def temp_integration_file(tmp_path: Path) -> str:
    file_path = tmp_path / "integration_test_file.txt"
    file_path.write_text("Line 1\nLine 2\nLine 3\n")
    return str(file_path)


@pytest.fixture
def temp_integration_binary_file(tmp_path: Path) -> str:
    file_path = tmp_path / "integration_test_binary_file.bin"
    content = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"
    file_path.write_bytes(content)
    return str(file_path)


@pytest.fixture
def read_only_dir(tmp_path: Path) -> Generator[Path, None, None]:
    dir_path = tmp_path / "read_only_dir"
    dir_path.mkdir()
    if sys.platform == "win32":
        user = os.getlogin()
        subprocess.run(["icacls", str(dir_path), "/deny", f"{user}:(W)"], check=True, capture_output=True)
    else:
        os.chmod(dir_path, stat.S_IREAD | stat.S_IEXEC)
    
    yield dir_path
    
    if sys.platform == "win32":
        user = os.getlogin()
        subprocess.run(["icacls", str(dir_path), "/grant", f"{user}:(F)"], check=True, capture_output=True)
    else:
        os.chmod(dir_path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)


def test_mcp_list_tools(mcp_server_client: MCPClient):
    tools = mcp_server_client.list_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0
    assert any(tool["name"] == "read_file" for tool in tools)


def test_mcp_read_file_text(mcp_server_client: MCPClient, temp_integration_file: str):
    result = mcp_server_client.call_tool("read_file", file_path=temp_integration_file, mode="text")
    assert result == "Line 1\nLine 2\nLine 3\n"


def test_mcp_read_file_binary(mcp_server_client: MCPClient, temp_integration_binary_file: str):
    result = mcp_server_client.call_tool("read_file", file_path=temp_integration_binary_file, mode="binary")
    expected_content_b64 = base64.b64encode(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09").decode('utf-8')
    assert result == expected_content_b64


def test_mcp_write_file_text(mcp_server_client: MCPClient, tmp_path: Path):
    file_path = tmp_path / "write_test.txt"
    result = mcp_server_client.call_tool("write_file", file_path=str(file_path), content="New text content.", mode="text")
    assert "Successfully wrote text content" in result
    assert file_path.read_text() == "New text content."


def test_mcp_write_file_binary(mcp_server_client: MCPClient, tmp_path: Path):
    file_path = tmp_path / "write_binary_test.bin"
    content_b64 = base64.b64encode(b"\x0a\x0b\x0c").decode('utf-8')
    result = mcp_server_client.call_tool("write_file", file_path=str(file_path), content=content_b64, mode="binary")
    assert "Successfully wrote binary content" in result
    assert file_path.read_bytes() == b"\x0a\x0b\x0c"


def test_mcp_replace_content_text(mcp_server_client: MCPClient, temp_integration_file: str):
    old_c = "Line 2"
    new_c = "Replaced Line 2"
    result = mcp_server_client.call_tool("edit_file_replace_string", file_path=temp_integration_file, old_string=old_c, new_string=new_c, mode="text")
    assert "Successfully replaced 1 occurrence(s)" in result
    with open(temp_integration_file, "r") as f:
        assert f.read() == "Line 1\nReplaced Line 2\nLine 3\n"


def test_mcp_replace_content_binary(mcp_server_client: MCPClient, temp_integration_binary_file: str):
    old_c = b"\x01\x02"
    new_c = b"\xff\xfe"
    result = mcp_server_client.call_tool("edit_file_replace_string", file_path=temp_integration_binary_file, old_string=base64.b64encode(old_c).decode(),
                                           new_string=base64.b64encode(new_c).decode(), mode="binary")
    assert "Successfully replaced 1 occurrence(s)" in result
    with open(temp_integration_binary_file, "rb") as f:
        assert f.read() == b"\x00\xff\xfe\x03\x04\x05\x06\x07\x08\x09"


def test_mcp_replace_lines(mcp_server_client: MCPClient, temp_integration_file: str):
    new_content = "New line 2\nNew line 3\n"
    result = mcp_server_client.call_tool("edit_file_replace_lines", file_path=temp_integration_file, start_line=2, end_line=3, new_string=new_content)
    assert "Successfully replaced lines 2-3" in result
    with open(temp_integration_file, "r") as f:
        assert f.read() == "Line 1\nNew line 2\nNew line 3\n"


def test_mcp_delete_files(mcp_server_client: MCPClient, tmp_path: Path):
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("content1")
    file2.write_text("content2")

    result = mcp_server_client.call_tool("delete_files", file_paths=[str(file1), str(file2)])
    assert "Successfully deleted 2 file(s)" in result
    assert not file1.exists()
    assert not file2.exists()


def test_mcp_move_files(mcp_server_client: MCPClient, tmp_path: Path):
    source_file = tmp_path / "source.txt"
    destination_file = tmp_path / "destination.txt"
    source_file.write_text("content")

    result = mcp_server_client.call_tool("move_files", source_paths=[str(source_file)], destination_paths=[str(destination_file)])
    assert "Successfully moved 1 file(s)" in result
    assert not source_file.exists()
    assert destination_file.exists()
    assert destination_file.read_text() == "content"


def test_mcp_create_directory(mcp_server_client: MCPClient, tmp_path: Path):
    new_dir = tmp_path / "new_directory"
    result = mcp_server_client.call_tool("create_directory", directory_path=str(new_dir))
    assert "Successfully created directory" in result
    assert new_dir.is_dir()


def test_mcp_delete_directory(mcp_server_client: MCPClient, tmp_path: Path):
    dir_to_delete = tmp_path / "dir_to_delete"
    dir_to_delete.mkdir()
    (dir_to_delete / "file.txt").write_text("content")

    result = mcp_server_client.call_tool("delete_directory", directory_path=str(dir_to_delete))
    assert "Successfully deleted directory" in result
    assert not dir_to_delete.exists()


# --- Error handling tests ---

def test_mcp_read_file_not_found_error(mcp_server_client: MCPClient, tmp_path: Path):
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(MCPError, match=r"File not found: .*non_existent.txt"):
        mcp_server_client.call_tool("read_file", file_path=str(non_existent_file))


def test_mcp_write_file_permission_error(mcp_server_client: MCPClient, read_only_dir: Path):
    read_only_path = read_only_dir / "test.txt"
    with pytest.raises(MCPError, match=r"Permission denied: cannot write to file"):
        mcp_server_client.call_tool("write_file", file_path=str(read_only_path), content="some content")


def test_mcp_replace_lines_error(mcp_server_client: MCPClient, tmp_path: Path):
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(MCPError, match=r"File not found: .*non_existent.txt"):
        mcp_server_client.call_tool("edit_file_replace_lines", file_path=str(non_existent_file), start_line=1, end_line=1, new_string="test")


def test_mcp_delete_files_error(mcp_server_client: MCPClient, tmp_path: Path):
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(MCPError, match=r"Some files could not be deleted: File not found: .*non_existent.txt"):
        mcp_server_client.call_tool("delete_files", file_paths=[str(non_existent_file)])


def test_mcp_move_files_error(mcp_server_client: MCPClient, tmp_path: Path):
    non_existent_file = tmp_path / "non_existent.txt"
    target_file = tmp_path / "target.txt"
    with pytest.raises(MCPError, match=r"Some files could not be moved: Source file not found: .*non_existent.txt"):
        mcp_server_client.call_tool("move_files", source_paths=[str(non_existent_file)], destination_paths=[str(target_file)])


def test_mcp_create_directory_permission_error(mcp_server_client: MCPClient, read_only_dir: Path):
    invalid_path = read_only_dir / "new_dir"
    with pytest.raises(MCPError, match=r"Permission denied creating directory"):
        mcp_server_client.call_tool("create_directory", directory_path=str(invalid_path))


def test_mcp_delete_directory_not_found_error(mcp_server_client: MCPClient, tmp_path: Path):
    invalid_path = tmp_path / "nonexistent_dir"
    with pytest.raises(MCPError, match=r"Directory not found: .*nonexistent_dir"):
        mcp_server_client.call_tool("delete_directory", directory_path=str(invalid_path))


def test_mcp_unknown_tool_error(mcp_server_client: MCPClient):
    with pytest.raises(MCPError, match="Unknown tool"):
        mcp_server_client.call_tool("non_existent_tool")


def test_mcp_server_shutdown_on_eof(mcp_server_client: MCPClient):
    if mcp_server_client.process.stdin and not mcp_server_client.process.stdin.closed:
        mcp_server_client.process.stdin.close()

    try:
        mcp_server_client.process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        mcp_server_client.process.kill()

    assert mcp_server_client.process.poll() is not None
