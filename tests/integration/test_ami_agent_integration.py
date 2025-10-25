"""Integration tests for scripts/ami-agent.

These tests ACTUALLY execute the ami-agent script with real subprocesses.
NO mocking of Claude CLI or agent functionality.

Note: These are integration tests - subprocess calls should fail if there are errors.
"""  # test-fixture

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestAmiAgentHookMode:
    """REAL execution of ami-agent --hook command."""

    def test_hook_command_guard_allows_safe_command(self):  # test-fixture
        """ami-agent --hook command-guard allows safe bash command."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        hook_input = fixtures_dir / "hooks" / "bash_allow.json"

        with hook_input.open() as f:
            result = subprocess.run(  # test-fixture
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--hook", "command-guard"],
                check=False,
                stdin=f,
                capture_output=True,
                text=True,
            )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output.get("decision") in (None, "allow")

    def test_hook_command_guard_denies_python3(self):  # test-fixture
        """ami-agent --hook command-guard denies direct python3."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        hook_input = fixtures_dir / "hooks" / "bash_deny_python.json"

        with hook_input.open() as f:
            result = subprocess.run(  # test-fixture
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--hook", "command-guard"],
                check=False,
                stdin=f,
                capture_output=True,
                text=True,
            )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        # PreToolUse hooks use hookSpecificOutput schema
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "ami-run" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_hook_command_guard_denies_pip(self):  # test-fixture
        """ami-agent --hook command-guard denies pip install."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        hook_input = fixtures_dir / "hooks" / "bash_deny_pip.json"

        with hook_input.open() as f:
            result = subprocess.run(  # test-fixture
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--hook", "command-guard"],
                check=False,
                stdin=f,
                capture_output=True,
                text=True,
            )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        # PreToolUse hooks use hookSpecificOutput schema
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert (
            "pyproject.toml" in output["hookSpecificOutput"]["permissionDecisionReason"] or "ami-uv" in output["hookSpecificOutput"]["permissionDecisionReason"]
        )

    def test_hook_command_guard_denies_git_commit(self):  # test-fixture
        """ami-agent --hook command-guard denies direct git commit."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        hook_input = fixtures_dir / "hooks" / "bash_deny_git_commit.json"

        with hook_input.open() as f:
            result = subprocess.run(  # test-fixture
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--hook", "command-guard"],
                check=False,
                stdin=f,
                capture_output=True,
                text=True,
            )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        # PreToolUse hooks use hookSpecificOutput schema
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "git_commit.sh" in output["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.slow
    def test_hook_response_scanner_allows_work_done(self):  # test-fixture
        """ami-agent --hook response-scanner allows WORK DONE marker."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        transcript = fixtures_dir / "transcripts" / "clean_with_work_done.jsonl"

        hook_input = {  # test-fixture
            "session_id": "test-123",
            "hook_event_name": "Stop",
            "tool_name": None,
            "tool_input": None,
            "transcript_path": str(transcript),
        }

        result = subprocess.run(  # test-fixture
            ["./scripts/ami-run.sh", "./scripts/ami-agent", "--hook", "response-scanner"],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output.get("decision") in (None, "allow")

    @pytest.mark.slow
    def test_hook_response_scanner_blocks_violation(self):  # test-fixture
        """ami-agent --hook response-scanner blocks prohibited phrase."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        transcript = fixtures_dir / "transcripts" / "violation_youre_right.jsonl"

        hook_input = {  # test-fixture
            "session_id": "test-456",
            "hook_event_name": "Stop",
            "tool_name": None,
            "tool_input": None,
            "transcript_path": str(transcript),
        }

        result = subprocess.run(  # test-fixture
            ["./scripts/ami-run.sh", "./scripts/ami-agent", "--hook", "response-scanner"],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["decision"] == "block"
        assert "VIOLATION" in output["reason"] or "right" in output["reason"].lower()

    @pytest.mark.slow
    def test_hook_response_scanner_allows_no_violation(self):  # test-fixture
        """ami-agent --hook response-scanner allows stop when no violations (no infinite loop)."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        transcript = fixtures_dir / "transcripts" / "no_completion_marker.jsonl"

        hook_input = {  # test-fixture
            "session_id": "test-789",
            "hook_event_name": "Stop",
            "tool_name": None,
            "tool_input": None,
            "transcript_path": str(transcript),
        }

        result = subprocess.run(  # test-fixture
            ["./scripts/ami-run.sh", "./scripts/ami-agent", "--hook", "response-scanner"],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        # Should allow (not block) to prevent infinite loops
        assert output.get("decision", "allow") == "allow" or "decision" not in output

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_hook_code_quality_calls_real_llm(self):  # test-fixture
        """ami-agent --hook code-quality actually invokes Claude CLI for LLM audit."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        hook_input = fixtures_dir / "hooks" / "edit_violation.json"

        with hook_input.open() as f:
            result = subprocess.run(  # test-fixture
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--hook", "code-quality"],
                check=False,
                stdin=f,
                capture_output=True,
                text=True,
                timeout=60,
            )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        # PreToolUse hooks use hookSpecificOutput schema
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "CODE QUALITY" in output["hookSpecificOutput"]["permissionDecisionReason"]


class TestAmiAgentPrintMode:
    """REAL execution of ami-agent --print."""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_print_mode_executes_instruction(self):  # test-fixture
        """ami-agent --print actually calls claude --print subprocess."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        instruction = fixtures_dir / "instructions" / "simple_task.txt"

        result = subprocess.run(  # test-fixture
            ["./scripts/ami-run.sh", "./scripts/ami-agent", "--print", str(instruction)],
            check=False,
            input="test input data",
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "PASS" in result.stdout

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_print_mode_handles_stdin(self):  # test-fixture
        """ami-agent --print passes stdin to subprocess."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        instruction = fixtures_dir / "instructions" / "simple_task.txt"

        stdin_data = "test data from stdin"

        result = subprocess.run(  # test-fixture
            ["./scripts/ami-run.sh", "./scripts/ami-agent", "--print", str(instruction)],
            check=False,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0


class TestAmiAgentAuditMode:
    """REAL execution of ami-agent --audit."""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_audit_mode_processes_directory(self):  # test-fixture
        """ami-agent --audit processes all files in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "clean.py").write_text(  # test-fixture
                'def foo():\n    """Doc."""\n    return 42\n'
            )
            (tmpdir_path / "test2.py").write_text(  # test-fixture
                'def bar():\n    """Doc."""\n    return sum([1, 2, 3])\n'
            )

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--audit", str(tmpdir_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert "Progress:" in result.stdout or "Audit Summary:" in result.stdout

            audit_dir = tmpdir_path / "docs" / "audit"
            assert audit_dir.exists()

            date_dirs = list(audit_dir.iterdir())
            assert len(date_dirs) > 0

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_audit_mode_creates_reports(self):  # test-fixture
        """ami-agent --audit creates mirrored directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            subdir = tmpdir_path / "module"
            subdir.mkdir()
            (subdir / "code.py").write_text("def test():\n    return True\n")  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--audit", str(tmpdir_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert result.returncode in (0, 1)

            audit_dirs = list((tmpdir_path / "docs" / "audit").iterdir())
            assert len(audit_dirs) > 0

            audit_output = audit_dirs[0]
            report_file = audit_output / "module" / "code.py.md"
            assert report_file.exists()

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_audit_mode_exit_codes(self):  # test-fixture
        """ami-agent --audit returns correct exit codes."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "code"

        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            import shutil  # test-fixture

            shutil.copy(fixtures_dir / "clean.py", tmpdir_path / "clean.py")  # test-fixture

            result = subprocess.run(  # test-fixture
                ["./scripts/ami-run.sh", "./scripts/ami-agent", "--audit", str(tmpdir_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert result.returncode == 0


class TestAmiAgentErrorHandling:
    """Test ami-agent error handling."""

    def test_hook_mode_unknown_validator(self):  # test-fixture
        """ami-agent --hook with unknown validator returns error."""
        result = subprocess.run(  # test-fixture
            ["./scripts/ami-run.sh", "./scripts/ami-agent", "--hook", "nonexistent-validator"],
            check=False,
            input="{}",
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Unknown validator" in result.stderr

    def test_print_mode_missing_instruction_file(self):  # test-fixture
        """ami-agent --print with missing file returns error."""
        result = subprocess.run(  # test-fixture
            ["./scripts/ami-run.sh", "./scripts/ami-agent", "--print", "/nonexistent/file.txt"],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "not found" in result.stderr.lower()

    def test_audit_mode_missing_directory(self):  # test-fixture
        """ami-agent --audit with missing directory returns error."""
        result = subprocess.run(  # test-fixture
            ["./scripts/ami-run.sh", "./scripts/ami-agent", "--audit", "/nonexistent/directory"],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "not found" in result.stderr.lower()
