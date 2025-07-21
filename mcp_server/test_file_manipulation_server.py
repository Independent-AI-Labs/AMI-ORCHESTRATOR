import pytest
import os
import json
import base64
from unittest.mock import patch, MagicMock

from orchestrator.mcp_server.file_manipulation_server import FileManipulationServer

@pytest.fixture
def file_server():
    return FileManipulationServer()

@pytest.fixture
def temp_file(tmp_path):
    file_path = tmp_path / "test_file.txt"
    with open(file_path, "w") as f:
        f.write("Hello, world!\nThis is a test.\n")
    return str(file_path)

@pytest.fixture
def temp_binary_file(tmp_path):
    file_path = tmp_path / "test_binary_file.bin"
    content = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"
    with open(file_path, "wb") as f:
        f.write(content)
    return str(file_path)

@pytest.mark.parametrize("mode, encoding, expected_content", [
    ("text", "utf-8", "Hello, world!\nThis is a test.\n"),
    ("binary", "utf-8", base64.b64encode(b"Hello, world!\nThis is a test.\n").decode('utf-8'))
])
def test_read_file(file_server, temp_file, mode, encoding, expected_content):
    if mode == "binary":
        # For binary read, ensure the file content is bytes
        with open(temp_file, "wb") as f:
            f.write(b"Hello, world!\nThis is a test.\n")

    result = file_server.read_file(temp_file, mode, encoding)
    assert result == expected_content

def test_read_file_not_found(file_server, tmp_path):
    non_existent_file = tmp_path / "non_existent.txt"
    with patch('sys.stdout', new=MagicMock()) as mock_stdout:
        with patch('sys.stdout', new=MagicMock()) as mock_stdout:
            file_server.read_file(str(non_existent_file))
            mock_stdout.write.assert_called_once()
            output_json = json.loads(mock_stdout.write.call_args[0][0])
            assert "File not found" in output_json["error"]

@pytest.mark.parametrize("mode, encoding, content_to_write, expected_file_content", [
    ("text", "utf-8", "New content.", "New content."),
    ("binary", "utf-8", base64.b64encode(b"binary data").decode('utf-8'), b"binary data")
])
def test_write_file(file_server, tmp_path, mode, encoding, content_to_write, expected_file_content):
    file_path = tmp_path / "write_test.txt"
    result = file_server.write_file(str(file_path), content_to_write, mode, encoding)
    assert result == "Success"

    if mode == "text":
        with open(file_path, "r", encoding=encoding) as f:
            assert f.read() == expected_file_content
    elif mode == "binary":
        with open(file_path, "rb") as f:
            assert f.read() == expected_file_content

def test_write_file_error(file_server):
    # Attempt to write to a read-only directory or invalid path
    invalid_path = "/invalid_path/test.txt"
    with patch('sys.stdout', new=MagicMock()) as mock_stdout:
        file_server.write_file(invalid_path, "some content")
        mock_stdout.write.assert_called_once()
        output_json = json.loads(mock_stdout.write.call_args[0][0])
        assert "Error writing to file" in output_json["error"]

@pytest.mark.parametrize("mode, encoding, old_c, new_c, count, expected_content", [
    ("text", "utf-8", "world", "universe", 0, "Hello, universe!\nThis is a test.\n"),
    ("text", "utf-8", "test", "example", 1, "Hello, world!\nThis is a example.\n"),
    ("binary", "utf-8", base64.b64encode(b"\x01\x02").decode('utf-8'), base64.b64encode(b"\xff\xfe").decode('utf-8'), 0, b"\x00\xff\xfe\x03\x04\x05\x06\x07\x08\x09")
])
def test_replace_content(file_server, temp_file, temp_binary_file, mode, encoding, old_c, new_c, count, expected_content):
    if mode == "text":
        file_path = temp_file
    else:
        file_path = temp_binary_file

    result = file_server.replace_content(file_path, old_c, new_c, mode, encoding, count)
    assert result == "Success"

    if mode == "text":
        with open(file_path, "r", encoding=encoding) as f:
            assert f.read() == expected_content
    else:
        with open(file_path, "rb") as f:
            assert f.read() == expected_content

def test_replace_content_not_found(file_server, temp_file):
    result = file_server.replace_content(temp_file, "non_existent_phrase", "something_new")
    assert result == "No changes made (content not found or already replaced)"

def test_replace_content_error(file_server, tmp_path):
    non_existent_file = tmp_path / "non_existent.txt"
    with patch('sys.stdout', new=MagicMock()) as mock_stdout:
        file_server.replace_content(str(non_existent_file), "old", "new")
        mock_stdout.write.assert_called_once()
        output_json = json.loads(mock_stdout.write.call_args[0][0])
        assert "File not found" in output_json["error"]

@pytest.mark.parametrize("start_line, end_line, new_content, expected_content", [
    (1, 1, "New first line.\n", "New first line.\nThis is a test.\n"),
    (2, 2, "Replaced second line.\n", "Hello, world!\nReplaced second line.\n"),
    (1, 2, "New content for both lines.\n", "New content for both lines.\n"),
    (1, 2, "", ""), # Replace with empty content
    (1, 3, "Line 1.\nLine 2.\nLine 3.\n", "Line 1.\nLine 2.\nLine 3.\n"), # Replace all lines
    (3, 3, "New third line.\n", "Hello, world!\nThis is a test.\nNew third line.\n"), # Add a new line at the end
])
def test_replace_lines(file_server, tmp_path, start_line, end_line, new_content, expected_content):
    file_path = tmp_path / "replace_lines_test.txt"
    initial_content = "Hello, world!\nThis is a test.\n"
    with open(file_path, "w") as f:
        f.write(initial_content)

    result = file_server.replace_lines(str(file_path), start_line, end_line, new_content)
    assert result == "Success"

    with open(file_path, "r") as f:
        assert f.read() == expected_content

def test_replace_lines_out_of_range(file_server, temp_file):
    with patch('sys.stdout', new=MagicMock()) as mock_stdout:
        file_server.replace_lines(temp_file, 10, 10, "some content")
        mock_stdout.write.assert_called_once()
        output_json = json.loads(mock_stdout.write.call_args[0][0])
        assert "Line numbers out of range" in output_json["error"]

def test_replace_lines_invalid_range(file_server, temp_file):
    with patch('sys.stdout', new=MagicMock()) as mock_stdout:
        file_server.replace_lines(temp_file, 2, 1, "some content")
        mock_stdout.write.assert_called_once()
        output_json = json.loads(mock_stdout.write.call_args[0][0])
        assert "Invalid line numbers" in output_json["error"]

def test_replace_lines_file_not_found(file_server, tmp_path):
    non_existent_file = tmp_path / "non_existent.txt"
    with patch('sys.stdout', new=MagicMock()) as mock_stdout:
        file_server.replace_lines(str(non_existent_file), 1, 1, "some content")
        mock_stdout.write.assert_called_once()
        output_json = json.loads(mock_stdout.write.call_args[0][0])
        assert "File not found" in output_json["error"]

def test_list_tools(file_server):
    tools = file_server._list_tools()
    assert isinstance(tools, list)
    assert len(tools) == 4

    tool_names = [tool["name"] for tool in tools]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "replace_content" in tool_names
    assert "replace_lines" in tool_names

    # Verify structure of a sample tool (read_file)
    read_file_tool = next(tool for tool in tools if tool["name"] == "read_file")
    assert read_file_tool["description"] == "Reads content from a file."
    assert "parameters" in read_file_tool
    assert "file_path" in read_file_tool["parameters"]["properties"]
    assert "mode" in read_file_tool["parameters"]["properties"]
    assert "encoding" in read_file_tool["parameters"]["properties"]
    assert "file_path" in read_file_tool["parameters"]["required"]
