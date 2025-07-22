import os
import pytest

from orchestrator.mcp.servers.local_file_server import LocalFiles


@pytest.fixture
def files_instance():
    return LocalFiles()

def test_write_file_and_read_file(files_instance, tmp_path):
    file_path = tmp_path / "test_file.txt"
    content = "Hello, world!"

    files_instance.write_file(str(file_path), content, 'text')

    read_content = files_instance.read_file(str(file_path), 'text')
    assert read_content == content + '\n' # Expect trailing newline

def test_write_file_error(files_instance):
    # Test writing to a non-existent directory without creating it
    invalid_path = "/nonexistent_dir_12345/test_file.txt"
    with pytest.raises(Exception) as excinfo:
        files_instance.write_file(invalid_path, "content", 'text')
    assert "Write operation failed" in str(excinfo.value)

def test_edit_file_replace_string(files_instance, tmp_path):
    file_path = tmp_path / "replace_test.txt"
    file_path.write_text("Hello, world!", newline='') # Ensure consistent line endings

    files_instance.edit_file_replace_string(str(file_path), "world!", "Python!")

    read_content = files_instance.read_file(str(file_path), 'text')
    assert read_content == "Hello, Python!\n" # Expect trailing newline

def test_edit_file_replace_string_error(files_instance):
    # Test replacing string in a non-existent file
    invalid_path = "/nonexistent_dir_12345/nonexistent_file.txt"
    with pytest.raises(Exception) as excinfo:
        files_instance.edit_file_replace_string(invalid_path, "old", "new")
    assert "String replacement failed" in str(excinfo.value)

def test_edit_file_replace_lines(files_instance, tmp_path):
    file_path = tmp_path / "replace_lines_test.txt"
    file_path.write_text("line1\nline2\nline3\nline4\nline5", newline='') # Ensure consistent line endings

    files_instance.edit_file_replace_lines(str(file_path), 2, 4, "newlineA\nnewlineB")

    read_content = files_instance.read_file(str(file_path), 'text')
    assert read_content == "line1\nnewlineA\nnewlineB\nline5\n"

def test_edit_file_replace_lines_error(files_instance):
    # Test replacing lines in a non-existent file
    invalid_path = "/nonexistent_dir_12345/nonexistent_file.txt"
    with pytest.raises(Exception) as excinfo:
        files_instance.edit_file_replace_lines(invalid_path, 1, 2, "new content")
    assert "Line replacement failed" in str(excinfo.value)

def test_edit_file_delete_lines(files_instance, tmp_path):
    file_path = tmp_path / "delete_lines_test.txt"
    file_path.write_text("line1\nline2\nline3\nline4\nline5", newline='') # Ensure consistent line endings

    files_instance.edit_file_delete_lines(str(file_path), 2, 3)

    read_content = files_instance.read_file(str(file_path), 'text')
    assert read_content == "line1\nline4\nline5\n"

def test_edit_file_delete_lines_error(files_instance):
    # Test deleting lines from a non-existent file
    invalid_path = "/nonexistent_dir_12345/nonexistent_file.txt"
    with pytest.raises(Exception) as excinfo:
        files_instance.edit_file_delete_lines(invalid_path, 1, 2)
    assert "Line deletion failed" in str(excinfo.value)

def test_edit_file_insert_lines(files_instance, tmp_path):
    file_path = tmp_path / "insert_lines_test.txt"
    file_path.write_text("line1\nline4\n", newline='') # Ensure consistent line endings

    files_instance.edit_file_insert_lines(str(file_path), 2, "line2\nline3\n")

    read_content = files_instance.read_file(str(file_path), 'text')
    assert read_content == "line1\nline2\nline3\nline4\n"

def test_edit_file_insert_lines_error(files_instance):
    # Test inserting lines into a non-existent file
    invalid_path = "/nonexistent_dir_12345/nonexistent_file.txt"
    with pytest.raises(Exception) as excinfo:
        files_instance.edit_file_insert_lines(invalid_path, 1, "new content")
    assert "Line insertion failed" in str(excinfo.value)

def test_delete_files(files_instance, tmp_path):
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("content1")
    file2.write_text("content2")

    files_instance.delete_files([str(file1), str(file2)])

    assert not file1.exists()
    assert not file2.exists()

def test_delete_files_error(files_instance, tmp_path):
    # Test deleting a non-existent file
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(Exception) as excinfo:
        files_instance.delete_files([str(non_existent_file)])
    assert "Some files could not be deleted" in str(excinfo.value)

def test_move_files(files_instance, tmp_path):
    source_file = tmp_path / "source.txt"
    destination_file = tmp_path / "destination.txt"
    source_file.write_text("content")

    files_instance.move_files([str(source_file)], [str(destination_file)])

    assert not source_file.exists()
    assert destination_file.exists()
    assert destination_file.read_text() == "content"

def test_move_files_error(files_instance, tmp_path):
    # Test moving a non-existent file
    non_existent_file = tmp_path / "non_existent.txt"
    target_file = tmp_path / "target.txt"
    with pytest.raises(Exception) as excinfo:
        files_instance.move_files([str(non_existent_file)], [str(target_file)])
    assert "Some files could not be moved" in str(excinfo.value)

def test_create_directory(files_instance, tmp_path):
    new_dir = tmp_path / "new_directory"
    files_instance.create_directory(str(new_dir))
    assert new_dir.is_dir()

def test_create_directory_error(files_instance):
    # Test creating a directory in an invalid path (e.g., root of a non-existent drive)
    # This should raise an OSError or similar, which is caught by the LocalFiles class
    invalid_path = "Z:/invalid_root_dir_12345/new_dir"
    with pytest.raises(Exception) as excinfo:
        files_instance.create_directory(invalid_path)
    assert "Failed to create directory" in str(excinfo.value)

def test_delete_directory(files_instance, tmp_path):
    dir_to_delete = tmp_path / "dir_to_delete"
    dir_to_delete.mkdir()
    (dir_to_delete / "file.txt").write_text("content")

    files_instance.delete_directory(str(dir_to_delete))
    assert not dir_to_delete.exists()

def test_delete_directory_error(files_instance):
    # Test deleting a non-existent directory
    invalid_path = "/nonexistent_dir_12345/dir_to_delete"
    with pytest.raises(Exception) as excinfo:
        files_instance.delete_directory(invalid_path)
    assert "Failed to delete directory" in str(excinfo.value)