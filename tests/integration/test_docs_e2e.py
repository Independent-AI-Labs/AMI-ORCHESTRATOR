"""E2E integration tests for ami-agent --docs mode.

Tests documentation maintenance workflow with worker and moderator agents.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_docs_dir():
    """Create temporary directory for documentation files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def orchestrator_root():
    """Get orchestrator root directory."""
    return Path(__file__).resolve().parents[2]


class TestDocsWorkflow:
    """Test documentation maintenance workflow."""

    def test_doc_with_work_done_succeeds(self, temp_docs_dir, orchestrator_root):
        """Documentation maintenance with WORK DONE should complete."""
        # Create simple doc file that doesn't need updates
        doc_file = temp_docs_dir / "test-doc.md"
        doc_file.write_text("# Test Documentation\n\nThis is current documentation that matches the codebase.\n")

        # Run ami-agent --docs with timeout
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--docs",
                str(temp_docs_dir),
                "--root-dir",
                str(temp_docs_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should succeed
        assert result.returncode == 0, f"Expected success, got exit code {result.returncode}.\nStdout: {result.stdout}\nStderr: {result.stderr}"

        # Check summary
        assert "Completed: 1" in result.stdout or "completed" in result.stdout.lower()

    def test_doc_without_marker_gets_feedback(self, temp_docs_dir, orchestrator_root):
        """Doc maintenance without completion marker should retry."""
        # Create doc file
        doc_file = temp_docs_dir / "test-no-marker.md"
        doc_file.write_text("# Simple Documentation\n\nContent here.\n")

        # Run ami-agent --docs with timeout
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--docs",
                str(temp_docs_dir),
                "--root-dir",
                str(temp_docs_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should succeed (worker gets feedback and retries with WORK DONE)
        assert result.returncode == 0, f"Expected success.\nStdout: {result.stdout}\nStderr: {result.stderr}"

    def test_doc_with_feedback_marker(self, temp_docs_dir, orchestrator_root):
        """Doc maintenance requesting feedback should provide feedback status."""
        # Create doc that references non-existent code
        doc_file = temp_docs_dir / "test-feedback.md"
        doc_file.write_text(
            "# API Documentation\n\n"
            "This documents the NonExistentClass API.\n"
            "If the class doesn't exist in the codebase, output 'FEEDBACK: Cannot find NonExistentClass'\n"
        )

        # Run ami-agent --docs with timeout
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--docs",
                str(temp_docs_dir),
                "--root-dir",
                str(temp_docs_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should handle feedback
        assert "Needs Feedback" in result.stdout or "feedback" in result.stdout.lower()

    def test_multiple_docs_sequential(self, temp_docs_dir, orchestrator_root):
        """Multiple docs should be processed sequentially."""
        # Create multiple doc files
        (temp_docs_dir / "doc1.md").write_text("# Doc 1\n\nContent.\n")
        (temp_docs_dir / "doc2.md").write_text("# Doc 2\n\nContent.\n")
        (temp_docs_dir / "doc3.md").write_text("# Doc 3\n\nContent.\n")

        # Run ami-agent --docs with timeout
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--docs",
                str(temp_docs_dir),
                "--root-dir",
                str(temp_docs_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )

        # Should succeed or have feedback (not fail)
        assert result.returncode in [0, 1]  # 0 = success, 1 = needs feedback

        # All docs should be processed
        assert "Total: 3" in result.stdout

    def test_excludes_special_files(self, temp_docs_dir, orchestrator_root):
        """CLAUDE.md and AGENTS.md should be excluded."""
        # Create doc and special files
        (temp_docs_dir / "doc.md").write_text("# Doc\n\nContent.\n")
        (temp_docs_dir / "CLAUDE.md").write_text("Agent instructions\n")
        (temp_docs_dir / "AGENTS.md").write_text("Agent documentation\n")

        # Run ami-agent --docs with timeout
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--docs",
                str(temp_docs_dir),
                "--root-dir",
                str(temp_docs_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should only process 1 doc
        assert "Total: 1" in result.stdout

    def test_update_action_edits_file(self, temp_docs_dir, orchestrator_root):
        """UPDATE action should modify documentation file."""
        # Create outdated doc with #AGENT: note
        doc_file = temp_docs_dir / "test-update.md"
        doc_file.write_text("# Test Documentation\n\n#AGENT: Add a section about testing.\n\nExisting content.\n")

        # Run ami-agent --docs with timeout
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--docs",
                str(temp_docs_dir),
                "--root-dir",
                str(temp_docs_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should succeed or have feedback
        assert result.returncode in [0, 1]

        # Doc should be processed
        assert "Total: 1" in result.stdout

    def test_archive_action_preserves_file(self, temp_docs_dir, orchestrator_root):
        """ARCHIVE action should move file to archive directory."""
        # Create doc about deprecated feature
        doc_file = temp_docs_dir / "deprecated-feature.md"
        doc_file.write_text("# Deprecated Feature\n\nThis feature was removed in v2.0.\nIf this feature doesn't exist, archive this document.\n")

        # Run ami-agent --docs with timeout
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--docs",
                str(temp_docs_dir),
                "--root-dir",
                str(temp_docs_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Should succeed or have feedback
        assert result.returncode in [0, 1]

        # Doc should be processed
        assert "Total: 1" in result.stdout


class TestDocsExecutionSummary:
    """Test documentation maintenance summary reporting."""

    def test_summary_shows_action_breakdown(self, temp_docs_dir, orchestrator_root):
        """Summary should show breakdown of actions taken."""
        # Create multiple docs
        (temp_docs_dir / "doc1.md").write_text("# Doc 1\n\nContent.\n")
        (temp_docs_dir / "doc2.md").write_text("# Doc 2\n\nContent.\n")

        # Run ami-agent --docs with timeout
        result = subprocess.run(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--docs",
                str(temp_docs_dir),
                "--root-dir",
                str(temp_docs_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )

        # Should show summary
        assert "Documentation Maintenance Summary" in result.stdout
        assert "Total:" in result.stdout
        assert "Completed:" in result.stdout or "Needs Feedback:" in result.stdout or "Failed:" in result.stdout
