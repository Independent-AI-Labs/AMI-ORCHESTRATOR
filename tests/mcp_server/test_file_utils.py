import base64
from quopri import encodestring

import pytest

from orchestrator.mcp.servers.localfs.file_utils import FileUtils, InputFormat, OffsetType, OutputFormat


class TestFileUtils:
    def test_list_directory_contents_non_recursive(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        (root_dir / "file1.txt").touch()
        (root_dir / "file2.txt").touch()
        (root_dir / "subdir1").mkdir()
        (root_dir / "subdir2").mkdir()

        contents = FileUtils.list_directory_contents(str(root_dir), str(root_dir))
        expected_lines = [
            "├───subdir1",
            "├───subdir2",
            "├───file1.txt",
            "└───file2.txt",
        ]
        assert contents.splitlines() == expected_lines

    def test_list_directory_contents_recursive(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        (root_dir / "file1.txt").touch()
        (root_dir / "subdir1").mkdir()
        (root_dir / "subdir1" / "file3.txt").touch()
        (root_dir / "subdir2").mkdir()
        (root_dir / "subdir2" / "file4.txt").touch()
        (root_dir / "subdir2" / "subsubdir1").mkdir()
        (root_dir / "subdir2" / "subsubdir1" / "file5.txt").touch()

        contents = FileUtils.list_directory_contents(str(root_dir), str(root_dir), recursive=True)
        # The expected output needs to be carefully crafted to match the ASCII tree structure
        expected_lines = [
            "├───subdir1",
            "│   └───file3.txt",
            "├───subdir2",
            "│   ├───subsubdir1",
            "│   │   └───file5.txt",
            "│   └───file4.txt",
            "└───file1.txt",
        ]
        # Normalize line endings and split to compare
        actual_lines = contents.splitlines()
        # The order of files and directories is now deterministic, so we can compare directly
        assert actual_lines == expected_lines

    def test_create_dirs(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        new_dir = root_dir / "new_dir" / "subdir"
        result = FileUtils.create_dirs(str(new_dir), str(root_dir))
        assert "Successfully created directory" in result["message"]
        assert new_dir.is_dir()

    def test_find_files_by_path_name(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        (root_dir / "test_file_abc.txt").touch()
        (root_dir / "another_file_xyz.log").touch()
        (root_dir / "subdir" / "nested_abc.txt").mkdir(parents=True)

        found_files = FileUtils.find_files(str(root_dir), str(root_dir), keywords_path_name=["abc"], keywords_file_content=[])
        expected_files = [
            str(root_dir / "test_file_abc.txt"),
        ]
        assert sorted(found_files) == sorted(expected_files)

    def test_find_files_by_content(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        (root_dir / "file_with_content1.txt").write_text("This is a test with keyword1.")
        (root_dir / "file_with_content2.txt").write_text("Another test with keyword2.")
        (root_dir / "binary_file.bin").write_bytes(b"\x00\x01\x02")

        found_files = FileUtils.find_files(str(root_dir), str(root_dir), keywords_path_name=[], keywords_file_content=["keyword1"])
        expected_files = [
            str(root_dir / "file_with_content1.txt"),
        ]
        assert sorted(found_files) == sorted(expected_files)

    def test_read_file_content_text_full(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_text.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3")
        content = FileUtils.read_file_content(str(file_path), str(root_dir), offset_type=OffsetType.BYTE)
        assert content == "   1 | Line 1\n   2 | Line 2\n   3 | Line 3"

    def test_read_file_content_text_full_raw_utf8_output(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_text_raw.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3")
        content = FileUtils.read_file_content(str(file_path), str(root_dir), offset_type=OffsetType.BYTE, output_format=OutputFormat.RAW_UTF8)
        assert content == "   1 | Line 1\n   2 | Line 2\n   3 | Line 3"

    def test_read_file_content_text_full_base64_output(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_text_base64.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3")
        content = FileUtils.read_file_content(str(file_path), str(root_dir), offset_type=OffsetType.BYTE, output_format=OutputFormat.BASE64)
        expected_content_bytes = b"   1 | Line 1\n   2 | Line 2\n   3 | Line 3"
        assert content == base64.b64encode(expected_content_bytes).decode("ascii")

    def test_read_file_content_binary_base64_output(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_binary_base64.bin"
        binary_data = b"\x00\x01\x02\x03\x04\x05"
        file_path.write_bytes(binary_data)
        content = FileUtils.read_file_content(str(file_path), str(root_dir), offset_type=OffsetType.BYTE, output_format=OutputFormat.BASE64)
        assert content == base64.b64encode(binary_data).decode("ascii")

    def test_read_file_content_binary_quoted_printable_output(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_binary_qp.bin"
        binary_data = b"\x00\x01\x02\x03\x04\x05"
        file_path.write_bytes(binary_data)
        content = FileUtils.read_file_content(str(file_path), str(root_dir), offset_type=OffsetType.BYTE, output_format=OutputFormat.QUOTED_PRINTABLE)
        assert content == encodestring(binary_data).decode("ascii")

    def test_read_file_content_text_with_different_encoding(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_text_latin1.txt"
        text_content = "Héllö Wörld"
        file_path.write_text(text_content, encoding="latin-1")
        content = FileUtils.read_file_content(str(file_path), str(root_dir), file_encoding="latin-1", output_format=OutputFormat.RAW_UTF8)
        assert content == "   1 | Héllö Wörld"

    def test_read_file_content_text_line_offset(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_text_offset.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        content = FileUtils.read_file_content(str(file_path), str(root_dir), start_offset_inclusive=1, end_offset_inclusive=2, offset_type=OffsetType.LINE)
        assert content == "   2 | Line 2\n   3 | Line 3"

    def test_delete_paths(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_to_delete = root_dir / "file_to_delete.txt"
        file_to_delete.touch()
        dir_to_delete = root_dir / "dir_to_delete"
        dir_to_delete.mkdir()
        (dir_to_delete / "nested_file.txt").touch()

        result = FileUtils.delete_paths([str(file_to_delete), str(dir_to_delete)], str(root_dir))
        assert "Successfully deleted" in result["message"]
        assert not file_to_delete.exists()
        assert not dir_to_delete.exists()

    def test_write_file_content_text_raw_utf8_input(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_write_raw.txt"
        new_content = "New raw content."
        processed_new_content = FileUtils.validate_and_decode_content(new_content, "text", InputFormat.RAW_UTF8)
        result = FileUtils.write_file_content(str(file_path), processed_new_content, str(root_dir), mode="text")
        assert "Successfully wrote text content" in result["message"]
        assert file_path.read_text() == new_content

    def test_write_file_content_text_base64_input(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_write_base64.txt"
        original_content = "Content to be encoded."
        encoded_content = base64.b64encode(original_content.encode("utf-8")).decode("ascii")
        processed_content = FileUtils.validate_and_decode_content(encoded_content, "text", InputFormat.BASE64)
        result = FileUtils.write_file_content(str(file_path), processed_content, str(root_dir), mode="text")
        assert "Successfully wrote text content" in result["message"]
        assert file_path.read_text() == original_content

    def test_write_file_content_binary_base64_input(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_write_binary_base64.bin"
        binary_data = b"\x06\x07\x08\x09"
        encoded_data = base64.b64encode(binary_data).decode("ascii")
        processed_data = FileUtils.validate_and_decode_content(encoded_data, "binary", InputFormat.BASE64)
        result = FileUtils.write_file_content(str(file_path), processed_data, str(root_dir), mode="binary")
        assert "Successfully wrote binary content" in result["message"]
        assert file_path.read_bytes() == binary_data

    def test_modify_file_text_raw_utf8_input(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_modify_raw.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3\nLine 4\n")
        result = FileUtils.modify_file(str(file_path), str(root_dir), 7, 12, OffsetType.CHAR, "Modified", InputFormat.RAW_UTF8, file_encoding="utf-8")
        assert "Successfully modified text file" in result
        assert file_path.read_text() == "Line 1\nModified\nLine 3\nLine 4\n"

    def test_modify_file_binary_base64_input(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_binary_modify_base64.bin"
        original_content = b"\x00\x01\x02\x03\x04\x05"
        file_path.write_bytes(original_content)
        new_bytes = b"\xff\xee"
        encoded_new_bytes = base64.b64encode(new_bytes).decode("ascii")
        result = FileUtils.modify_file(
            str(file_path), str(root_dir), 2, 4, OffsetType.BYTE, encoded_new_bytes, input_format=InputFormat.BASE64, file_encoding=None
        )
        assert "Successfully modified binary file" in result
        assert file_path.read_bytes() == b"\x00\x01\xff\xee\x04\x05"

    def test_replace_content_in_file_text_raw_utf8_input(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_replace_raw.txt"
        file_path.write_text("Hello World\nHello Python\n")
        result = FileUtils.replace_content_in_file(str(file_path), str(root_dir), "Hello", "Hi", input_format=InputFormat.RAW_UTF8)
        assert "Successfully replaced 2 occurrence(s) in text file" in result
        assert file_path.read_text() == "Hi World\nHi Python\n"

    def test_replace_content_in_file_binary_base64_input(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_replace_binary_base64.bin"
        original_content = b"\x00\x01\x02\x01\x03"
        file_path.write_bytes(original_content)
        old_content_bytes = b"\x01"
        new_content_bytes = b"\xff"
        encoded_old_content = base64.b64encode(old_content_bytes).decode("ascii")
        encoded_new_content = base64.b64encode(new_content_bytes).decode("ascii")
        result = FileUtils.replace_content_in_file(
            str(file_path), str(root_dir), encoded_old_content, encoded_new_content, mode="binary", is_regex=False, input_format=InputFormat.BASE64
        )
        assert "Successfully replaced 2 occurrence(s) in binary file" in result
        assert file_path.read_bytes() == b"\x00\xff\x02\xff\x03"

    def test_replace_content_in_file_text_with_different_encoding(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_replace_latin1.txt"
        original_text = "Héllö Wörld"
        file_path.write_text(original_text, encoding="latin-1")
        old_text = "Wörld"
        new_text = "Universe"
        result = FileUtils.replace_content_in_file(
            str(file_path), str(root_dir), old_text, new_text, file_encoding="latin-1", input_format=InputFormat.RAW_UTF8
        )
        assert "Successfully replaced 1 occurrence(s) in text file" in result
        assert file_path.read_text(encoding="latin-1") == "Héllö Universe"

    def test_validate_file_path_inside_root(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = root_dir / "test_file.txt"
        file_path.touch()
        validated_path = FileUtils.validate_file_path(str(file_path), str(root_dir))
        assert str(file_path.resolve()) == validated_path

    def test_validate_file_path_outside_root(self, tmp_path):
        root_dir = tmp_path / "test_root"
        root_dir.mkdir()
        file_path = tmp_path / "outside_file.txt"
        with pytest.raises(ValueError):
            FileUtils.validate_file_path(str(file_path), str(root_dir))
