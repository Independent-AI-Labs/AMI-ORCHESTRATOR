import asyncio
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from orchestrator.mcp_server.file_manipulation_server import Files

@pytest.fixture
def files_instance():
    return Files()

def test_write_file_and_read_file(files_instance):
    with tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix=".txt") as tmpfile:
        file_path = tmpfile.name
        content = "Hello, world!"

    files_instance.write_file(file_path, content, 'text')

    read_content = files_instance.read_file(file_path, 'text')
    assert read_content == content

    os.remove(file_path)

def test_write_file_error(files_instance):
    with pytest.raises(Exception) as excinfo:
        files_instance.write_file("/nonexistent/path/to/file.txt", "content", 'text')
    assert "Write operation failed" in str(excinfo.value)

def test_edit_file_replace_string(files_instance):
    with tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix=".txt") as tmpfile:
        file_path = tmpfile.name
        tmpfile.write("Hello, world!")

    files_instance.edit_file_replace_string(file_path, "world", "Python")

    read_content = files_instance.read_file(file_path, 'text')
    assert read_content == "Hello, Python!"

    os.remove(file_path)

def test_edit_file_replace_string_error(files_instance):
    with pytest.raises(Exception) as excinfo:
        files_instance.edit_file_replace_string("/nonexistent/path/to/file.txt", "old", "new")
    assert "String replacement failed" in str(excinfo.value)


def test_edit_file_replace_lines(files_instance):
    with tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix=".txt") as tmpfile:
        file_path = tmpfile.name
        tmpfile.write("line1\nline2\nline3\nline4\nline5")

    files_instance.edit_file_replace_lines(file_path, 2, 4, "newlineA\nnewlineB")

    read_content = files_instance.read_file(file_path, 'text')
    assert read_content == "line1\nnewlineA\nnewlineB\nline5"

    os.remove(file_path)

def test_edit_file_replace_lines_error(files_instance):
    with pytest.raises(Exception) as excinfo:
        files_instance.edit_file_replace_lines("/nonexistent/path/to/file.txt", 1, 2, "new content")
    assert "Line replacement failed" in str(excinfo.value)
