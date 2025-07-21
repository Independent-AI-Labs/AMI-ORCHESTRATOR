import pytest
import os
import time
import json
import base64
import sys
from subprocess import Popen, PIPE, STDOUT

# Define paths relative to the project root
SERVER_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "file_manipulation_server.py"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

@pytest.fixture(scope="module")
def mcp_server_process():
    # Start the MCP server
    process = Popen(
        [sys.executable, SERVER_SCRIPT],
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT,
        cwd=PROJECT_ROOT,
        # Use CREATE_NEW_PROCESS_GROUP for Windows to ensure process group termination
        creationflags=0x00000200 if sys.platform == "win32" else 0
    )
    # Give the server a moment to start up
    time.sleep(2)
    yield process
    # Teardown: Terminate the server process
    if process.poll() is None:
        if sys.platform == "win32":
            # Terminate the process group on Windows
            Popen(["taskkill", "/F", "/T", "/PID", str(process.pid)], stdout=PIPE, stderr=PIPE).wait()
        else:
            # Terminate the process group on Unix-like systems
            os.killpg(os.getpgid(process.pid), 9) # SIGKILL
        process.wait()


def send_mcp_request(process, tool_name: str, **tool_args):
    request = {"tool_name": tool_name, "tool_args": tool_args}
    process.stdin.write((json.dumps(request) + '\n').encode('utf-8'))
    process.stdin.flush()
    response_line = process.stdout.readline()
    return json.loads(response_line)

@pytest.fixture
def temp_integration_file(tmp_path):
    file_path = tmp_path / "integration_test_file.txt"
    with open(file_path, "w") as f:
        f.write("Line 1\nLine 2\nLine 3\n")
    return str(file_path)

@pytest.fixture
def temp_integration_binary_file(tmp_path):
    file_path = tmp_path / "integration_test_binary_file.bin"
    content = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"
    with open(file_path, "wb") as f:
        f.write(content)
    return str(file_path)

def test_mcp_read_file_text(mcp_server_process, temp_integration_file):
    response = send_mcp_request(mcp_server_process, "read_file", file_path=temp_integration_file, mode="text")
    assert response["result"] == "Line 1\nLine 2\nLine 3\n"

def test_mcp_read_file_binary(mcp_server_process, temp_integration_binary_file):
    response = send_mcp_request(mcp_server_process, "read_file", file_path=temp_integration_binary_file, mode="binary")
    expected_content_b64 = base64.b64encode(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09").decode('utf-8')
    assert response["result"] == expected_content_b64

def test_mcp_write_file_text(mcp_server_process, tmp_path):
    file_path = tmp_path / "write_test.txt"
    response = send_mcp_request(mcp_server_process, "write_file", file_path=str(file_path), content="New text content.", mode="text")
    assert response["result"] == "Success"
    with open(file_path, "r") as f:
        assert f.read() == "New text content."

def test_mcp_write_file_binary(mcp_server_process, tmp_path):
    file_path = tmp_path / "write_binary_test.bin"
    content_b64 = base64.b64encode(b"\x0a\x0b\x0c").decode('utf-8')
    response = send_mcp_request(mcp_server_process, "write_file", file_path=str(file_path), content=content_b64, mode="binary")
    assert response["result"] == "Success"
    with open(file_path, "rb") as f:
        assert f.read() == b"\x0a\x0b\x0c"

def test_mcp_replace_content_text(mcp_server_process, temp_integration_file):
    old_c = "Line 2"
    new_c = "Replaced Line 2"
    response = send_mcp_request(mcp_server_process, "replace_content", file_path=temp_integration_file, old_content=old_c, new_content=new_c, mode="text")
    assert response["result"] == "Success"
    with open(temp_integration_file, "r") as f:
        assert f.read() == "Line 1\nReplaced Line 2\nLine 3\n"

def test_mcp_replace_content_binary(mcp_server_process, temp_integration_binary_file):
    old_c = b"\x01\x02"
    new_c = b"\xff\xfe"
    response = send_mcp_request(mcp_server_process, "replace_content", file_path=temp_integration_binary_file, old_content=base64.b64encode(old_c).decode(), new_content=base64.b64encode(new_c).decode(), mode="binary")
    assert response["result"] == "Success"
    with open(temp_integration_binary_file, "rb") as f:
        assert f.read() == b"\x00\xff\xfe\x03\x04\x05\x06\x07\x08\x09"

def test_mcp_replace_lines(mcp_server_process, temp_integration_file):
    new_content = "New line 2\nNew line 3\n"
    response = send_mcp_request(mcp_server_process, "replace_lines", file_path=temp_integration_file, start_line=2, end_line=3, new_content=new_content)
    assert response["result"] == "Success"
    with open(temp_integration_file, "r") as f:
        assert f.read() == "Line 1\nNew line 2\nNew line 3\n"

def test_mcp_read_file_not_found_error(mcp_server_process, tmp_path):
    non_existent_file = tmp_path / "non_existent.txt"
    response = send_mcp_request(mcp_server_process, "read_file", file_path=str(non_existent_file))
    assert "error" in response
    assert "File not found" in response["error"]

def test_mcp_write_file_error(mcp_server_process):
    invalid_path = "/invalid_path/test.txt"
    response = send_mcp_request(mcp_server_process, "write_file", file_path=invalid_path, content="some content")
    assert "error" in response
    assert "Error writing to file" in response["error"]

def test_mcp_replace_content_error(mcp_server_process, tmp_path):
    non_existent_file = tmp_path / "non_existent.txt"
    response = send_mcp_request(mcp_server_process, "replace_content", file_path=str(non_existent_file), old_content=base64.b64encode(b"old").decode(), new_content=base64.b64encode(b"new").decode())
    assert "error" in response
    assert "File not found" in response["error"]

def test_mcp_replace_lines_error(mcp_server_process, tmp_path):
    non_existent_file = tmp_path / "non_existent.txt"
    response = send_mcp_request(mcp_server_process, "replace_lines", file_path=str(non_existent_file), start_line=1, end_line=1, new_content="test")
    assert "error" in response
    assert "File not found" in response["error"]
