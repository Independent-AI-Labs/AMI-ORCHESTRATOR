"""Integration tests for automation.agent_cli module.

These tests ACTUALLY invoke ClaudeAgentCLI.run_print() which calls subprocess.
NO mocking of Claude CLI subprocess calls.
"""  # test-fixture

import tempfile
from pathlib import Path

import pytest

from scripts.automation.agent_cli import AgentConfigPresets, ClaudeAgentCLI


class TestClaudeAgentCLIIntegration:
    """REAL tests of ClaudeAgentCLI - NO MOCKING."""

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_run_print_executes_subprocess(self):  # test-fixture
        """run_print() actually calls subprocess.run() with claude --print."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        instruction = fixtures_dir / "instructions" / "simple_task.txt"

        cli = ClaudeAgentCLI()
        exit_code, output = cli.run_print(  # test-fixture
            instruction_file=instruction,
            stdin="test input",
            agent_config=AgentConfigPresets.worker(),
        )

        assert exit_code == 0
        assert "PASS" in output

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_run_print_audit_preset_tool_restrictions(self):  # test-fixture
        """run_print() correctly applies audit preset tool restrictions."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        instruction = fixtures_dir / "instructions" / "simple_task.txt"

        cli = ClaudeAgentCLI()

        audit_config = AgentConfigPresets.audit()
        assert audit_config.allowed_tools == ["WebSearch", "WebFetch"]

        disallowed = cli.compute_disallowed_tools(audit_config.allowed_tools)
        assert len(disallowed) == 13
        assert "Bash" in disallowed
        assert "Read" in disallowed
        assert "Write" in disallowed

        exit_code, output = cli.run_print(  # test-fixture
            instruction_file=instruction,
            stdin="test",
            agent_config=audit_config,
        )

        assert exit_code == 0

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_run_print_handles_stdin(self):  # test-fixture
        """run_print() passes stdin data to subprocess."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        instruction = fixtures_dir / "instructions" / "simple_task.txt"

        cli = ClaudeAgentCLI()
        stdin_data = "test data from integration test"

        exit_code, output = cli.run_print(  # test-fixture
            instruction_file=instruction,
            stdin=stdin_data,
            agent_config=AgentConfigPresets.worker(),
        )

        assert exit_code == 0

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_run_print_timeout(self):  # test-fixture
        """run_print() respects timeout setting."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as f:  # test-fixture
            f.write("Sleep for 100 seconds")
            f.flush()

            cli = ClaudeAgentCLI()
            config = AgentConfigPresets.worker()
            config.timeout = 1

            exit_code, output = cli.run_print(  # test-fixture
                instruction_file=Path(f.name),
                stdin="",
                agent_config=config,
            )

            assert exit_code == 1
            assert "timeout" in output.lower()

    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_run_print_hooks_disabled(self):  # test-fixture
        """run_print() creates empty settings file when hooks disabled."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        instruction = fixtures_dir / "instructions" / "simple_task.txt"

        cli = ClaudeAgentCLI()
        audit_config = AgentConfigPresets.audit()
        assert audit_config.enable_hooks is False

        exit_code, output = cli.run_print(  # test-fixture
            instruction_file=instruction,
            stdin="test",
            agent_config=audit_config,
        )

        assert exit_code == 0

    def test_compute_disallowed_tools_complement(self):  # test-fixture
        """compute_disallowed_tools() returns correct complement."""
        allowed = ["WebSearch", "WebFetch"]
        disallowed = ClaudeAgentCLI.compute_disallowed_tools(allowed)

        assert len(disallowed) == 13
        assert "WebSearch" not in disallowed
        assert "WebFetch" not in disallowed
        assert "Bash" in disallowed
        assert "Read" in disallowed
        assert sorted(disallowed) == disallowed

    def test_compute_disallowed_tools_none(self):  # test-fixture
        """compute_disallowed_tools(None) returns empty list."""
        result = ClaudeAgentCLI.compute_disallowed_tools(None)
        assert result == []

    def test_compute_disallowed_tools_unknown_tool(self):  # test-fixture
        """compute_disallowed_tools() raises on unknown tool."""
        with pytest.raises(ValueError) as exc_info:  # test-fixture
            ClaudeAgentCLI.compute_disallowed_tools(["UnknownTool"])

        assert "unknown" in str(exc_info.value).lower()

    def test_load_instruction_template_substitution(self):  # test-fixture
        """_load_instruction() substitutes {date} template."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:  # test-fixture
            f.write("Date: {date}")
            temp_path = Path(f.name)

        try:  # test-fixture
            cli = ClaudeAgentCLI()
            result = cli._load_instruction(temp_path)

            assert "{date}" not in result
            assert "Date:" in result
        finally:  # test-fixture
            if temp_path.exists():  # test-fixture
                temp_path.unlink()  # test-fixture
