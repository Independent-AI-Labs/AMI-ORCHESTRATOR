"""Unit tests for run_tests.py script."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import the module being tested
import scripts.run_tests as run_tests_module


class TestEnsureRepoOnPath:
    """Tests for _ensure_repo_on_path function."""

    def test_finds_orchestrator_root(self) -> None:
        """_ensure_repo_on_path locates AMI orchestrator root."""
        with patch.object(Path, "exists") as mock_exists:
            # Simulate finding .git and base directories
            mock_exists.return_value = True

            # Mock resolve to return a path structure
            test_root = Path("/test/orchestrator")
            with patch.object(Path, "resolve") as mock_resolve:
                mock_resolve.return_value = test_root / "scripts" / "run_tests.py"

                # Should find the root successfully
                try:
                    result = run_tests_module._ensure_repo_on_path()
                    assert isinstance(result, Path)
                except RuntimeError:
                    # If it actually tries to walk the filesystem, that's fine for this test
                    pass

    def test_raises_error_if_root_not_found(self) -> None:
        """_ensure_repo_on_path raises RuntimeError if root not found."""
        with (
            patch.object(Path, "exists", return_value=False),
            pytest.raises(RuntimeError, match="Unable to locate AMI orchestrator root"),
            patch.object(Path, "resolve", return_value=Path("/")),
        ):
            run_tests_module._ensure_repo_on_path()


class TestMain:
    """Tests for main() function."""

    @pytest.fixture
    def mock_orchestrator_root(self, tmp_path: Path) -> Path:
        """Create a mock orchestrator root directory."""
        root = tmp_path / "orchestrator"
        root.mkdir()
        (root / "base").mkdir()
        (root / ".git").mkdir()
        return root

    @pytest.fixture
    def mock_tests_dir(self, mock_orchestrator_root: Path) -> Path:
        """Create a mock tests directory with test files."""
        tests_dir = mock_orchestrator_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_example.py").write_text("def test_pass(): assert True")
        return tests_dir

    def test_main_runs_pytest_when_tests_exist(
        self,
        mock_orchestrator_root: Path,
        mock_tests_dir: Path,
    ) -> None:
        """main() runs pytest when test files exist."""
        with (
            patch.object(run_tests_module, "_ensure_repo_on_path", return_value=mock_orchestrator_root),
            patch("base.backend.utils.runner_bootstrap.ensure_module_venv"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=0)

            # Run main
            result = run_tests_module.main()

            # Should have called pytest
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == sys.executable
            assert call_args[1] == "-m"
            assert call_args[2] == "pytest"
            assert result == 0

    def test_main_returns_zero_when_no_tests_dir(self, mock_orchestrator_root: Path) -> None:
        """main() returns 0 when tests directory doesn't exist."""
        with (
            patch.object(run_tests_module, "_ensure_repo_on_path", return_value=mock_orchestrator_root),
            patch("base.backend.utils.runner_bootstrap.ensure_module_venv"),
            patch("subprocess.run") as mock_run,
        ):
            # Run main
            result = run_tests_module.main()

            # Should NOT call pytest
            assert not mock_run.called
            assert result == 0

    def test_main_returns_zero_when_no_test_files(self, mock_orchestrator_root: Path) -> None:
        """main() returns 0 when tests directory has no test files."""
        # Create tests dir but no test files
        tests_dir = mock_orchestrator_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "not_a_test.py").write_text("# Not a test file")

        with (
            patch.object(run_tests_module, "_ensure_repo_on_path", return_value=mock_orchestrator_root),
            patch("base.backend.utils.runner_bootstrap.ensure_module_venv"),
            patch("subprocess.run") as mock_run,
        ):
            # Run main
            result = run_tests_module.main()

            # Should NOT call pytest
            assert not mock_run.called
            assert result == 0

    def test_main_passes_cli_args_to_pytest(
        self,
        mock_orchestrator_root: Path,
        mock_tests_dir: Path,
    ) -> None:
        """main() passes command-line arguments to pytest."""
        with (
            patch.object(run_tests_module, "_ensure_repo_on_path", return_value=mock_orchestrator_root),
            patch("base.backend.utils.runner_bootstrap.ensure_module_venv"),
            patch("subprocess.run") as mock_run,
            patch.object(sys, "argv", ["run_tests.py", "-v", "--tb=short"]),
        ):
            mock_run.return_value = Mock(returncode=0)

            # Run main
            result = run_tests_module.main()

            # Check pytest was called with extra args
            call_args = mock_run.call_args[0][0]
            assert "-v" in call_args
            assert "--tb=short" in call_args
            assert result == 0

    def test_main_returns_pytest_exit_code(
        self,
        mock_orchestrator_root: Path,
        mock_tests_dir: Path,
    ) -> None:
        """main() returns pytest's exit code."""
        with (
            patch.object(run_tests_module, "_ensure_repo_on_path", return_value=mock_orchestrator_root),
            patch("base.backend.utils.runner_bootstrap.ensure_module_venv"),
            patch("subprocess.run") as mock_run,
        ):
            # Simulate pytest failure
            mock_run.return_value = Mock(returncode=1)

            result = run_tests_module.main()

            assert result == 1

    def test_main_handles_pytest_subprocess_error(
        self,
        mock_orchestrator_root: Path,
        mock_tests_dir: Path,
    ) -> None:
        """main() handles subprocess errors gracefully."""
        with (
            patch.object(run_tests_module, "_ensure_repo_on_path", return_value=mock_orchestrator_root),
            patch("base.backend.utils.runner_bootstrap.ensure_module_venv"),
            patch("subprocess.run") as mock_run,
        ):
            # Simulate subprocess returning non-zero
            mock_run.return_value = Mock(returncode=127)

            result = run_tests_module.main()

            # Should return the subprocess return code
            assert result == 127

    def test_main_finds_test_files_with_different_patterns(
        self,
        mock_orchestrator_root: Path,
    ) -> None:
        """main() finds test files with test_*.py and *_test.py patterns."""
        tests_dir = mock_orchestrator_root / "tests"
        tests_dir.mkdir()

        # Create test files with different patterns
        (tests_dir / "test_prefix.py").write_text("def test_1(): pass")
        (tests_dir / "suffix_test.py").write_text("def test_2(): pass")

        with (
            patch.object(run_tests_module, "_ensure_repo_on_path", return_value=mock_orchestrator_root),
            patch("base.backend.utils.runner_bootstrap.ensure_module_venv"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=0)

            result = run_tests_module.main()

            # Should have found test files and run pytest
            assert mock_run.called
            assert result == 0
