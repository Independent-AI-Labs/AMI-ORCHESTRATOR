import base64
import shutil
import unittest
from pathlib import Path

from orchestrator.mcp.servers.localfs.file_utils import FileUtils, OffsetType


class TestFileUtils(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent / "test_root"
        if self.root_dir.exists():
            shutil.rmtree(self.root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.root_dir.exists():
            shutil.rmtree(self.root_dir, ignore_errors=True)

    def test_list_directory_contents_non_recursive(self):
        (self.root_dir / "file1.txt").touch()
        (self.root_dir / "file2.txt").touch()
        (self.root_dir / "subdir1").mkdir()
        (self.root_dir / "subdir2").mkdir()

        contents = FileUtils.list_directory_contents(str(self.root_dir), str(self.root_dir))
        expected_lines = [
            "├───subdir1",
            "├───subdir2",
            "├───file1.txt",
            "└───file2.txt",
        ]
        self.assertEqual(contents.splitlines(), expected_lines)

    def test_list_directory_contents_recursive(self):
        (self.root_dir / "file1.txt").touch()
        (self.root_dir / "subdir1").mkdir()
        (self.root_dir / "subdir1" / "file3.txt").touch()
        (self.root_dir / "subdir2").mkdir()
        (self.root_dir / "subdir2" / "file4.txt").touch()
        (self.root_dir / "subdir2" / "subsubdir1").mkdir()
        (self.root_dir / "subdir2" / "subsubdir1" / "file5.txt").touch()

        contents = FileUtils.list_directory_contents(str(self.root_dir), str(self.root_dir), recursive=True)
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
        self.assertEqual(actual_lines, expected_lines)

    def test_create_dirs(self):
        new_dir = self.root_dir / "new_dir" / "subdir"
        result = FileUtils.create_dirs(str(new_dir), str(self.root_dir))
        self.assertTrue("Successfully created directory" in result["message"])
        self.assertTrue(new_dir.is_dir())

    def test_find_files_by_path_name(self):
        (self.root_dir / "test_file_abc.txt").touch()
        (self.root_dir / "another_file_xyz.log").touch()
        (self.root_dir / "subdir" / "nested_abc.txt").mkdir(parents=True)

        found_files = FileUtils.find_files(str(self.root_dir), str(self.root_dir), keywords_path_name=["abc"], keywords_file_content=[])
        expected_files = [
            str(self.root_dir / "test_file_abc.txt"),
        ]
        self.assertCountEqual(found_files, expected_files)

    def test_find_files_by_content(self):
        (self.root_dir / "file_with_content1.txt").write_text("This is a test with keyword1.")
        (self.root_dir / "file_with_content2.txt").write_text("Another test with keyword2.")
        (self.root_dir / "binary_file.bin").write_bytes(b"\x00\x01\x02")

        found_files = FileUtils.find_files(str(self.root_dir), str(self.root_dir), keywords_path_name=[], keywords_file_content=["keyword1"])
        expected_files = [
            str(self.root_dir / "file_with_content1.txt"),
        ]
        self.assertCountEqual(found_files, expected_files)

    def test_read_file_content_text_full(self):
        file_path = self.root_dir / "test_text.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3")
        content = FileUtils.read_file_content(str(file_path), str(self.root_dir), offset_type=OffsetType.BYTE)
        self.assertEqual(content, "   1 | Line 1\n   2 | Line 2\n   3 | Line 3")

    def test_read_file_content_text_line_offset(self):
        file_path = self.root_dir / "test_text_line_offset.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        content = FileUtils.read_file_content(str(file_path), str(self.root_dir), start_offset_inclusive=2, end_offset_inclusive=4, offset_type=OffsetType.LINE)
        self.assertEqual(content, "   2 | Line 2\n   3 | Line 3\n   4 | Line 4")

    def test_delete_paths(self):
        file1 = self.root_dir / "file_to_delete1.txt"
        dir1 = self.root_dir / "dir_to_delete1"
        file1.touch()
        dir1.mkdir()
        result = FileUtils.delete_paths([str(file1), str(dir1)], str(self.root_dir))
        self.assertTrue("Successfully deleted 2 item(s)" in result["message"])
        self.assertFalse(file1.exists())
        self.assertFalse(dir1.exists())

    def test_modify_file_text(self):
        file_path = self.root_dir / "test_modify.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3\nLine 4\n")
        result = FileUtils.modify_file(str(file_path), str(self.root_dir), 7, 12, OffsetType.CHAR, "Modified")
        self.assertIn("Successfully modified text file", result)
        self.assertEqual(file_path.read_text(), "Line 1\nModified\nLine 3\nLine 4\n")

    def test_modify_file_binary(self):
        file_path = self.root_dir / "test_binary_modify.bin"
        original_content = b"\x00\x01\x02\x03\x04\x05"
        file_path.write_bytes(original_content)
        new_bytes = b"\xff\xee"
        result = FileUtils.modify_file(str(file_path), str(self.root_dir), 2, 4, OffsetType.BYTE, new_bytes)
        self.assertIn("Successfully modified binary file", result)
        self.assertEqual(file_path.read_bytes(), b"\x00\x01\xff\xee\x04\x05")

    def test_replace_content_in_file_text(self):
        file_path = self.root_dir / "test_replace_text.txt"
        file_path.write_text("Hello World\nHello Python\n")
        result = FileUtils.replace_content_in_file(str(file_path), str(self.root_dir), "Hello", "Hi")
        self.assertIn("Successfully replaced 2 occurrence(s) in text file", result)
        self.assertEqual(file_path.read_text(), "Hi World\nHi Python\n")

    def test_replace_content_in_file_binary(self):
        file_path = self.root_dir / "test_replace_binary.bin"
        original_content = b"\x00\x01\x02\x01\x03"
        file_path.write_bytes(original_content)
        old_content_b64 = base64.b64encode(b"\x01").decode("utf-8")
        new_content_b64 = base64.b64encode(b"\xff").decode("utf-8")
        result = FileUtils.replace_content_in_file(str(file_path), str(self.root_dir), old_content_b64, new_content_b64)
        self.assertIn("Successfully replaced 2 occurrence(s) in binary file", result)
        self.assertEqual(file_path.read_bytes(), b"\x00\xff\x02\xff\x03")

    def test_validate_file_path_inside_root(self):
        file_path = self.root_dir / "test_file.txt"
        file_path.touch()
        validated_path = FileUtils.validate_file_path(str(file_path), str(self.root_dir))
        self.assertEqual(str(file_path.resolve()), validated_path)

    def test_validate_file_path_outside_root(self):
        file_path = self.root_dir.parent / "outside_file.txt"
        with self.assertRaises(ValueError):
            FileUtils.validate_file_path(str(file_path), str(self.root_dir))


if __name__ == "__main__":
    unittest.main()
