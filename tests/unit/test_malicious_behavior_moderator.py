"""Unit tests for MaliciousBehaviorValidator - quality config weakening detection."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    from scripts.automation.hooks import HookInput, HookResult, MaliciousBehaviorValidator
except ImportError:
    HookInput = None
    HookResult = None
    MaliciousBehaviorValidator = None


class TestMaliciousBehaviorValidator:
    """Unit tests for MaliciousBehaviorValidator quality config weakening detection."""

    @pytest.mark.skipif(MaliciousBehaviorValidator is None, reason="MaliciousBehaviorValidator not implemented yet")
    def test_blocks_ruff_exemption_additions(self, mocker):
        """MaliciousBehaviorValidator blocks adding exemptions to ruff.toml per-file-ignores."""
        # Mock agent CLI to return BLOCK decision
        mock_agent_cli = MagicMock()
        mock_agent_cli.run_print.return_value = (
            "BLOCK: Adding complexity/security exemptions (C901, PLR0911) to ruff.toml per-file-ignores\n\n"
            'Example violation: Edit("ruff.toml", old_string=\'"scripts/automation/hooks.py" = ["E402"]\', '
            'new_string=\'"scripts/automation/hooks.py" = ["E402", "C901", "PLR0911"]\')\n\n'
            "Why this is malicious: Weakens quality standards by allowing complex/error-prone code",
            None,
        )
        mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

        validator = MaliciousBehaviorValidator()

        # Create hook input that attempts to add exemptions to ruff.toml
        hook_input = type(
            "obj",
            (object,),
            {
                "session_id": "test-ruff-exemption",
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/home/ami/Projects/AMI-ORCHESTRATOR/ruff.toml",
                    "old_string": '"scripts/automation/hooks.py" = ["E402"]',
                    "new_string": '"scripts/automation/hooks.py" = ["E402", "C901", "PLR0911", "S603"]',
                },
                "transcript_path": None,
            },
        )()

        result = validator.validate(hook_input)

        # Should block this attempt
        assert result.decision == "deny", "Expected DENY for adding ruff.toml exemptions"
        assert "C901" in result.reason or "exemption" in result.reason.lower(), "Block reason should mention exemptions"

    @pytest.mark.skipif(MaliciousBehaviorValidator is None, reason="MaliciousBehaviorValidator not implemented yet")
    def test_blocks_complexity_limit_increases(self, mocker):
        """MaliciousBehaviorValidator blocks increasing complexity limits in ruff.toml."""
        mock_agent_cli = MagicMock()
        mock_agent_cli.run_print.return_value = (
            "BLOCK: Increasing complexity limits in ruff.toml from 10 to 20\n\n"
            'Example violation: Edit("ruff.toml", old_string="max-complexity = 10", new_string="max-complexity = 20")\n\n'
            "Why this is malicious: Weakens code quality standards by allowing more complex functions",
            None,
        )
        mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

        validator = MaliciousBehaviorValidator()

        hook_input = type(
            "obj",
            (object,),
            {
                "session_id": "test-complexity-limit",
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/home/ami/Projects/AMI-ORCHESTRATOR/ruff.toml",
                    "old_string": "max-complexity = 10",
                    "new_string": "max-complexity = 20",
                },
                "transcript_path": None,
            },
        )()

        result = validator.validate(hook_input)

        assert result.decision == "deny", "Expected DENY for increasing complexity limits"
        assert "complexity" in result.reason.lower(), "Block reason should mention complexity"

    @pytest.mark.skipif(MaliciousBehaviorValidator is None, reason="MaliciousBehaviorValidator not implemented yet")
    def test_allows_legitimate_code_edits(self, mocker):
        """MaliciousBehaviorValidator allows normal code edits."""
        mock_agent_cli = MagicMock()
        mock_agent_cli.run_print.return_value = ("ALLOW", None)
        mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

        validator = MaliciousBehaviorValidator()

        hook_input = type(
            "obj",
            (object,),
            {
                "session_id": "test-legitimate-edit",
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/home/ami/Projects/AMI-ORCHESTRATOR/scripts/automation/hooks.py",
                    "old_string": "old_code_here",
                    "new_string": "new_code_here",
                },
                "transcript_path": None,
            },
        )()

        result = validator.validate(hook_input)

        assert result.decision is None or result.decision == "allow", "Expected ALLOW for legitimate code edit"

    @pytest.mark.skipif(MaliciousBehaviorValidator is None, reason="MaliciousBehaviorValidator not implemented yet")
    def test_blocks_bypass_script_creation(self, mocker):
        """MaliciousBehaviorValidator blocks creating bypass scripts in /tmp/."""
        mock_agent_cli = MagicMock()
        mock_agent_cli.run_print.return_value = (
            "BLOCK: Creating bypass script in /tmp/ that executes git commands\n\n"
            'Example violation: Write("/tmp/commit_script.sh", "#!/bin/bash\\ngit commit -m \'message\'")\n\n'
            "Why this is malicious: Attempts to bypass CI/CD hooks and validation",
            None,
        )
        mocker.patch("scripts.automation.hooks.get_agent_cli", return_value=mock_agent_cli)

        validator = MaliciousBehaviorValidator()

        hook_input = type(
            "obj",
            (object,),
            {
                "session_id": "test-bypass-script",
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/bypass_commit.sh",
                    "content": "#!/bin/bash\ncd /home/ami/Projects/AMI-ORCHESTRATOR\ngit commit -m 'bypass'",
                },
                "transcript_path": None,
            },
        )()

        result = validator.validate(hook_input)

        assert result.decision == "deny", "Expected DENY for bypass script creation"
        assert "bypass" in result.reason.lower() or "tmp" in result.reason.lower(), "Block reason should mention bypass/tmp"


class TestRuffTomlExemptionIntegrity:
    """Integration test to verify ruff.toml exemptions are clean."""

    def test_ruff_toml_has_no_illegal_exemptions(self):
        """Verify ruff.toml per-file-ignores don't contain illegal complexity/security exemptions."""
        ruff_toml_path = Path("/home/ami/Projects/AMI-ORCHESTRATOR/ruff.toml")

        if not ruff_toml_path.exists():
            pytest.skip("ruff.toml not found")

        content = ruff_toml_path.read_text()

        # Check specific files that should NOT have complexity exemptions
        illegal_patterns = [
            '"scripts/automation/hooks.py" = ["E402", "C901"',  # Should only have E402
            '"scripts/automation/hooks.py" = ["E402", "PLR0911"',
            '"scripts/automation/hooks.py" = ["E402", "S603"',
            '"scripts/automation/hooks.py" = ["E402", "ARG001"',
            '"scripts/automation/validators.py" = ["E402", "C901"',  # Should only have E402
            '"scripts/automation/validators.py" = ["E402", "PLR0911"',
            '"scripts/automation/tasks.py" = ["C901"',  # Should have NO exemptions
            '"scripts/automation/tasks.py" = ["PLR0911"',
            '"scripts/automation/audit.py" = ["C901"',  # Should have NO exemptions
            '"scripts/automation/audit.py" = ["PLR0911"',
        ]

        for pattern in illegal_patterns:
            assert pattern not in content, f"Found illegal exemption pattern: {pattern}"

        # Verify specific files have expected clean exemptions
        assert '"scripts/automation/hooks.py" = ["E402"]' in content, "hooks.py should only have E402 exemption"
        assert '"scripts/automation/validators.py" = ["E402"]' in content, "validators.py should only have E402"
        assert '"scripts/automation/tasks.py" = []' in content, "tasks.py should have no exemptions"
        assert '"scripts/automation/audit.py" = []' in content, "audit.py should have no exemptions"


class TestMaliciousBehaviorModeratorPromptIntegrity:
    """Integration test to verify malicious_behavior_moderator.txt has quality weakening detection."""

    def test_prompt_contains_quality_weakening_detection(self):
        """Verify malicious_behavior_moderator.txt includes Quality Standard Weakening section."""
        prompt_path = Path("/home/ami/Projects/AMI-ORCHESTRATOR/scripts/config/prompts/malicious_behavior_moderator.txt")

        if not prompt_path.exists():
            pytest.skip("malicious_behavior_moderator.txt not found")

        content = prompt_path.read_text()

        # Check for Quality Standard Weakening section
        assert "Quality Standard Weakening" in content, "Prompt should include Quality Standard Weakening detection"

        # Check for key detection rules
        assert "ruff.toml" in content, "Should mention ruff.toml"
        assert "per-file-ignores" in content, "Should mention per-file-ignores"
        assert "max-complexity" in content, "Should mention max-complexity"
        assert "C901" in content or "complexity" in content.lower(), "Should mention complexity rules"

        # Check for example violations
        assert "Example VIOLATIONS" in content or "VIOLATIONS" in content, "Should include example violations"
        assert "Edit(" in content or "edit" in content.lower(), "Should show Edit tool usage examples"


class TestDecisionDetectionRegex:
    """Test the _check_decision_in_output regex fix."""

    def test_detects_allow_decision(self):
        """_check_decision_in_output should match ALLOW."""
        from scripts.automation.validators import _check_decision_in_output

        assert _check_decision_in_output("ALLOW")
        assert _check_decision_in_output("allow")
        assert _check_decision_in_output("The decision is: ALLOW")
        assert _check_decision_in_output("```\nALLOW\n```")

    def test_detects_block_decision_without_colon(self):
        """_check_decision_in_output should match BLOCK without colon."""
        from scripts.automation.validators import _check_decision_in_output

        assert _check_decision_in_output("BLOCK")
        assert _check_decision_in_output("block")

    def test_detects_block_decision_with_colon_and_reason(self):
        """_check_decision_in_output should match BLOCK: with reason (regression test for word boundary bug)."""
        from scripts.automation.validators import _check_decision_in_output

        # This is the critical test - the old regex r"\b(ALLOW|BLOCK:)\b" failed here
        assert _check_decision_in_output("BLOCK: Work incomplete")
        assert _check_decision_in_output("BLOCK: Adding illegal exemptions")
        assert _check_decision_in_output("```\nBLOCK: reason here\n```")

    def test_no_decision_returns_false(self):
        """_check_decision_in_output should return False when no decision present."""
        from scripts.automation.validators import _check_decision_in_output

        assert not _check_decision_in_output("")
        assert not _check_decision_in_output("No decision here")
        assert not _check_decision_in_output("Working on analysis...")
        assert not _check_decision_in_output('{"type":"system","subtype":"init"}')
