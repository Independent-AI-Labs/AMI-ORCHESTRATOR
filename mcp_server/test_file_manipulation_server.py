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
        result = file_server.read_file(str(non_existent_file))
        assert result is None
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
        result = file_server.write_file(invalid_path, "some content")
        assert result is None
        mock_stdout.write.assert_called_once()
        assert "Error writing to file" in mock_stdout.write.call_args[0][0]

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
        result = file_server.replace_content(str(non_existent_file), "old", "new")
        assert result is None
        mock_stdout.write.assert_called_once()
        output_json = json.loads(mock_stdout.write.call_args[0][0])
        assert "File not found" in output_json["error"]
