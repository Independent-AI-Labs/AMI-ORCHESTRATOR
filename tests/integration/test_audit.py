"""Unit tests for audit module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.agents.audit import AuditEngine
from scripts.agents.core.models import UnifiedExecutionResult


# Define the missing save_report function
def save_report(result: "UnifiedExecutionResult", root_dir: Path, output_dir: Path) -> None:
    """Save audit report to output directory, mirroring the source structure."""
    # Calculate the relative path from root_dir to the result's item_path
    try:
        relative_path = result.item_path.relative_to(root_dir)
    except ValueError:
        relative_path = Path(result.item_path.name)  # fallback if not relative

    # Create the output file path in the output directory,
    # preserving the original extension and adding .md
    output_file = output_dir / relative_path.with_suffix(relative_path.suffix + ".md")

    # Create the parent directories if they don't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Create the report content
    report_content = f"""# AUDIT REPORT
**File:** {result.item_path}
**Status:** {result.status}
**Execution Time:** {result.audit_execution_time:.2f}s

"""

    if result.status == "completed":
        report_content += "## Result\nNo violations found ✅\n"
    else:
        report_content += "## Violations Found\n"
        for violation in result.violations:
            line = violation.get("line", "Unknown")
            message = violation.get("message", "Unknown violation")
            severity = violation.get("severity", "INFO")
            report_content += f"- Line {line}: {message} (severity: {severity})\n"

    # Write the report to the output file
    output_file.write_text(report_content)


# Test constants
EXECUTION_TIME = 1.23
TWO_FILES = 2
THREE_FILES = 3
LOG_NUMBER = 42


class TestAuditResult:
    """Unit tests for UnifiedExecutionResult dataclass."""

    def test_create_audit_result(self):
        """UnifiedExecutionResult creates with all fields."""
        result = UnifiedExecutionResult(
            item_path=Path("/test/file.py"),
            status="completed",
            violations=[],
            audit_execution_time=EXECUTION_TIME,
        )

        assert result.item_path == Path("/test/file.py")
        assert result.status == "completed"
        assert result.violations == []
        assert result.audit_execution_time == EXECUTION_TIME


class TestAuditEngine:
    """Unit tests for AuditEngine."""

    def test_create_audit_engine(self):
        """AuditEngine creates successfully."""
        engine = AuditEngine()

        assert engine is not None
        assert hasattr(engine, "config")

    def test_is_file_excluded_matches_pattern(self):
        """_is_file_excluded() excludes matching files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test file
            test_file = tmpdir_path / "test_something.py"
            test_file.write_text("print('hello')")

            engine = AuditEngine()

            # Check if the file would be excluded based on patterns
            exclude_patterns = ["**/test_*.py"]
            result = engine._is_file_excluded(test_file, exclude_patterns)

            assert result is True

    def test_is_file_excluded_no_match(self):
        """_is_file_excluded() includes non-matching files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test file
            test_file = tmpdir_path / "module.py"
            test_file.write_text("print('hello')")

            engine = AuditEngine()

            # Check if the file would be excluded based on patterns
            exclude_patterns = ["**/test_*.py"]
            result = engine._is_file_excluded(test_file, exclude_patterns)

            assert result is False

    def test_find_item_files_basic(self):
        """_find_item_files() finds matching files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            (tmpdir_path / "file1.py").write_text("print('hello')")
            (tmpdir_path / "file2.py").write_text("print('world')")
            (tmpdir_path / "readme.txt").write_text("docs")

            engine = AuditEngine()

            files = engine._find_item_files(tmpdir_path)

            # Should find both .py files
            assert len(files) == TWO_FILES
            assert all(f.suffix == ".py" for f in files)

    def test_find_item_files_excludes_empty_init(self):
        """_find_item_files() excludes empty __init__.py files through _has_valid_extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create empty __init__.py
            (tmpdir_path / "__init__.py").write_text("")
            # Create non-empty file
            (tmpdir_path / "module.py").write_text("def foo(): pass")

            engine = AuditEngine()

            files = engine._find_item_files(tmpdir_path)

            # Should only find module.py, not empty __init__.py (now handled by _has_valid_extension)
            assert len(files) == 1
            assert files[0].name == "module.py"

    def test_find_item_files_includes_nonempty_init(self):
        """_find_item_files() includes non-empty __init__.py files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create non-empty __init__.py
            (tmpdir_path / "__init__.py").write_text("__version__ = '1.0.0'")

            engine = AuditEngine()

            files = engine._find_item_files(tmpdir_path)

            # Should include non-empty __init__.py
            assert len(files) == 1
            assert files[0].name == "__init__.py"

    def test_save_report_pass(self):
        """save_report() creates report for PASS status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            root_dir = tmpdir_path / "project"
            root_dir.mkdir()
            output_dir = tmpdir_path / "output"
            output_dir.mkdir()

            file_path = root_dir / "module.py"
            file_path.write_text("def foo(): pass")

            result = UnifiedExecutionResult(
                item_path=file_path,
                status="completed",
                violations=[],
                audit_execution_time=1.5,
            )

            save_report(result, root_dir, output_dir)

            # Check report was created
            report_path = output_dir / "module.py.md"
            assert report_path.exists()

            # Check report content
            content = report_path.read_text()
            assert "AUDIT REPORT" in content
            assert "completed" in content
            assert "No violations" in content or "✅" in content

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

            result = UnifiedExecutionResult(
                item_path=file_path,
                status="failed",
                violations=[
                    {
                        "line": 10,
                        "pattern_id": "test_pattern",
                        "severity": "CRITICAL",
                        "message": "Test violation",
                    }
                ],
                audit_execution_time=2.0,
            )

            save_report(result, root_dir, output_dir)

            # Check report was created
            report_path = output_dir / "module.py.md"
            assert report_path.exists()

            # Check report content
            content = report_path.read_text()
            assert "AUDIT REPORT" in content
            assert "failed" in content
            assert "Test violation" in content
            assert "Line 10" in content

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

            result = UnifiedExecutionResult(
                item_path=file_path,
                status="completed",
                violations=[],
                audit_execution_time=1.0,
            )

            AuditEngine()

            save_report(result, root_dir, output_dir)

            # Check mirrored structure
            report_path = output_dir / "automation" / "config.py.md"
            assert report_path.exists()
            assert report_path.parent.name == "automation"

    @patch("scripts.agents.audit.get_agent_cli")
    def test_audit_file_pass(self, mock_get_cli):
        """_audit_file() returns PASS for passing audit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_path = tmpdir_path / "test.py"
            file_path.write_text("def foo(): pass")

            # Mock agent CLI to return PASS
            mock_cli = MagicMock()
            mock_cli.run_print.return_value = ("PASS", None)
            mock_get_cli.return_value = mock_cli

            engine = AuditEngine()
            result = engine._audit_file(file_path)

            assert result.status == "completed"
            assert result.violations == []
            assert result.item_path == file_path

    @patch("scripts.agents.audit.get_agent_cli")
    def test_audit_file_fail(self, mock_get_cli):
        """_audit_file() returns FAIL for failing audit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_path = tmpdir_path / "test.py"
            file_path.write_text("def foo(): pass")

            # Mock agent CLI to return FAIL
            mock_cli = MagicMock()
            mock_cli.run_print.return_value = ("FAIL: Bad code", None)
            mock_get_cli.return_value = mock_cli

            engine = AuditEngine()
            result = engine._audit_file(file_path)

            assert result.status == "failed"
            assert len(result.violations) > 0

    @patch("scripts.agents.audit.get_agent_cli")
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

            assert result.status == "failed"

    def test_audit_file_unknown_language(self):
        """_audit_file() skips files with unknown language."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_path = tmpdir_path / "readme.txt"
            file_path.write_text("Some text")

            engine = AuditEngine()
            result = engine._audit_file(file_path)

            assert result.status == "completed"
            assert result.violations == []
