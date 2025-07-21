import pytest
import os
import json
import base64

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

@pytest.mark.parametrize("mode, encoding, content_to_write, expected_file_content", [
    ("text", "utf-8", "New content.", "New content."),
    ("binary", "utf-8", base64.b64encode(b"binary data").decode('utf-8'), b"binary data")
])
def test_write_file(file_server, tmp_path, mode, encoding, content_to_write, expected_file_content):
    file_path = tmp_path / "write_test.txt"
    result = file_server.write_file(str(file_path), content_to_write, mode, encoding)
    assert "Successfully wrote" in result

    if mode == "text":
        with open(file_path, "r", encoding=encoding) as f:
            assert f.read() == expected_file_content
    elif mode == "binary":
        with open(file_path, "rb") as f:
            assert f.read() == expected_file_content

def test_write_file_error(file_server):
    # Attempt to write to a read-only directory or invalid path
    invalid_path = "/invalid_path/test.txt"
    with pytest.raises(Exception) as excinfo:
        file_server.write_file(invalid_path, "some content")
    assert "Error writing to file" in str(excinfo.value)

@pytest.mark.parametrize("mode, encoding, old_c, new_c, count, expected_content", [
    ("text", "utf-8", "world", "universe", 0, "Hello, universe!\nThis is a test.\n"),
    ("text", "utf-8", "test", "example", 1, "Hello, world!\nThis is a example.\n"),
    ("binary", "utf-8", base64.b64encode(b"\x01\x02").decode('utf-8'), base64.b64encode(b"\xff\xfe").decode('utf-8'), 0, b"\x00\xff\xfe\x03\x04\x05\x06\x07\x08\x09")
])
def test_edit_file_replace_string(file_server, temp_file, temp_binary_file, mode, encoding, old_c, new_c, count, expected_content):
    if mode == "text":
        file_path = temp_file
    else:
        file_path = temp_binary_file

    result = file_server.edit_file_replace_string(file_path, old_c, new_c, mode, encoding, count)
    assert "Successfully replaced" in result or "No changes made" in result

    if mode == "text":
        with open(file_path, "r", encoding=encoding) as f:
            assert f.read() == expected_content
    else:
        with open(file_path, "rb") as f:
            assert f.read() == expected_content

def test_edit_file_replace_string_not_found(file_server, temp_file):
    result = file_server.edit_file_replace_string(temp_file, "non_existent_phrase", "something_new")
    assert "No changes made" in result

def test_edit_file_replace_string_error(file_server, tmp_path):
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(Exception) as excinfo:
        file_server.edit_file_replace_string(str(non_existent_file), "old", "new")
    assert "File not found" in str(excinfo.value)

@pytest.mark.parametrize("start_line, end_line, new_content, expected_content", [
    (1, 1, "New first line.\n", "New first line.\nThis is a test.\n"),
    (2, 2, "Replaced second line.\n", "Hello, world!\nReplaced second line.\n"),
    (1, 2, "New content for both lines.\n", "New content for both lines.\n"),
    (1, 2, "", ""), # Replace with empty content
])
def test_edit_file_replace_lines(file_server, tmp_path, start_line, end_line, new_content, expected_content):
    file_path = tmp_path / "replace_lines_test.txt"
    initial_content = "Hello, world!\nThis is a test.\n"
    with open(file_path, "w") as f:
        f.write(initial_content)

    result = file_server.edit_file_replace_lines(str(file_path), start_line, end_line, new_content)
    assert "Successfully replaced" in result

    with open(file_path, "r") as f:
        assert f.read() == expected_content

@pytest.mark.parametrize("start_line, end_line, new_content, error_message", [
    (3, 3, "New third line.\n", "Start line 3 exceeds file length (2 lines)"),
    (1, 3, "Line 1.\nLine 2.\nLine 3.\n", "Line 1.\nLine 2.\nLine 3.\n"), # Replace all lines
    (3, 3, "New third line.\n", "Hello, world!\nThis is a test.\nNew third line.\n"), # Add a new line at the end
])
def test_edit_file_replace_lines(file_server, tmp_path, start_line, end_line, new_content, expected_content):
    file_path = tmp_path / "replace_lines_test.txt"
    initial_content = "Hello, world!\nThis is a test.\n"
    with open(file_path, "w") as f:
        f.write(initial_content)

    result = file_server.edit_file_replace_lines(str(file_path), start_line, end_line, new_content)
    assert "Successfully replaced" in result

    with open(file_path, "r") as f:
        assert f.read() == expected_content

@pytest.mark.parametrize("start_line, end_line, new_content, error_message", [
    (10, 10, "some content", "Start line 10 exceeds file length"),
    (2, 1, "some content", "Start line (2) must be less than or equal to end line (1)"),
    (1, 1, "some content", "File not found"),
])
def test_edit_file_replace_lines_error_cases(file_server, tmp_path, start_line, end_line, new_content, error_message):
    file_path = tmp_path / "replace_lines_test.txt"
    initial_content = "Hello, world!\nThis is a test.\n"
    with open(file_path, "w") as f:
        f.write(initial_content)

    with pytest.raises(Exception) as excinfo:
        file_server.edit_file_replace_lines(str(file_path), start_line, end_line, new_content)
    assert error_message in str(excinfo.value)

def test_edit_file_replace_lines_file_not_found(file_server, tmp_path):
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(Exception) as excinfo:
        file_server.edit_file_replace_lines(str(non_existent_file), 1, 1, "some content")
    assert "File not found" in str(excinfo.value)

def test_edit_file_replace_lines_out_of_range(file_server, temp_file):
    with pytest.raises(Exception) as excinfo:
        file_server.edit_file_replace_lines(temp_file, 10, 10, "some content")
    assert "Start line 10 exceeds file length" in str(excinfo.value)

def test_edit_file_replace_lines_invalid_range(file_server, temp_file):
    with pytest.raises(Exception) as excinfo:
        file_server.edit_file_replace_lines(temp_file, 2, 1, "some content")
    assert "Start line (2) must be less than or equal to end line (1)" in str(excinfo.value)

def test_edit_file_replace_lines_file_not_found(file_server, tmp_path):
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(Exception) as excinfo:
        file_server.edit_file_replace_lines(str(non_existent_file), 1, 1, "some content")
    assert "File not found" in str(excinfo.value)
def test_edit_file_replace_lines(file_server, tmp_path, start_line, end_line, new_content, expected_content):
    file_path = tmp_path / "replace_lines_test.txt"
    initial_content = "Hello, world!\nThis is a test.\n"
    with open(file_path, "w") as f:
        f.write(initial_content)

    result = file_server.edit_file_replace_lines(str(file_path), start_line, end_line, new_content)
    assert "Successfully replaced" in result

    with open(file_path, "r") as f:
        assert f.read() == expected_content

def test_edit_file_replace_lines_out_of_range(file_server, temp_file):
    with pytest.raises(Exception) as excinfo:
        file_server.edit_file_replace_lines(temp_file, 10, 10, "some content")
    assert "Start line 10 exceeds file length" in str(excinfo.value)

def test_edit_file_replace_lines_invalid_range(file_server, temp_file):
    with pytest.raises(Exception) as excinfo:
        file_server.edit_file_replace_lines(temp_file, 2, 1, "some content")
    assert "Start line (2) must be less than or equal to end line (1)" in str(excinfo.value)

def test_edit_file_replace_lines_file_not_found(file_server, tmp_path):
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(Exception) as excinfo:
        file_server.edit_file_replace_lines(str(non_existent_file), 1, 1, "some content")
    assert "File not found" in str(excinfo.value)

def test_list_tools(file_server):
    tools = file_server.get_tool_declarations()
    assert isinstance(tools, list)
    assert len(tools) == 6

    tool_names = [tool["name"] for tool in tools]
    assert "write_file" in tool_names
    assert "edit_file_replace_string" in tool_names
    assert "edit_file_replace_lines" in tool_names
    assert "delete_files" in tool_names
    assert "create_directory" in tool_names
    assert "delete_directory" in tool_names

    # Verify structure of a sample tool (write_file)
    write_file_tool = next(tool for tool in tools if tool["name"] == "write_file")
    assert write_file_tool["description"] == "Writes content to a file. Creates parent directories if they don't exist. Supports both text and binary modes."
    assert "inputSchema" in write_file_tool
    assert "file_path" in write_file_tool["inputSchema"]["properties"]
    assert "content" in write_file_tool["inputSchema"]["properties"]
    assert "mode" in write_file_tool["inputSchema"]["properties"]
    assert "encoding" in write_file_tool["inputSchema"]["properties"]
    assert "file_path" in write_file_tool["inputSchema"]["required"]
    assert "content" in write_file_tool["inputSchema"]["required"]
