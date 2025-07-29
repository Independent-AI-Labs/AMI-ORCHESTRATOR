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
from subprocess import Popen

import pytest
import yaml

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
        raw_result = response["result"]["content"][0]["text"]
        # For tools that are expected to return structured YAML output, attempt to parse it.
        # If parsing fails, it indicates an unexpected format, which should be treated as an error.
        if tool_name in [
            "write_file",
            "edit_file_replace_string",
            "edit_file_replace_lines",
            "edit_file_delete_lines",
            "edit_file_insert_lines",
            "delete_files",
            "move_files",
            "create_directory",
            "delete_directory",
        ]:
            try:
                return yaml.safe_load(raw_result)
            except yaml.YAMLError as e:
                raise ValueError(f"Failed to parse YAML output for tool {tool_name}: {raw_result}") from e
        # For other tools, return the raw string result.
        return raw_result


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
                        # `taskkill` is a trusted system executable, and `process.pid` is an integer, not untrusted input.
                        check=False,
                        capture_output=True,
                        shell=False,
                    )
                else:
                    try:
                        # pylint: disable=no-member
                        pgid = process.pid  # os.getpgid(process.pid)
                        signal.signal(signal.SIGTERM, signal.SIG_IGN)
                        os.killpg(pgid, signal.SIGTERM)  # pylint: disable=no-member
                    except OSError:
                        pass  # Process already gone
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


def test_mcp_list_tools(client: MCPClient):
    """Tests the list_tools MCP command."""
    tools = client.list_tools()
    assert isinstance(tools, list)  # nosec B101
    assert len(tools) > 0  # nosec B101
    assert any(tool["name"] == "read_file" for tool in tools)  # nosec B101


def test_mcp_read_file_text(client: MCPClient, temp_file: str):
    """Tests reading a text file using MCP."""
    result = client.call_tool("read_file", file_path=temp_file, mode="text")
    assert result == "1: Line 1\n2: Line 2\n3: Line 3\n"  # nosec B101


def test_mcp_read_file_binary(client: MCPClient, temp_binary_file: str):
    """Tests reading a binary file using MCP."""
    result = client.call_tool("read_file", file_path=temp_binary_file, mode="binary")
    expected_content_b64 = base64.b64encode(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09").decode("utf-8")
    assert result == expected_content_b64  # nosec B101


def test_mcp_write_file_text(client: MCPClient):
    """Tests writing a text file using MCP."""
    file_path = Path(client.root_dir) / "write_test.txt"
    result = client.call_tool("write_file", file_path=str(file_path), content="New text content.", mode="text")
    assert "Successfully wrote text content" in result["message"]  # nosec B101
    assert file_path.read_text() == "New text content."  # nosec B101


def test_mcp_write_file_binary(client: MCPClient):
    """Tests writing a binary file using MCP."""
    file_path = Path(client.root_dir) / "write_binary_test.bin"
    content_b64 = base64.b64encode(b"\x0a\x0b\x0c").decode("utf-8")
    result = client.call_tool("write_file", file_path=str(file_path), content=content_b64, mode="binary")
    assert "Successfully wrote binary content" in result["message"]  # nosec B101
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
    assert "Successfully replaced 1 occurrence(s)" in result["message"]  # nosec B101


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


def test_mcp_replace_string_outside_root_error(client: MCPClient):
    """Tests edit_file_replace_string error for a file outside the allowed root directory."""
    outside_file = Path(client.root_dir).parent / "outside_replace.txt"
    outside_file.write_text("original content")
    with pytest.raises(MCPError, match=r"Path '.*outside_replace.txt' is outside the allowed root directory"):
        client.call_tool("edit_file_replace_string", file_path=str(outside_file), old_string="original", new_string="new")


def test_mcp_replace_lines_outside_root_error(client: MCPClient):
    """Tests edit_file_replace_lines error for a file outside the allowed root directory."""
    outside_file = Path(client.root_dir).parent / "outside_replace_lines.txt"
    outside_file.write_text("line1\nline2")
    with pytest.raises(MCPError, match=r"Path '.*outside_replace_lines.txt' is outside the allowed root directory"):
        client.call_tool("edit_file_replace_lines", file_path=str(outside_file), start_line=1, end_line=1, new_string="newline")


def test_mcp_delete_files_outside_root_error(client: MCPClient):
    """Tests delete_files error for a file outside the allowed root directory."""
    outside_file = Path(client.root_dir).parent / "outside_delete.txt"
    outside_file.write_text("delete me")
    with pytest.raises(MCPError, match=r"Path '.*outside_delete.txt' is outside the allowed root directory"):
        client.call_tool("delete_files", file_paths=[str(outside_file)])


def test_mcp_move_files_source_outside_root_error(client: MCPClient):
    """Tests move_files error when source is outside the allowed root directory."""
    outside_source = Path(client.root_dir).parent / "outside_source.txt"
    outside_source.write_text("source content")
    inside_dest = Path(client.root_dir) / "inside_dest.txt"
    with pytest.raises(MCPError, match=r"Path '.*outside_source.txt' is outside the allowed root directory"):
        client.call_tool("move_files", source_paths=[str(outside_source)], destination_paths=[str(inside_dest)])


def test_mcp_move_files_destination_outside_root_error(client: MCPClient):
    """Tests move_files error when destination is outside the allowed root directory."""
    inside_source = Path(client.root_dir) / "inside_source.txt"
    inside_source.write_text("source content")
    outside_dest = Path(client.root_dir).parent / "outside_dest.txt"
    with pytest.raises(MCPError, match=r"Path '.*outside_dest.txt' is outside the allowed root directory"):
        client.call_tool("move_files", source_paths=[str(inside_source)], destination_paths=[str(outside_dest)])


def test_mcp_create_directory_outside_root_error(client: MCPClient):
    """Tests create_directory error for a directory outside the allowed root directory."""
    outside_dir = Path(client.root_dir).parent / "outside_new_dir"
    with pytest.raises(MCPError, match=r"Path '.*outside_new_dir' is outside the allowed root directory"):
        client.call_tool("create_directory", directory_path=str(outside_dir))


def test_mcp_delete_directory_outside_root_error(client: MCPClient):
    """Tests delete_directory error for a directory outside the allowed root directory."""
    outside_dir = Path(client.root_dir).parent / "outside_delete_dir"
    outside_dir.mkdir()
    with pytest.raises(MCPError, match=r"Path '.*outside_delete_dir' is outside the allowed root directory"):
        client.call_tool("delete_directory", directory_path=str(outside_dir))


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
    assert "Successfully replaced 1 occurrence(s)" in result["message"]  # nosec B101
    with Path(temp_binary_file).open("rb") as f:
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
    assert "Successfully replaced lines 2-3" in result["message"]  # nosec B101
    with Path(temp_file).open(encoding="utf-8") as f:
        assert f.read() == "Line 1\nNew line 2\nNew line 3\n"  # nosec B101


def test_mcp_insert_lines(client: MCPClient, temp_file: str):
    """Tests inserting lines in a text file using MCP."""
    new_content = "Inserted Line\n"
    result = client.call_tool(
        "edit_file_insert_lines",
        file_path=temp_file,
        line_number=2,
        content=new_content,
    )
    assert "Successfully inserted content at line" in result["message"]
    with Path(temp_file).open(encoding="utf-8") as f:
        assert f.read() == "Line 1\nInserted Line\nLine 2\nLine 3\n"


def test_mcp_delete_lines(client: MCPClient, temp_file: str):
    """Tests deleting lines in a text file using MCP."""
    result = client.call_tool(
        "edit_file_delete_lines",
        file_path=temp_file,
        start_line=2,
        end_line=2,
    )
    assert "Successfully deleted lines 2-2 (1 lines)" in result["message"]
    with Path(temp_file).open(encoding="utf-8") as f:
        assert f.read() == "Line 1\nLine 3\n"


def test_mcp_insert_lines_append(client: MCPClient, temp_file: str):
    """Tests appending lines to a text file using MCP."""
    path = Path(temp_file)
    original_content = path.read_text()
    num_lines = len(original_content.splitlines())

    new_content = "Appended Line\n"
    result = client.call_tool(
        "edit_file_insert_lines",
        file_path=temp_file,
        line_number=num_lines + 1,
        content=new_content,
    )
    assert "Successfully inserted content at line" in result["message"]
    with path.open(encoding="utf-8") as f:
        assert f.read() == "Line 1\nLine 2\nLine 3\nAppended Line\n"


def test_mcp_read_file_raw_response_format(client: MCPClient, temp_file: str):
    """Tests that a string result from a tool is not formatted as YAML."""
    # The bug fix was to ensure that string results are not dumped as YAML.
    # A direct string result should be returned as is.
    result = client.call_tool("read_file", file_path=temp_file, mode="text")
    assert result == "1: Line 1\n2: Line 2\n3: Line 3\n"
    # If it were YAML, it might have quotes or document separators.
    assert not result.startswith("'")
    assert not result.endswith("'\n")
    assert "---" not in result


def test_mcp_delete_files(client: MCPClient):
    """Tests deleting multiple files using MCP."""
    file1 = Path(client.root_dir) / "file1.txt"
    file2 = Path(client.root_dir) / "file2.txt"
    file1.write_text("content1")
    file2.write_text("content2")

    result = client.call_tool("delete_files", file_paths=[str(file1), str(file2)])
    assert "Successfully deleted 2 file(s)" in result["message"]  # nosec B101
    assert not file1.exists()  # nosec B101
    assert not file2.exists()  # nosec B101


def test_mcp_move_files(client: MCPClient):
    """Tests moving files using MCP."""
    source_file = Path(client.root_dir) / "source.txt"
    destination_file = Path(client.root_dir) / "destination.txt"
    source_file.write_text("content")

    result = client.call_tool(
        "move_files",
        source_paths=[str(source_file)],
        destination_paths=[str(destination_file)],
    )
    assert "Successfully moved 1 file(s)" in result["message"]  # nosec B101
    assert not source_file.exists()  # nosec B101
    assert destination_file.exists()  # nosec B101
    assert destination_file.read_text() == "content"  # nosec B101


def test_mcp_create_directory(client: MCPClient):
    """Tests creating a directory using MCP."""
    new_dir = Path(client.root_dir) / "new_directory"
    result = client.call_tool("create_directory", directory_path=str(new_dir))
    assert "Successfully created directory" in result["message"]  # nosec B101
    assert new_dir.is_dir()  # nosec B101


def test_mcp_delete_directory(client: MCPClient):
    """Tests deleting a directory using MCP."""
    dir_to_delete = Path(client.root_dir) / "dir_to_delete"
    dir_to_delete.mkdir()
    (dir_to_delete / "file.txt").write_text("content")

    result = client.call_tool("delete_directory", directory_path=str(dir_to_delete))
    assert "Successfully deleted directory" in result["message"]  # nosec B101
    assert not dir_to_delete.exists()  # nosec B101


# --- Error handling tests ---


def test_mcp_read_file_not_found_error(client: MCPClient):
    """Tests read_file error for non-existent file."""
    non_existent_file = Path(client.root_dir) / "non_existent.txt"
    with pytest.raises(MCPError, match=r"File not found: .*non_existent.txt"):
        client.call_tool("read_file", file_path=str(non_existent_file))


def test_mcp_write_file_permission_error(client: MCPClient, read_only_dir: Path):
    """Tests write_file error for permission denied."""
    read_only_path = read_only_dir / "test.txt"
    with pytest.raises(MCPError, match=r"Permission denied"):
        client.call_tool("write_file", file_path=str(read_only_path), content="some content")


def test_mcp_replace_lines_error(client: MCPClient):
    """Tests replace_lines error for non-existent file."""
    non_existent_file = Path(client.root_dir) / "non_existent.txt"
    with pytest.raises(MCPError, match=r"File not found: .*non_existent.txt"):
        client.call_tool(
            "edit_file_replace_lines",
            file_path=str(non_existent_file),
            start_line=1,
            end_line=1,
            new_string="test",
        )


def test_mcp_delete_files_error(client: MCPClient):
    """Tests delete_files error for non-existent file."""
    non_existent_file = Path(client.root_dir) / "non_existent.txt"
    with pytest.raises(
        MCPError,
        match=r"Some files could not be deleted: File not found: .*non_existent.txt",
    ):
        client.call_tool("delete_files", file_paths=[str(non_existent_file)])


def test_mcp_move_files_error(client: MCPClient):
    """Tests move_files error for non-existent source file."""
    non_existent_file = Path(client.root_dir) / "non_existent.txt"
    target_file = Path(client.root_dir) / "target.txt"
    with pytest.raises(
        MCPError,
        match=(
            r"Internal server error during tool 'move_files' execution: "
            "Some files could not be moved: Failed to move '.*' to '.*': "
            "Source file not found: '.*'"
        ),
    ):
        client.call_tool(
            "move_files",
            source_paths=[str(non_existent_file)],
            destination_paths=[str(target_file)],
        )


@pytest.mark.skipif(sys.platform == "win32", reason="This test is unreliable on Windows due to os.chmod behavior on directories.")
def test_mcp_create_directory_permission_error(client: MCPClient, read_only_dir: Path):
    """Tests create_directory error for permission denied."""
    invalid_path = read_only_dir / "new_dir"
    with pytest.raises(MCPError, match=r"Permission denied"):
        client.call_tool("create_directory", directory_path=str(invalid_path))


def test_mcp_delete_directory_not_found_error(client: MCPClient):
    """Tests delete_directory error for non-existent directory."""
    invalid_path = Path(client.root_dir) / "nonexistent_dir"
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
