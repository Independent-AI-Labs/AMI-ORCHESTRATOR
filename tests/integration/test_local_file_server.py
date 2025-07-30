import ast
import base64
import json
import os
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path
from quopri import encodestring
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
        response = self._send_and_read("tools/call", {"name": tool_name, "arguments": tool_args})
        return response["result"]


@pytest.fixture(scope="module")
def client(tmp_path_factory) -> Generator[MCPClient, None, None]:
    """Pytest fixture to provide an MCPClient instance for testing."""
    test_root_dir = tmp_path_factory.mktemp("mcp_test_root")
    manager = MCPServerManager(str(SERVER_SCRIPT_PATH), str(test_root_dir))
    process = None
    try:
        manager.stop_server()
        process = manager.start_server_for_testing(cwd=str(test_root_dir), capture_stderr=True)
        time.sleep(1)
        if process.poll() is not None:
            stderr_output = process.stderr.read().decode(errors="ignore")
            raise RuntimeError(f"MCP server failed to start. Exit code: {process.poll()}\n{stderr_output}")
        client = MCPClient(process, test_root_dir)
        yield client
    finally:
        if process and process.poll() is not None:
            try:
                if sys.platform == "win32":
                    subprocess.run(  # noqa: S603, S607
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],  # noqa: S603, S607
                        check=False,
                        capture_output=True,
                        shell=False,
                    )
                else:
                    try:
                        pgid = process.pid
                        signal.signal(signal.SIGTERM, signal.SIG_IGN)
                        os.killpg(pgid, signal.SIGTERM)
                    except OSError:
                        pass
                process.wait(timeout=5)
            except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
                process.kill()


@pytest.fixture
def temp_file(client: MCPClient) -> str:
    """Creates a temporary text file for integration tests."""
    file_path = Path(client.root_dir) / "integration_test_file.txt"
    file_path.write_text("Line 1\nLine 2\nLine 3\n")
    return str(file_path)


@pytest.fixture
def temp_binary_file(client: MCPClient) -> str:
    """Creates a temporary binary file for integration tests."""
    file_path = Path(client.root_dir) / "integration_test_binary_file.bin"
    content = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"
    file_path.write_bytes(content)
    return str(file_path)


@pytest.fixture
def read_only_dir(client: MCPClient) -> Generator[Path, None, None]:
    """Creates a temporary read-only directory for permission tests within the client's root_dir."""
    dir_path = Path(client.root_dir) / "temp_read_only_dir"
    dir_path.mkdir(parents=True, exist_ok=True)

    (dir_path / "test.txt").write_text("test")

    if sys.platform == "win32":
        (dir_path / "test.txt").chmod(stat.S_IREAD)
    else:
        (dir_path / "test.txt").chmod(stat.S_IREAD | stat.S_IEXEC)

    yield dir_path

    if sys.platform == "win32":
        (dir_path / "test.txt").chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
    else:
        (dir_path / "test.txt").chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)


def test_mcp_list_tools(client: MCPClient):
    """Tests the list_tools MCP command."""
    tools = client.list_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0
    assert any(tool["name"] == "read_from_file" for tool in tools)

    # Create the test directory structure and files
    test_dir = client.root_dir / "test_dir"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create the subdirectory
    (test_dir / "subdir").mkdir(parents=True, exist_ok=True)

    # Create the expected files
    (test_dir / "file1.txt").touch()
    (test_dir / "file2.txt").touch()

    result = client.call_tool("list_dir", path=str(test_dir))
    # The output is now a formatted string representing a tree
    expected_output = "\n".join(["├───subdir", "├───file1.txt", "└───file2.txt"])
    assert result["content"][0]["text"] == expected_output

    # Testing recursive listing
    (test_dir / "subdir" / "subfile.txt").touch()
    result = client.call_tool("list_dir", path=str(test_dir), recursive=True)
    expected_recursive_output = "\n".join(
        [
            "├───subdir",
            "│   └───subfile.txt",
            "├───file1.txt",
            "└───file2.txt",
        ]
    )
    assert result["content"][0]["text"] == expected_recursive_output


def test_mcp_create_dirs(client: MCPClient):
    """Tests the create_dirs MCP command."""
    new_dir = Path(client.root_dir) / "new_dir" / "subdir"
    result = client.call_tool("create_dirs", path=str(new_dir))
    assert "Successfully created directory" in result["content"][0]["text"]
    assert new_dir.is_dir()


def test_mcp_find_paths(client: MCPClient):
    """Tests the find_paths MCP command."""
    (client.root_dir / "find_test").mkdir()
    (client.root_dir / "find_test" / "file_a.txt").write_text("content_x")
    (client.root_dir / "find_test" / "file_b.log").write_text("content_y")
    (client.root_dir / "find_test" / "subdir").mkdir()
    (client.root_dir / "find_test" / "subdir" / "file_c.txt").write_text("content_x")

    result = client.call_tool("find_paths", path=str(client.root_dir / "find_test"), keywords_path_name=["file_a"])
    file_list = ast.literal_eval(result["content"][0]["text"])
    assert len(file_list) == 1
    assert Path(file_list[0]).name == "file_a.txt"

    result = client.call_tool("find_paths", path=str(client.root_dir / "find_test"), kewords_file_content=["content_x"])
    file_list = ast.literal_eval(result["content"][0]["text"])
    expected_file_count = 2
    assert len(file_list) == expected_file_count
    assert {Path(p).name for p in file_list} == {"file_a.txt", "file_c.txt"}


def test_mcp_read_from_file_text(client: MCPClient, temp_file: str):
    """Tests reading a text file using MCP."""
    result = client.call_tool("read_from_file", path=temp_file)
    expected_content_qp = encodestring(b"   1 | Line 1\n   2 | Line 2\n   3 | Line 3").decode("ascii")
    assert result["content"][0]["text"] == expected_content_qp


def test_mcp_read_from_file_binary(client: MCPClient, temp_binary_file: str):
    """Tests reading a binary file using MCP."""
    result = client.call_tool("read_from_file", path=temp_binary_file)
    expected_content_base64 = base64.b64encode(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09").decode("ascii")
    assert result["content"][0]["text"] == expected_content_base64


def test_mcp_write_to_file_text(client: MCPClient):
    """Tests writing a text file using MCP."""
    file_path = Path(client.root_dir) / "write_test.txt"
    new_content_qp = encodestring(b"New text content.").decode("ascii")
    result = client.call_tool("write_to_file", path=str(file_path), new_content=new_content_qp, mode="text")
    assert "Successfully wrote text content" in result["content"][0]["text"]
    assert file_path.read_text() == "New text content."


def test_mcp_write_to_file_binary(client: MCPClient):
    """Tests writing a binary file using MCP."""
    file_path = Path(client.root_dir) / "write_binary_test.bin"
    content_bytes = b"\x0a\x0b\x0c"
    result = client.call_tool(
        "write_to_file",
        path=str(file_path),
        new_content=base64.b64encode(content_bytes).decode("ascii"),
        mode="binary",
        input_format="raw-utf8",
    )
    assert "Successfully wrote binary content" in result["content"][0]["text"]
    assert file_path.read_bytes() == b"\x0a\x0b\x0c"


def test_mcp_delete_paths(client: MCPClient):
    """Tests deleting multiple files and directories using MCP."""
    file1 = Path(client.root_dir) / "file1.txt"
    dir1 = Path(client.root_dir) / "dir1"
    file1.write_text("content1")
    dir1.mkdir()
    (dir1 / "file2.txt").write_text("content2")

    result = client.call_tool("delete_paths", paths=[str(file1), str(dir1)])
    assert "Successfully deleted 2 item(s)" in result["content"][0]["text"]
    assert not file1.exists()
    assert not dir1.exists()


def test_mcp_modify_file_text(client: MCPClient, temp_file: str):
    """Tests modifying a text file using MCP."""
    result = client.call_tool(
        "modify_file",
        path=temp_file,
        start_offset_inclusive=7,
        end_offset_inclusive=12,
        offset_type="CHAR",
        new_content="Modified",
    )
    assert "Successfully modified text file" in result["content"][0]["text"]
    with Path(temp_file).open(encoding="utf-8") as f:
        assert f.read() == "Line 1\nModified\nLine 3\n"


def test_mcp_modify_file_binary(client: MCPClient, temp_binary_file: str):
    """Tests modifying a binary file using MCP."""
    new_content = encodestring(b"\xff\xee").decode("ascii")
    result = client.call_tool(
        "modify_file",
        path=temp_binary_file,
        start_offset_inclusive=2,
        end_offset_inclusive=4,
        offset_type="BYTE",
        new_content=new_content,
    )
    assert "Successfully modified binary file" in result["content"][0]["text"]
    with Path(temp_binary_file).open("rb") as f:
        assert f.read() == b"\x00\x01\xff\xee\x04\x05\x06\x07\x08\x09"


# --- Error handling tests ---


def test_mcp_read_from_file_not_found_error(client: MCPClient):
    """Tests read_from_file error for non-existent file."""
    non_existent_file = Path(client.root_dir) / "non_existent.txt"
    with pytest.raises(MCPError, match=r"File not found: .*non_existent.txt"):
        client.call_tool("read_from_file", path=str(non_existent_file))


def test_mcp_write_to_file_permission_error(client: MCPClient, read_only_dir: Path):
    """Tests write_to_file error for permission denied."""
    read_only_path = read_only_dir / "test.txt"
    with pytest.raises(MCPError, match=r"Permission denied"):
        client.call_tool("write_to_file", path=str(read_only_path), new_content="some content")


def test_mcp_delete_paths_error(client: MCPClient):
    """Tests delete_paths error for non-existent file."""
    non_existent_file = Path(client.root_dir) / "non_existent.txt"
    with pytest.raises(
        MCPError,
        match=r"Some items could not be deleted: Path not found: .*non_existent.txt",
    ):
        client.call_tool("delete_paths", paths=[str(non_existent_file)])


@pytest.mark.skipif(sys.platform == "win32", reason="This test is unreliable on Windows due to os.chmod behavior on directories.")
def test_mcp_create_dirs_permission_error(client: MCPClient, read_only_dir: Path):
    """Tests create_dirs error for permission denied."""
    invalid_path = read_only_dir / "new_dir"
    with pytest.raises(MCPError, match=r"Permission denied"):
        client.call_tool("create_dirs", path=str(invalid_path))


def test_mcp_server_shutdown_on_eof(client: MCPClient):
    """Tests that the MCP server shuts down on EOF."""
    if client.process.stdin and not client.process.stdin.closed:
        client.process.stdin.close()

    try:
        client.process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        client.process.kill()

    assert client.process.poll() is not None
