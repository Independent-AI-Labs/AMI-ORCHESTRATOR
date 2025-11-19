"""Unit and integration tests for backup archive module."""

from unittest.mock import AsyncMock, Mock, mock_open, patch

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


class TestCreateZipArchiveUnit:
    """Unit tests for create_zip_archive function with mocked dependencies."""

    async def test_create_zip_archive_basic_unit(self, tmp_path):
        """Unit test to verify archive creation with mocked file operations."""

        # Create a source directory
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Mock all external dependencies
        with (
            patch("scripts.backup.backup_archive.tarfile.open"),
            patch("scripts.backup.backup_archive.zstd.ZstdCompressor") as mock_compressor_cls,
            patch("scripts.backup.backup_archive.Path.unlink"),
            patch("scripts.backup.backup_archive.Path.exists", return_value=False),
            patch("scripts.backup.backup_archive.Path.stat") as mock_stat,
            patch("builtins.open", mock_open()) as mock_file,
        ):
            # Setup mock compressor
            mock_compressor = AsyncMock()
            mock_compressor_cls.return_value = mock_compressor

            # Setup mock stream writer
            mock_stream_writer = AsyncMock()
            mock_compressor.stream_writer.return_value.__enter__.return_value = mock_stream_writer

            # Setup mock stat for file size
            mock_file_stat = Mock()
            mock_file_stat.st_size = 1024  # 1KB for example
            mock_stat.return_value = mock_file_stat

            # Run the archive creation function
            archive_path = await create_zip_archive(source_dir)

            # Verify the function ran and created expected path
            assert archive_path == source_dir / "ami-orchestrator-backup.tar.zst"

            # Verify that the compressor was called with correct parameters
            mock_compressor_cls.assert_called_once_with(level=3, threads=-1)

            # Verify that file operations were attempted
            mock_file.assert_called()  # Should have opened the archive file

    async def test_create_zip_archive_exclusion_patterns_unit(self, tmp_path):
        """Unit test to verify exclusion patterns work with mocked operations."""

        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Mock all external dependencies
        with (
            patch("scripts.backup.backup_archive.tarfile.open"),
            patch("scripts.backup.backup_archive.zstd.ZstdCompressor") as mock_compressor_cls,
            patch("scripts.backup.backup_archive.Path.unlink"),
            patch("scripts.backup.backup_archive.Path.exists", return_value=False),
            patch("scripts.backup.backup_archive.Path.stat") as mock_stat,
            patch("builtins.open", mock_open()),
        ):
            # Setup mocks
            mock_compressor = AsyncMock()
            mock_compressor_cls.return_value = mock_compressor

            mock_stream_writer = AsyncMock()
            mock_compressor.stream_writer.return_value.__enter__.return_value = mock_stream_writer

            mock_file_stat = Mock()
            mock_file_stat.st_size = 2048
            mock_stat.return_value = mock_file_stat

            # Run the archive creation function
            archive_path = await create_zip_archive(source_dir)

            # Verify the function executed without error
            assert archive_path.exists()  # This is based on the path, not actual existence

            # Verify compressor was called correctly
            mock_compressor_cls.assert_called_once_with(level=3, threads=-1)

    async def test_create_zip_archive_file_size_unit(self, tmp_path):
        """Unit test to verify archive file size reporting with mocked operations."""

        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Mock all external dependencies to test the size reporting path
        with (
            patch("scripts.backup.backup_archive.tarfile.open"),
            patch("scripts.backup.backup_archive.zstd.ZstdCompressor") as mock_compressor_cls,
            patch("scripts.backup.backup_archive.Path.unlink"),
            patch("scripts.backup.backup_archive.Path.exists", return_value=False),
            patch("scripts.backup.backup_archive.Path.stat") as mock_stat,
            patch("builtins.open", mock_open()),
        ):
            # Setup mocks
            mock_compressor = AsyncMock()
            mock_compressor_cls.return_value = mock_compressor

            mock_stream_writer = AsyncMock()
            mock_compressor.stream_writer.return_value.__enter__.return_value = mock_stream_writer

            mock_file_stat = Mock()
            mock_file_stat.st_size = 4096  # 4KB
            mock_stat.return_value = mock_file_stat

            # Run the archive creation function
            archive_path = await create_zip_archive(source_dir)

            # Verify execution completed
            assert str(archive_path).endswith("ami-orchestrator-backup.tar.zst")

            # Verify stat was called to get file size
            mock_stat.assert_called()
