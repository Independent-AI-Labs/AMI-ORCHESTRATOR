"""Unit and integration tests for backup archive module."""

import tarfile
from unittest.mock import Mock

import zstandard as zstd

from scripts.backup.backup_archive import (
    _create_archive_filter,
    _get_archive_size_mb,
    create_zip_archive,
)
from scripts.backup.backup_exceptions import ArchiveError


class TestArchiveFilter:
    """Unit tests for archive filter functions."""

    def test_create_archive_filter_excludes_patterns(self):
        """_create_archive_filter creates function that excludes patterns."""

        exclude_patterns = ["__pycache__", ".pyc", "node_modules"]
        filter_func = _create_archive_filter(exclude_patterns)

        # Create mock tarinfo objects
        mock_tarinfo_pycache = Mock()
        mock_tarinfo_pycache.name = "path/__pycache__/file.py"

        mock_tarinfo_node_modules = Mock()
        mock_tarinfo_node_modules.name = "node_modules/package/file.js"

        mock_tarinfo_normal = Mock()
        mock_tarinfo_normal.name = "normal_file.py"

        # Test that excluded files return None
        assert filter_func(mock_tarinfo_pycache) is None
        assert filter_func(mock_tarinfo_node_modules) is None

        # Test that normal files return themselves
        assert filter_func(mock_tarinfo_normal) == mock_tarinfo_normal

    def test_create_archive_filter_excludes_venv_subdirs(self):
        """_create_archive_filter excludes .venv in subdirectories."""

        filter_func = _create_archive_filter([])

        # Create mock tarinfo objects
        mock_tarinfo_root_venv = Mock()
        mock_tarinfo_root_venv.name = ".venv/bin/python"  # Should NOT be excluded (at root)

        mock_tarinfo_sub_venv = Mock()
        mock_tarinfo_sub_venv.name = "some/sub/.venv/bin/python"  # Should be excluded

        mock_tarinfo_normal = Mock()
        mock_tarinfo_normal.name = "normal_file.txt"

        # Root .venv should be preserved
        assert filter_func(mock_tarinfo_root_venv) == mock_tarinfo_root_venv
        # Subdirectory .venv should be excluded
        assert filter_func(mock_tarinfo_sub_venv) is None
        # Normal file should be preserved
        assert filter_func(mock_tarinfo_normal) == mock_tarinfo_normal


class TestArchiveSize:
    """Tests for archive size functions."""

    def test_get_archive_size_mb(self, tmp_path):
        """_get_archive_size_mb returns file size in MB."""
        # Create a test file with known size
        test_file = tmp_path / "test_file.txt"
        # Write 2MB of data (2 * 1024 * 1024 bytes)
        with test_file.open("wb") as f:
            f.write(b"x" * 2 * 1024 * 1024)

        size_mb = _get_archive_size_mb(test_file)
        assert size_mb == 2.0

    def test_get_archive_size_mb_error(self, tmp_path):
        """_get_archive_size_mb raises ArchiveError for missing file."""
        nonexistent_file = tmp_path / "nonexistent.txt"

        try:
            _get_archive_size_mb(nonexistent_file)
            raise AssertionError("Expected ArchiveError was not raised")
        except ArchiveError:
            pass  # Expected behavior


class TestCreateZipArchiveIntegration:
    """Integration tests for create_zip_archive function using real file operations."""

    async def test_create_zip_archive_basic_integration(self, tmp_path):
        """Integration test to verify archive creation with real file operations."""

        # Create a temporary source directory with some test files
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create some test files in the source directory
        (source_dir / "file1.txt").write_text("Test content 1")
        (source_dir / "file2.txt").write_text("Test content 2")

        # Create a subdirectory with more files
        sub_dir = source_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("Test content 3")

        # Run the actual archive creation function
        archive_path = await create_zip_archive(source_dir)

        # Assert that the archive file was created
        assert archive_path.exists()
        assert archive_path.name == "ami-orchestrator-backup.tar.zst"

        # Verify that the archive can be read and contains the expected files
        # Decompress and read the archive
        with archive_path.open("rb") as fh:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(fh) as reader, tarfile.open(fileobj=reader, mode="r|") as tar:
                # Get all member names
                members = [member.name for member in tar.getmembers() if member.isfile()]

                # Verify expected files are in the archive (with correct relative paths)
                expected_files = [
                    "./file1.txt",
                    "./file2.txt",
                    "./subdir/file3.txt",
                ]

                for expected_file in expected_files:
                    assert expected_file in members, f"Expected file {expected_file} not found in archive"

    async def test_create_zip_archive_with_excluded_patterns(self, tmp_path):
        """Integration test to verify exclusion patterns work with real file operations."""

        # Create a temporary source directory with files including some to be excluded
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create test files (some that should be excluded)
        (source_dir / "file1.txt").write_text("Normal file")
        (source_dir / "__pycache__").mkdir()
        (source_dir / "__pycache__" / "cache_file.py").write_text("Cache file")
        (source_dir / ".pyc").write_text("Pyc file")

        sub_venv = source_dir / "project" / ".venv" / "bin"
        sub_venv.mkdir(parents=True)
        (sub_venv / "python").write_text("Python binary")

        # Root .venv should NOT be excluded
        root_venv = source_dir / ".venv" / "bin"
        root_venv.mkdir(parents=True)
        (root_venv / "python").write_text("Root Python binary")

        # Run the actual archive creation function
        archive_path = await create_zip_archive(source_dir)

        # Assert that the archive file was created
        assert archive_path.exists()

        # Verify that excluded files are not in the archive
        with archive_path.open("rb") as fh:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(fh) as reader, tarfile.open(fileobj=reader, mode="r|") as tar:
                members = [member.name for member in tar.getmembers() if member.isfile()]

                # Check that excluded files are not present
                assert "./__pycache__/cache_file.py" not in members
                assert "./.pyc" not in members
                assert "./project/.venv/bin/python" not in members  # Subdir .venv should be excluded

                # Check that allowed files are present
                assert "./file1.txt" in members
                # Root .venv should be included
                assert "./.venv/bin/python" in members  # Root .venv should be included

    async def test_create_zip_archive_file_size(self, tmp_path):
        """Integration test to verify archive file has appropriate size."""

        # Create a temporary source directory with content
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create a reasonably sized test file
        large_content = "Hello world\n" * 1000  # 12KB of content
        (source_dir / "large_file.txt").write_text(large_content)

        # Create the archive
        archive_path = await create_zip_archive(source_dir)

        # Verify the archive was created and has reasonable size
        assert archive_path.exists()
        assert archive_path.stat().st_size > 0  # Non-zero size
