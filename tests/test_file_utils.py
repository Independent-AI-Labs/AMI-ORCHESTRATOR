import unittest
from pathlib import Path

from orchestrator.mcp.servers.localfs.file_utils import FileUtils


class TestFileUtils(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).parent / "test_root"
        self.root_dir.mkdir(exist_ok=True)

    def tearDown(self):
        for f in self.root_dir.glob("*"):
            if f.is_file():
                f.unlink()
            else:
                f.rmdir()
        self.root_dir.rmdir()

    def test_validate_file_path_inside_root(self):
        file_path = self.root_dir / "test_file.txt"
        validated_path = FileUtils.validate_file_path(str(file_path), str(self.root_dir))
        self.assertEqual(str(file_path.resolve()), validated_path)

    def test_validate_file_path_outside_root(self):
        file_path = self.root_dir.parent / "outside_file.txt"
        with self.assertRaises(ValueError):
            FileUtils.validate_file_path(str(file_path), str(self.root_dir))

    def test_validate_file_path_relative_path_inside_root(self):
        file_path = self.root_dir / "test_file.txt"
        validated_path = FileUtils.validate_file_path("test_file.txt", str(self.root_dir))
        self.assertEqual(str(file_path.resolve()), validated_path)

    def test_validate_file_path_relative_path_outside_root(self):
        with self.assertRaises(ValueError):
            FileUtils.validate_file_path("../outside_file.txt", str(self.root_dir))


if __name__ == "__main__":
    unittest.main()
