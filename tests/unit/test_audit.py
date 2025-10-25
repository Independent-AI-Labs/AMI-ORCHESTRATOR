"""Unit tests for automation.audit module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import will fail until we implement audit.py - that's expected in TDD
try:
    from scripts.automation.audit import AuditEngine, FileResult
except ImportError:
    AuditEngine = None
    FileResult = None


class TestFileResult:
    """Unit tests for FileResult dataclass."""

    @pytest.mark.skipif(FileResult is None, reason="FileResult not implemented yet")
    def test_create_file_result(self):
        """FileResult creates with all fields."""
        result = FileResult(
            file_path=Path("/test/file.py"),
            status="PASS",
            violations=[],
            execution_time=1.23,
        )

        assert result.file_path == Path("/test/file.py")
        assert result.status == "PASS"
        assert result.violations == []
        assert result.execution_time == 1.23


class TestAuditEngine:
    """Unit tests for AuditEngine."""

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_create_audit_engine(self):
        """AuditEngine creates successfully."""
        engine = AuditEngine()

        assert engine is not None
        assert hasattr(engine, "config")
        assert hasattr(engine, "logger")

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_detect_language_python(self):
        """_detect_language() detects Python files."""
        engine = AuditEngine()

        lang = engine._detect_language(Path("/test/file.py"))

        assert lang == "python"

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_detect_language_javascript(self):
        """_detect_language() detects JavaScript files."""
        engine = AuditEngine()

        lang = engine._detect_language(Path("/test/file.js"))

        assert lang == "javascript"

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_detect_language_typescript(self):
        """_detect_language() detects TypeScript files."""
        engine = AuditEngine()

        lang = engine._detect_language(Path("/test/file.ts"))

        assert lang == "typescript"

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_detect_language_unknown(self):
        """_detect_language() returns None for unknown files."""
        engine = AuditEngine()

        lang = engine._detect_language(Path("/test/file.txt"))

        assert lang is None

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_should_exclude_matches_pattern(self):
        """_should_exclude() excludes matching files."""
        engine = AuditEngine()

        # Mock config to return exclusion patterns
        engine.config._data["audit"]["scanning"]["exclude_patterns"] = ["**/test_*.py"]

        result = engine._should_exclude(Path("/foo/test_something.py"))

        assert result is True

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_should_exclude_no_match(self):
        """_should_exclude() includes non-matching files."""
        engine = AuditEngine()

        engine.config._data["audit"]["scanning"]["exclude_patterns"] = ["**/test_*.py"]

        result = engine._should_exclude(Path("/foo/module.py"))

        assert result is False

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_find_files_basic(self):
        """_find_files() finds matching files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            (tmpdir_path / "file1.py").write_text("print('hello')")
            (tmpdir_path / "file2.py").write_text("print('world')")
            (tmpdir_path / "readme.txt").write_text("docs")

            engine = AuditEngine()
            engine.config._data["audit"]["scanning"]["include_patterns"] = ["*.py"]
            engine.config._data["audit"]["scanning"]["exclude_patterns"] = []

            files = list(engine._find_files(tmpdir_path))

            # Should find both .py files
            assert len(files) == 2
            assert all(f.suffix == ".py" for f in files)

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_find_files_excludes_empty_init(self):
        """_find_files() excludes empty __init__.py files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create empty __init__.py
            (tmpdir_path / "__init__.py").write_text("")
            # Create non-empty file
            (tmpdir_path / "module.py").write_text("def foo(): pass")

            engine = AuditEngine()
            engine.config._data["audit"]["scanning"]["include_patterns"] = ["*.py"]
            engine.config._data["audit"]["scanning"]["exclude_patterns"] = []

            files = list(engine._find_files(tmpdir_path))

            # Should only find module.py, not empty __init__.py
            assert len(files) == 1
            assert files[0].name == "module.py"

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_find_files_includes_nonempty_init(self):
        """_find_files() includes non-empty __init__.py files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create non-empty __init__.py
            (tmpdir_path / "__init__.py").write_text("__version__ = '1.0.0'")

            engine = AuditEngine()
            engine.config._data["audit"]["scanning"]["include_patterns"] = ["*.py"]
            engine.config._data["audit"]["scanning"]["exclude_patterns"] = []

            files = list(engine._find_files(tmpdir_path))

            # Should include non-empty __init__.py
            assert len(files) == 1
            assert files[0].name == "__init__.py"

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_check_cache_disabled(self):
        """_check_cache() returns None when cache disabled."""
        engine = AuditEngine()
        engine.config._data["audit"]["cache"]["enabled"] = False

        result = engine._check_cache(Path("/test/file.py"))

        assert result is None

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_check_cache_missing_file(self):
        """_check_cache() returns None when cache file doesn't exist."""
        engine = AuditEngine()
        engine.config._data["audit"]["cache"]["enabled"] = True
        engine.config._data["audit"]["cache"]["storage"] = "/tmp/nonexistent"

        result = engine._check_cache(Path("/test/file.py"))

        assert result is None

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_cache_result_disabled(self):
        """_cache_result() does nothing when cache disabled."""
        engine = AuditEngine()
        engine.config._data["audit"]["cache"]["enabled"] = False

        result = FileResult(
            file_path=Path("/test/file.py"),
            status="PASS",
            violations=[],
            execution_time=1.0,
        )

        # Should not crash
        engine._cache_result(Path("/test/file.py"), result)

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_save_report_pass(self):
        """_save_report() creates report for PASS status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            root_dir = tmpdir_path / "project"
            root_dir.mkdir()
            output_dir = tmpdir_path / "output"
            output_dir.mkdir()

            file_path = root_dir / "module.py"
            file_path.write_text("def foo(): pass")

            result = FileResult(
                file_path=file_path,
                status="PASS",
                violations=[],
                execution_time=1.5,
            )

            engine = AuditEngine()
            engine._save_report(result, root_dir, output_dir)

            # Check report was created
            report_path = output_dir / "module.py.md"
            assert report_path.exists()

            # Check report content
            content = report_path.read_text()
            assert "AUDIT REPORT" in content
            assert "PASS" in content
            assert "No violations" in content or "✅" in content

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_save_report_fail(self):
        """_save_report() creates report for FAIL status with violations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            root_dir = tmpdir_path / "project"
            root_dir.mkdir()
            output_dir = tmpdir_path / "output"
            output_dir.mkdir()

            file_path = root_dir / "module.py"
            file_path.write_text("def foo(): pass")

            result = FileResult(
                file_path=file_path,
                status="FAIL",
                violations=[
                    {
                        "line": 10,
                        "pattern_id": "test_pattern",
                        "severity": "CRITICAL",
                        "message": "Test violation",
                    }
                ],
                execution_time=2.0,
            )

            engine = AuditEngine()
            engine._save_report(result, root_dir, output_dir)

            # Check report was created
            report_path = output_dir / "module.py.md"
            assert report_path.exists()

            # Check report content
            content = report_path.read_text()
            assert "AUDIT REPORT" in content
            assert "FAIL" in content
            assert "Test violation" in content
            assert "Line 10" in content

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_save_report_mirrors_structure(self):
        """_save_report() mirrors directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            root_dir = tmpdir_path / "project"
            root_dir.mkdir()
            output_dir = tmpdir_path / "output"
            output_dir.mkdir()

            # Create nested file
            subdir = root_dir / "automation"
            subdir.mkdir()
            file_path = subdir / "config.py"
            file_path.write_text("class Config: pass")

            result = FileResult(
                file_path=file_path,
                status="PASS",
                violations=[],
                execution_time=1.0,
            )

            engine = AuditEngine()
            engine._save_report(result, root_dir, output_dir)

            # Check mirrored structure
            report_path = output_dir / "automation" / "config.py.md"
            assert report_path.exists()
            assert report_path.parent.name == "automation"

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    @patch("scripts.automation.audit.get_agent_cli")
    def test_audit_file_pass(self, mock_get_cli):
        """_audit_file() returns PASS for passing audit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_path = tmpdir_path / "test.py"
            file_path.write_text("def foo(): pass")

            # Mock agent CLI to return PASS
            mock_cli = MagicMock()
            mock_cli.run_print.return_value = "PASS"
            mock_get_cli.return_value = mock_cli

            engine = AuditEngine()
            result = engine._audit_file(file_path)

            assert result.status == "PASS"
            assert result.violations == []
            assert result.file_path == file_path

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    @patch("scripts.automation.audit.get_agent_cli")
    def test_audit_file_fail(self, mock_get_cli):
        """_audit_file() returns FAIL for failing audit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_path = tmpdir_path / "test.py"
            file_path.write_text("def foo(): pass")

            # Mock agent CLI to return FAIL
            mock_cli = MagicMock()
            mock_cli.run_print.return_value = "FAIL: Bad code"
            mock_get_cli.return_value = mock_cli

            engine = AuditEngine()
            result = engine._audit_file(file_path)

            assert result.status == "FAIL"
            assert len(result.violations) > 0

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    @patch("scripts.automation.audit.get_agent_cli")
    def test_audit_file_error(self, mock_get_cli):
        """_audit_file() returns ERROR on audit failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_path = tmpdir_path / "test.py"
            file_path.write_text("def foo(): pass")

            # Mock agent CLI to raise exception
            mock_cli = MagicMock()
            mock_cli.run_print.side_effect = Exception("Audit failed")
            mock_get_cli.return_value = mock_cli

            engine = AuditEngine()
            result = engine._audit_file(file_path)

            assert result.status == "ERROR"

    @pytest.mark.skipif(AuditEngine is None, reason="AuditEngine not implemented yet")
    def test_audit_file_unknown_language(self):
        """_audit_file() skips files with unknown language."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_path = tmpdir_path / "readme.txt"
            file_path.write_text("Some text")

            engine = AuditEngine()
            result = engine._audit_file(file_path)

            assert result.status == "PASS"
            assert result.violations == []
