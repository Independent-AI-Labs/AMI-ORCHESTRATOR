import base64
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from subprocess import Popen
from typing import Generator

import pytest

from orchestrator.mcp.mcp_server_manager import MCPServerManager

# Define paths relative to the project root
SERVER_SCRIPT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "mcp",
        "servers",
        "localfs",
        "local_file_server.py",
    )
)
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
                pass  # pylint: disable=unnecessary-pass

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
        # The actual result is nested inside the response
        return response["result"]["content"][0]["text"]


@pytest.fixture(scope="module")
def client() -> Generator[MCPClient, None, None]:
    """Pytest fixture to provide an MCPClient instance for testing."""
    manager = MCPServerManager(SERVER_SCRIPT, PROJECT_ROOT)
    process = None
    try:
        manager.stop_server()
        env = os.environ.copy()
        env["PYTHONPATH"] = PROJECT_ROOT
        process = manager.start_server_for_testing(env=env)
        time.sleep(1)
        if process.poll() is not None:
            stderr_output = process.stderr.read().decode(errors="ignore")
            raise RuntimeError(f"MCP server failed to start. Exit code: {process.poll()}\n{stderr_output}")
        client = MCPClient(process)
        yield client
    finally:
        if process and process.poll() is not None:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        check=False,
                        capture_output=True,
                        shell=False,  # nosec B603, B607
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
def temp_file(tmp_path: Path) -> str:
    """Creates a temporary text file for integration tests."""
    # Create temporary files within the orchestrator directory
    orchestrator_temp_dir = Path(PROJECT_ROOT) / "orchestrator" / "temp_test_files"
    orchestrator_temp_dir.mkdir(parents=True, exist_ok=True)
    file_path = orchestrator_temp_dir / "integration_test_file.txt"
    file_path.write_text("Line 1\nLine 2\nLine 3\n")
    return str(file_path)


@pytest.fixture
def temp_binary_file(tmp_path: Path) -> str:
    """Creates a temporary binary file for integration tests."""
    # Create temporary files within the orchestrator directory
    orchestrator_temp_dir = Path(PROJECT_ROOT) / "orchestrator" / "temp_test_files"
    orchestrator_temp_dir.mkdir(parents=True, exist_ok=True)
    file_path = orchestrator_temp_dir / "integration_test_binary_file.bin"
    content = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"
    file_path.write_bytes(content)
    return str(file_path)


@pytest.fixture
def read_only_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Creates a temporary read-only directory for permission tests within PROJECT_ROOT."""
    # Create temporary read-only directory within the orchestrator directory
    orchestrator_temp_dir = Path(PROJECT_ROOT) / "orchestrator" / "temp_read_only_dir"
    orchestrator_temp_dir.mkdir(parents=True, exist_ok=True)
    dir_path = orchestrator_temp_dir

    # Set read-only permissions
    if sys.platform == "win32":
        # On Windows, deny write access for the current user
        user = os.getlogin()
        subprocess.run(
            ["icacls", str(dir_path), "/deny", f"{user}:(W)"],
            check=True,
            capture_output=True,
            shell=False,
        )
    else:
        # On Unix-like systems, remove write permissions for owner, group, others
        os.chmod(dir_path, stat.S_IREAD | stat.S_IEXEC)  # r-x for owner, no write for anyone

    yield dir_path

    # Clean up: restore permissions and remove directory
    if sys.platform == "win32":
        user = os.getlogin()
        subprocess.run(
            ["icacls", str(dir_path), "/remove", f"{user}:(W)"],  # Remove explicit deny
            check=False,  # May fail if permissions were already changed
            capture_output=True,
            shell=False,
        )
        # Attempt to remove the directory, handle if it's still read-only
        try:
            shutil.rmtree(dir_path)
        except OSError as e:
            print(f"Error removing read-only directory on Windows: {e}")
            # Fallback: try to force remove
            subprocess.run(["rmdir", "/s", "/q", str(dir_path)], shell=True)
    else:
        os.chmod(dir_path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)  # Restore write for owner
        shutil.rmtree(dir_path)


def test_mcp_list_tools(client: MCPClient):
    """Tests the list_tools MCP command."""
    tools = client.list_tools()
    assert isinstance(tools, list)  # nosec B101
    assert len(tools) > 0  # nosec B101
    assert any(tool["name"] == "read_file" for tool in tools)  # nosec B101


def test_mcp_read_file_text(client: MCPClient, temp_file: str):
    """Tests reading a text file using MCP."""
    result = client.call_tool("read_file", file_path=temp_file, mode="text")
    assert result == "Line 1\nLine 2\nLine 3\n"  # nosec B101


def test_mcp_read_file_binary(client: MCPClient, temp_binary_file: str):
    """Tests reading a binary file using MCP."""
    result = client.call_tool("read_file", file_path=temp_binary_file, mode="binary")
    expected_content_b64 = base64.b64encode(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09").decode("utf-8")
    assert result == expected_content_b64  # nosec B101


def test_mcp_write_file_text(client: MCPClient, tmp_path: Path):
    """Tests writing a text file using MCP."""
    file_path = tmp_path / "write_test.txt"
    result = client.call_tool("write_file", file_path=str(file_path), content="New text content.", mode="text")
    assert "Successfully wrote text content" in result  # nosec B101
    assert file_path.read_text() == "New text content."  # nosec B101


def test_mcp_write_file_binary(client: MCPClient, tmp_path: Path):
    """Tests writing a binary file using MCP."""
    file_path = tmp_path / "write_binary_test.bin"
    content_b64 = base64.b64encode(b"\x0a\x0b\x0c").decode("utf-8")
    result = client.call_tool("write_file", file_path=str(file_path), content=content_b64, mode="binary")
    assert "Successfully wrote binary content" in result  # nosec B101
    assert file_path.read_bytes() == b"\x0a\x0b\x0c"  # nosec B101


def test_mcp_replace_content_text(client: MCPClient, temp_file: str):
    """Tests replacing content in a text file using MCP."""
    old_c = "Line 2"
    new_c = "Replaced Line 2"
    result = client.call_tool(
        "edit_file_replace_string",
        file_path=temp_file,
        old_string=old_c,
        new_string=new_c,
        mode="text",
    )
    assert "Successfully replaced 1 occurrence(s)" in result  # nosec B101


def test_mcp_read_file_outside_root_error(client: MCPClient, tmp_path: Path):
    """Tests read_file error for a file outside the allowed root directory."""
    # Create a file outside the project root
    outside_file = tmp_path.parent / "outside_file.txt"
    outside_file.write_text("This is outside.")
    with pytest.raises(MCPError, match=r"Path '.*outside_file.txt' is outside the allowed root directory"):
        client.call_tool("read_file", file_path=str(outside_file))


def test_mcp_write_file_outside_root_error(client: MCPClient, tmp_path: Path):
    """Tests write_file error for a file outside the allowed root directory."""
    outside_file = tmp_path.parent / "outside_write.txt"
    with pytest.raises(MCPError, match=r"Path '.*outside_write.txt' is outside the allowed root directory"):
        client.call_tool("write_file", file_path=str(outside_file), content="Attempt to write outside.")


def test_mcp_replace_string_outside_root_error(client: MCPClient, tmp_path: Path):
    """Tests edit_file_replace_string error for a file outside the allowed root directory."""
    outside_file = tmp_path.parent / "outside_replace.txt"
    outside_file.write_text("original content")
    with pytest.raises(MCPError, match=r"Path '.*outside_replace.txt' is outside the allowed root directory"):
        client.call_tool("edit_file_replace_string", file_path=str(outside_file), old_string="original", new_string="new")


def test_mcp_replace_lines_outside_root_error(client: MCPClient, tmp_path: Path):
    """Tests edit_file_replace_lines error for a file outside the allowed root directory."""
    outside_file = tmp_path.parent / "outside_replace_lines.txt"
    outside_file.write_text("line1\nline2")
    with pytest.raises(MCPError, match=r"Path '.*outside_replace_lines.txt' is outside the allowed root directory"):
        client.call_tool("edit_file_replace_lines", file_path=str(outside_file), start_line=1, end_line=1, new_string="newline")


def test_mcp_delete_files_outside_root_error(client: MCPClient, tmp_path: Path):
    """Tests delete_files error for a file outside the allowed root directory."""
    outside_file = tmp_path.parent / "outside_delete.txt"
    outside_file.write_text("delete me")
    with pytest.raises(MCPError, match=r"Path '.*outside_delete.txt' is outside the allowed root directory"):
        client.call_tool("delete_files", file_paths=[str(outside_file)])


def test_mcp_move_files_source_outside_root_error(client: MCPClient, tmp_path: Path):
    """Tests move_files error when source is outside the allowed root directory."""
    outside_source = tmp_path.parent / "outside_source.txt"
    outside_source.write_text("source content")
    inside_dest = tmp_path / "inside_dest.txt"
    with pytest.raises(MCPError, match=r"Path '.*outside_source.txt' is outside the allowed root directory"):
        client.call_tool("move_files", source_paths=[str(outside_source)], destination_paths=[str(inside_dest)])


def test_mcp_move_files_destination_outside_root_error(client: MCPClient, tmp_path: Path):
    """Tests move_files error when destination is outside the allowed root directory."""
    inside_source = tmp_path / "inside_source.txt"
    inside_source.write_text("source content")
    outside_dest = tmp_path.parent / "outside_dest.txt"
    with pytest.raises(MCPError, match=r"Path '.*outside_dest.txt' is outside the allowed root directory"):
        client.call_tool("move_files", source_paths=[str(inside_source)], destination_paths=[str(outside_dest)])


def test_mcp_create_directory_outside_root_error(client: MCPClient, tmp_path: Path):
    """Tests create_directory error for a directory outside the allowed root directory."""
    outside_dir = tmp_path.parent / "outside_new_dir"
    with pytest.raises(MCPError, match=r"Path '.*outside_new_dir' is outside the allowed root directory"):
        client.call_tool("create_directory", directory_path=str(outside_dir))


def test_mcp_delete_directory_outside_root_error(client: MCPClient, tmp_path: Path):
    """Tests delete_directory error for a directory outside the allowed root directory."""
    outside_dir = tmp_path.parent / "outside_delete_dir"
    outside_dir.mkdir()
    with pytest.raises(MCPError, match=r"Path '.*outside_delete_dir' is outside the allowed root directory"):
        client.call_tool("delete_directory", directory_path=str(outside_dir))
    with open(temp_file, "r", encoding="utf-8") as f:
        assert f.read() == "Line 1\nReplaced Line 2\nLine 3\n"  # nosec B101


def test_mcp_replace_content_binary(client: MCPClient, temp_binary_file: str):
    """Tests replacing content in a binary file using MCP."""
    old_c = b"\x01\x02"
    new_c = b"\xff\xfe"
    result = client.call_tool(
        "edit_file_replace_string",
        file_path=temp_binary_file,
        old_string=base64.b64encode(old_c).decode(),
        new_string=base64.b64encode(new_c).decode(),
        mode="binary",
    )
    assert "Successfully replaced 1 occurrence(s)" in result  # nosec B101
    with open(temp_binary_file, "rb") as f:
        assert f.read() == b"\x00\xff\xfe\x03\x04\x05\x06\x07\x08\x09"  # nosec B101


def test_mcp_replace_lines(client: MCPClient, temp_file: str):
    """Tests replacing lines in a text file using MCP."""
    new_content = "New line 2\nNew line 3\n"
    result = client.call_tool(
        "edit_file_replace_lines",
        file_path=temp_file,
        start_line=2,
        end_line=3,
        new_string=new_content,
    )
    assert "Successfully replaced lines 2-3" in result  # nosec B101
    with open(temp_file, "r", encoding="utf-8") as f:
        assert f.read() == "Line 1\nNew line 2\nNew line 3\n"  # nosec B101


def test_mcp_delete_files(client: MCPClient, tmp_path: Path):
    """Tests deleting multiple files using MCP."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("content1")
    file2.write_text("content2")

    result = client.call_tool("delete_files", file_paths=[str(file1), str(file2)])
    assert "Successfully deleted 2 file(s)" in result  # nosec B101
    assert not file1.exists()  # nosec B101
    assert not file2.exists()  # nosec B101


def test_mcp_move_files(client: MCPClient, tmp_path: Path):
    """Tests moving files using MCP."""
    source_file = tmp_path / "source.txt"
    destination_file = tmp_path / "destination.txt"
    source_file.write_text("content")

    result = client.call_tool(
        "move_files",
        source_paths=[str(source_file)],
        destination_paths=[str(destination_file)],
    )
    assert "Successfully moved 1 file(s)" in result  # nosec B101
    assert not source_file.exists()  # nosec B101
    assert destination_file.exists()  # nosec B101
    assert destination_file.read_text() == "content"  # nosec B101


def test_mcp_create_directory(client: MCPClient, tmp_path: Path):
    """Tests creating a directory using MCP."""
    new_dir = tmp_path / "new_directory"
    result = client.call_tool("create_directory", directory_path=str(new_dir))
    assert "Successfully created directory" in result  # nosec B101
    assert new_dir.is_dir()  # nosec B101


def test_mcp_delete_directory(client: MCPClient, tmp_path: Path):
    """Tests deleting a directory using MCP."""
    dir_to_delete = tmp_path / "dir_to_delete"
    dir_to_delete.mkdir()
    (dir_to_delete / "file.txt").write_text("content")

    result = client.call_tool("delete_directory", directory_path=str(dir_to_delete))
    assert "Successfully deleted directory" in result  # nosec B101
    assert not dir_to_delete.exists()  # nosec B101


# --- Error handling tests ---


def test_mcp_read_file_not_found_error(client: MCPClient, tmp_path: Path):
    """Tests read_file error for non-existent file."""
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(MCPError, match=r"File not found: .*non_existent.txt"):
        client.call_tool("read_file", file_path=str(non_existent_file))


def test_mcp_write_file_permission_error(client: MCPClient, read_only_dir: Path):
    """Tests write_file error for permission denied."""
    read_only_path = read_only_dir / "test.txt"
    with pytest.raises(MCPError, match=r"Permission denied: cannot write to file"):
        client.call_tool("write_file", file_path=str(read_only_path), content="some content")


def test_mcp_replace_lines_error(client: MCPClient, tmp_path: Path):
    """Tests replace_lines error for non-existent file."""
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(MCPError, match=r"File not found: .*non_existent.txt"):
        client.call_tool(
            "edit_file_replace_lines",
            file_path=str(non_existent_file),
            start_line=1,
            end_line=1,
            new_string="test",
        )


def test_mcp_delete_files_error(client: MCPClient, tmp_path: Path):
    """Tests delete_files error for non-existent file."""
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(
        MCPError,
        match=r"Some files could not be deleted: File not found: .*non_existent.txt",
    ):
        client.call_tool("delete_files", file_paths=[str(non_existent_file)])


def test_mcp_move_files_error(client: MCPClient, tmp_path: Path):
    """Tests move_files error for non-existent source file."""
    non_existent_file = tmp_path / "non_existent.txt"
    target_file = tmp_path / "target.txt"
    with pytest.raises(
        MCPError,
        match=r"Some files could not be moved: Source file not found: .*non_existent.txt",
    ):
        client.call_tool(
            "move_files",
            source_paths=[str(non_existent_file)],
            destination_paths=[str(target_file)],
        )


def test_mcp_create_directory_permission_error(client: MCPClient, read_only_dir: Path):
    """Tests create_directory error for permission denied."""
    invalid_path = read_only_dir / "new_dir"
    with pytest.raises(MCPError, match=r"Permission denied creating directory"):
        client.call_tool("create_directory", directory_path=str(invalid_path))


def test_mcp_delete_directory_not_found_error(client: MCPClient, tmp_path: Path):
    """Tests delete_directory error for non-existent directory."""
    invalid_path = tmp_path / "nonexistent_dir"
    with pytest.raises(MCPError, match=r"Directory not found: .*nonexistent_dir"):
        client.call_tool("delete_directory", directory_path=str(invalid_path))


def test_mcp_unknown_tool_error(client: MCPClient):
    """Tests unknown tool error."""
    with pytest.raises(MCPError, match="Unknown tool"):
        client.call_tool("non_existent_tool")


def test_mcp_server_shutdown_on_eof(client: MCPClient):
    """Tests that the MCP server shuts down on EOF."""
    if client.process.stdin and not client.process.stdin.closed:
        client.process.stdin.close()

    try:
        client.process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        client.process.kill()

    assert client.process.poll() is not None  # nosec B101
