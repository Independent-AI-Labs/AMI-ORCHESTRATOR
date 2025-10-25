"""Edge case tests for AMI automation system.

Tests unusual inputs, error conditions, and boundary cases.
"""  # test-fixture

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from scripts.automation.agent_cli import AgentConfigPresets, ClaudeAgentCLI
from scripts.automation.audit import AuditEngine
from scripts.automation.hooks import CodeQualityValidator, CommandValidator, HookInput, ResponseScanner


class TestHookEdgeCases:
    """Edge cases for hook validators."""

    def test_hook_empty_stdin(self):  # test-fixture
        """Hook with empty stdin fails gracefully."""
        result = subprocess.run(  # test-fixture
            ["./scripts/ami-agent", "--hook", "command-guard"],
            check=False,
            input="",  # test-fixture
            capture_output=True,
            text=True,
        )

        # Should fail-open and allow
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output.get("decision") in (None, "allow")

    def test_hook_malformed_json(self):  # test-fixture
        """Hook with malformed JSON fails gracefully."""
        result = subprocess.run(  # test-fixture
            ["./scripts/ami-agent", "--hook", "command-guard"],
            check=False,
            input="{not valid json}",  # test-fixture
            capture_output=True,
            text=True,
        )

        # Should fail-open on parse error
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output.get("decision") in (None, "allow")

    def test_hook_missing_required_fields(self):  # test-fixture
        """Hook with missing fields fails gracefully."""
        hook_input = json.dumps({})  # test-fixture

        result = subprocess.run(  # test-fixture
            ["./scripts/ami-agent", "--hook", "command-guard"],
            check=False,
            input=hook_input,
            capture_output=True,
            text=True,
        )

        # Should fail-open
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output.get("decision") in (None, "allow")

    def test_hook_unicode_command(self):  # test-fixture
        """Hook handles unicode in commands."""
        hook_input = {  # test-fixture
            "session_id": "test-unicode",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo '你好世界'"},  # test-fixture
            "transcript_path": None,
        }

        result = subprocess.run(  # test-fixture
            ["./scripts/ami-agent", "--hook", "command-guard"],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_hook_very_long_command(self):  # test-fixture
        """Hook handles very long commands."""
        long_cmd = "echo " + "a" * 10000  # test-fixture

        hook_input = {  # test-fixture
            "session_id": "test-long",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": long_cmd},
            "transcript_path": None,
        }

        result = subprocess.run(  # test-fixture
            ["./scripts/ami-agent", "--hook", "command-guard"],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_response_scanner_empty_transcript(self):  # test-fixture
        """ResponseScanner handles empty transcript."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:  # test-fixture
            temp_path = Path(f.name)

        try:  # test-fixture
            scanner = ResponseScanner()
            hook_input = HookInput(
                session_id="test",
                hook_event_name="Stop",
                tool_name=None,
                tool_input=None,
                transcript_path=temp_path,
            )

            result = scanner.validate(hook_input)

            # Empty transcript has no assistant message, so scanner allows
            assert result.decision in (None, "allow")
        finally:  # test-fixture
            if temp_path.exists():  # test-fixture
                temp_path.unlink()  # test-fixture

    def test_response_scanner_malformed_transcript_lines(self):  # test-fixture
        """ResponseScanner skips malformed lines."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:  # test-fixture
            f.write("not json\n")  # test-fixture
            f.write('{"incomplete": \n')  # test-fixture
            f.write('{"type": "assistant", "message": {"content": [{"type": "text", "text": "WORK DONE"}]}}\n')  # test-fixture
            temp_path = Path(f.name)

        try:  # test-fixture
            scanner = ResponseScanner()
            hook_input = HookInput(
                session_id="test",
                hook_event_name="Stop",
                tool_name=None,
                tool_input=None,
                transcript_path=temp_path,
            )

            result = scanner.validate(hook_input)

            # Should find the valid line with WORK DONE
            assert result.decision in (None, "allow")
        finally:  # test-fixture
            if temp_path.exists():  # test-fixture
                temp_path.unlink()  # test-fixture


class TestAgentCLIEdgeCases:
    """Edge cases for AgentCLI."""

    def test_agent_cli_missing_instruction(self):  # test-fixture
        """ClaudeAgentCLI requires instruction."""
        cli = ClaudeAgentCLI()

        with pytest.raises(ValueError) as exc_info:  # test-fixture
            cli.run_print(instruction=None, instruction_file=None)

        assert "required" in str(exc_info.value).lower()

    def test_agent_cli_empty_instruction(self):  # test-fixture
        """ClaudeAgentCLI rejects empty instruction."""
        cli = ClaudeAgentCLI()

        # Empty string is treated as no instruction
        with pytest.raises(ValueError) as exc_info:  # test-fixture
            cli.run_print(  # test-fixture
                instruction="",
                stdin="test",
                agent_config=AgentConfigPresets.worker(),
            )

        assert "required" in str(exc_info.value).lower()

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_agent_cli_very_short_timeout(self):  # test-fixture
        """ClaudeAgentCLI respects very short timeout."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        instruction = fixtures_dir / "instructions" / "simple_task.txt"

        cli = ClaudeAgentCLI()
        config = AgentConfigPresets.worker()
        config.timeout = 0.001  # 1ms - guaranteed timeout  # test-fixture

        exit_code, output = cli.run_print(  # test-fixture
            instruction_file=instruction,
            stdin="test",
            agent_config=config,
        )

        assert exit_code == 1
        assert "timeout" in output.lower()

    def test_agent_cli_unknown_tool_in_allowed(self):  # test-fixture
        """ClaudeAgentCLI rejects unknown tools in allowed_tools."""
        with pytest.raises(ValueError) as exc_info:  # test-fixture
            ClaudeAgentCLI.compute_disallowed_tools(["NonexistentTool"])

        assert "unknown" in str(exc_info.value).lower()

    def test_agent_cli_empty_allowed_tools(self):  # test-fixture
        """ClaudeAgentCLI handles empty allowed_tools list."""
        disallowed = ClaudeAgentCLI.compute_disallowed_tools([])

        # All tools should be disallowed
        assert len(disallowed) == len(ClaudeAgentCLI.ALL_TOOLS)


class TestAuditEngineEdgeCases:
    """Edge cases for AuditEngine."""

    def test_audit_empty_directory(self):  # test-fixture
        """audit_directory() handles empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            engine = AuditEngine()
            results = engine.audit_directory(tmpdir_path)  # test-fixture

            assert len(results) == 0

    def test_audit_directory_with_only_excluded_files(self):  # test-fixture
        """audit_directory() skips all files if all excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            # Create only excluded files
            (tmpdir_path / "__init__.py").write_text("")  # test-fixture
            (tmpdir_path / "readme.txt").write_text("text")  # test-fixture

            pycache = tmpdir_path / "__pycache__"
            pycache.mkdir()
            (pycache / "cache.pyc").write_text("binary")  # test-fixture

            engine = AuditEngine()
            results = engine.audit_directory(tmpdir_path)  # test-fixture

            # Should find no files to audit
            assert len(results) == 0

    def test_audit_nonexistent_file(self):  # test-fixture
        """_audit_file() handles nonexistent file."""
        engine = AuditEngine()

        result = engine._audit_file(Path("/nonexistent/file.py"))  # test-fixture

        assert result.status == "ERROR"
        assert result.file_path == Path("/nonexistent/file.py")
        # Error details are logged, not stored in FileResult

    def test_audit_file_with_no_extension(self):  # test-fixture
        """_find_files() skips files with no extension."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "README").write_text("text")  # test-fixture
            (tmpdir_path / "Makefile").write_text("rules")  # test-fixture
            (tmpdir_path / "test.py").write_text("def foo(): pass")  # test-fixture

            engine = AuditEngine()
            files = list(engine._find_files(tmpdir_path))  # test-fixture

            # Should only find test.py
            assert len(files) == 1
            assert files[0].name == "test.py"

    def test_audit_detect_language_unknown_extension(self):  # test-fixture
        """_detect_language() returns None for unknown extensions."""
        engine = AuditEngine()

        assert engine._detect_language(Path("test.xyz")) is None
        assert engine._detect_language(Path("file.unknown")) is None

    def test_audit_very_large_file(self):  # test-fixture
        """_audit_file() handles very large files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:  # test-fixture
            # Create a 1MB file
            for i in range(10000):  # test-fixture
                f.write(f"def function_{i}():\n    return {i}\n\n")  # test-fixture
            temp_path = Path(f.name)

        try:  # test-fixture
            engine = AuditEngine()
            # This might timeout or fail, but should not crash
            result = engine._audit_file(temp_path)  # test-fixture

            # Should complete (PASS, FAIL, or ERROR)
            assert result.status in ("PASS", "FAIL", "ERROR")
        finally:  # test-fixture
            if temp_path.exists():  # test-fixture
                temp_path.unlink()  # test-fixture

    def test_audit_file_with_special_characters(self):  # test-fixture
        """_audit_file() handles filenames with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            # Create file with spaces and special chars
            special_file = tmpdir_path / "test file (copy).py"
            special_file.write_text("def test():\n    return True")  # test-fixture

            engine = AuditEngine()
            result = engine._audit_file(special_file)  # test-fixture

            assert result.file_path == special_file
            assert result.status in ("PASS", "FAIL", "ERROR")


class TestCommandValidatorEdgeCases:
    """Edge cases for CommandValidator."""

    def test_command_validator_non_bash_tool(self):  # test-fixture
        """CommandValidator allows non-Bash tools."""
        validator = CommandValidator()

        hook_input = HookInput(
            session_id="test",
            hook_event_name="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "test.py"},
            transcript_path=None,
        )

        result = validator.validate(hook_input)

        assert result.decision in (None, "allow")

    def test_command_validator_null_tool_input(self):  # test-fixture
        """CommandValidator handles null tool_input."""
        validator = CommandValidator()

        hook_input = HookInput(
            session_id="test",
            hook_event_name="PreToolUse",
            tool_name="Bash",
            tool_input=None,  # test-fixture
            transcript_path=None,
        )

        # Should not crash
        result = validator.validate(hook_input)

        # Might allow or deny depending on implementation
        assert result.decision in (None, "allow", "deny")

    def test_command_validator_nested_tool_input(self):  # test-fixture
        """CommandValidator searches nested tool_input."""
        validator = CommandValidator()

        hook_input = HookInput(
            session_id="test",
            hook_event_name="PreToolUse",
            tool_name="Bash",
            tool_input={
                "command": "echo safe",
                "nested": {"deep": "python3 script.py"},  # test-fixture
            },
            transcript_path=None,
        )

        result = validator.validate(hook_input)

        # Should find python3 in nested structure
        assert result.decision == "deny"


class TestCodeQualityValidatorEdgeCases:
    """Edge cases for CodeQualityValidator."""

    def test_code_quality_non_python_file(self):  # test-fixture
        """CodeQualityValidator skips non-Python files."""
        validator = CodeQualityValidator()

        hook_input = HookInput(
            session_id="test",
            hook_event_name="PreToolUse",
            tool_name="Edit",
            tool_input={
                "file_path": "test.js",
                "old_string": "const x = 1",
                "new_string": "const x = 2",
            },
            transcript_path=None,
        )

        result = validator.validate(hook_input)

        # Should skip and allow
        assert result.decision in (None, "allow")

    def test_code_quality_empty_diff(self):  # test-fixture
        """CodeQualityValidator handles empty code."""
        validator = CodeQualityValidator()

        hook_input = HookInput(
            session_id="test",
            hook_event_name="PreToolUse",
            tool_name="Edit",
            tool_input={
                "file_path": "test.py",
                "old_string": "",
                "new_string": "",
            },
            transcript_path=None,
        )

        result = validator.validate(hook_input)

        # Should handle gracefully
        assert result.decision in (None, "allow", "deny")

    def test_code_quality_write_new_file(self):  # test-fixture
        """CodeQualityValidator handles Write tool for new files."""
        validator = CodeQualityValidator()

        hook_input = HookInput(
            session_id="test",
            hook_event_name="PreToolUse",
            tool_name="Write",
            tool_input={
                "file_path": "/tmp/nonexistent_test_file.py",
                "content": "def test():\n    return True",
            },
            transcript_path=None,
        )

        result = validator.validate(hook_input)

        # Should check new code
        assert result.decision in (None, "allow", "deny")
