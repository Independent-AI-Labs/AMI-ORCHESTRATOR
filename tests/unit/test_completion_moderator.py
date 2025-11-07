"""Integration tests for completion moderator functionality."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest

from scripts.automation.agent_cli import AgentTimeoutError
from scripts.automation.hooks import HookInput, HookResult, ResponseScanner


class TestCompletionModeratorIntegration:
    """Tests for ResponseScanner completion moderator integration."""

    @pytest.fixture
    def scanner(self) -> Generator[ResponseScanner, None, None]:
        """Create ResponseScanner instance with mocked config."""
        with patch("scripts.automation.hooks.get_config") as mock_config, patch("scripts.automation.hooks.get_logger"):
            mock_config.return_value.get.return_value = True
            scanner = ResponseScanner()
            scanner.config = Mock()
            scanner.logger = Mock()
            yield scanner

    @pytest.fixture
    def test_transcript(self) -> Generator[Path, None, None]:
        """Create test transcript file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            # User message
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Create hello.py with hello() function"}]},
                "timestamp": "2025-01-01T12:00:00Z",
            }
            tmp.write(json.dumps(user_msg) + "\n")

            # Assistant message with WORK DONE
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "I created hello.py with the function.\n\nWORK DONE"}]},
                "timestamp": "2025-01-01T12:00:01Z",
            }
            tmp.write(json.dumps(assistant_msg) + "\n")
            tmp_path = tmp.name

        yield Path(tmp_path)
        Path(tmp_path).unlink()

    def test_validate_calls_moderator_on_work_done(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test that validate() calls moderator when WORK DONE marker found."""
        hook_input = HookInput(
            session_id="test-session",
            hook_event_name="Stop",
            tool_name=None,
            tool_input=None,
            transcript_path=test_transcript,
        )

        with patch.object(scanner, "_validate_completion") as mock_validate:
            mock_validate.return_value = HookResult.allow()

            result = scanner.validate(hook_input)

            # Should have called _validate_completion
            mock_validate.assert_called_once_with("test-session", test_transcript, "I created hello.py with the function.\n\nWORK DONE")
            assert result.decision is None  # allow() returns None decision

    def test_validate_blocks_without_completion_marker(self, scanner: ResponseScanner) -> None:
        """Test that validate() blocks when no completion marker present."""
        # Create transcript without completion marker
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Just some response"}]},
            }
            tmp.write(json.dumps(assistant_msg) + "\n")
            transcript_path = tmp.name

        transcript = Path(transcript_path)

        try:
            hook_input = HookInput(
                session_id="test-session",
                hook_event_name="Stop",
                tool_name=None,
                tool_input=None,
                transcript_path=transcript,
            )

            result = scanner.validate(hook_input)

            # Should block with "COMPLETION MARKER REQUIRED" message
            assert result.decision == "block"
            assert result.reason is not None
            assert "COMPLETION MARKER REQUIRED" in result.reason
        finally:
            transcript.unlink()

    def test_validate_completion_moderator_disabled(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test that moderator is skipped when disabled in config."""
        cast(Mock, scanner.config.get).return_value = False  # disabled

        result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

        # Should allow without running moderator
        assert result.decision is None  # allow() returns None

    def test_validate_completion_allow_decision(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test parsing ALLOW decision from moderator output."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        with patch("scripts.automation.hooks.get_agent_cli") as mock_get_cli:
            mock_cli = Mock()
            mock_cli.run_print.return_value = ("ALLOW", None)
            mock_get_cli.return_value = mock_cli

            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # Should allow
            assert result.decision == "allow"
            # Bare "ALLOW" triggers legacy format warning, not info log
            cast(Mock, scanner.logger.warning).assert_any_call(
                "completion_moderator_allow_no_explanation", session_id="test-session", note="Moderator used legacy ALLOW format without explanation"
            )

    def test_validate_completion_block_decision(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test parsing BLOCK decision from moderator output."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        with patch("scripts.automation.hooks.get_agent_cli") as mock_get_cli:
            mock_cli = Mock()
            mock_cli.run_print.return_value = ("BLOCK: Tests are failing, bug still present", None)
            mock_get_cli.return_value = mock_cli

            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # Should block
            assert result.decision == "block"
            assert result.reason is not None
            assert "Tests are failing" in result.reason

    def test_validate_completion_unclear_decision(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test handling of unclear moderator output."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        with patch("scripts.automation.hooks.get_agent_cli") as mock_get_cli:
            mock_cli = Mock()
            mock_cli.run_print.return_value = ("Some unclear output with no decision", None)
            mock_get_cli.return_value = mock_cli

            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # Should fail-closed (block)
            assert result.decision == "block"
            assert result.reason is not None
            assert "COMPLETION VALIDATION UNCLEAR" in result.reason
            cast(Mock, scanner.logger.warning).assert_called()

    def test_validate_completion_missing_prompt(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test handling of missing moderator prompt file."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "nonexistent_prompt.txt",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

        # Should fail-closed (block)
        assert result.decision == "block"
        assert result.reason is not None
        assert "Moderator prompt not found" in result.reason
        cast(Mock, scanner.logger.error).assert_called()

    def test_validate_completion_transcript_error(self, scanner: ResponseScanner) -> None:
        """Test handling of transcript read errors."""
        cast(Mock, scanner.config.get).return_value = True

        # Non-existent transcript
        result = scanner._validate_completion("test-session", Path("/nonexistent/transcript.jsonl"), "WORK DONE")

        # Should fail-closed (block)
        assert result.decision == "block"
        assert result.reason is not None
        assert "Failed to read conversation context" in result.reason

    def test_validate_completion_agent_execution_error(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test handling of agent execution errors."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        with patch("scripts.automation.hooks.get_agent_cli") as mock_get_cli:
            mock_cli = Mock()
            mock_cli.run_print.side_effect = AgentTimeoutError(120, ["claude"], 120.0)
            mock_get_cli.return_value = mock_cli

            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # Should fail-closed (block)
            assert result.decision == "block"
            assert result.reason is not None
            assert "COMPLETION VALIDATION TIMEOUT" in result.reason
            cast(Mock, scanner.logger.error).assert_called()

    def test_validate_completion_with_feedback_marker(self, scanner: ResponseScanner) -> None:
        """Test that FEEDBACK: marker also triggers validation."""
        # Create transcript with FEEDBACK: marker
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "FEEDBACK: Need clarification on requirements"}]},
            }
            tmp.write(json.dumps(assistant_msg) + "\n")
            transcript_path = tmp.name

        transcript = Path(transcript_path)

        try:
            with patch.object(scanner, "_validate_completion") as mock_validate:
                mock_validate.return_value = HookResult.allow()

                hook_input = HookInput(
                    session_id="test-session",
                    hook_event_name="Stop",
                    tool_name=None,
                    tool_input=None,
                    transcript_path=transcript,
                )

                scanner.validate(hook_input)

                # Should have called _validate_completion for FEEDBACK: too
                mock_validate.assert_called_once()
        finally:
            transcript.unlink()

    def test_validate_completion_feedback_skips_incomplete_todo_check(self, scanner: ResponseScanner) -> None:
        """Test that FEEDBACK: marker skips incomplete todo check (allows stop even with open todos)."""
        # Create transcript with FEEDBACK: marker
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "FEEDBACK: Hook already has complete propagation"}]},
            }
            tmp.write(json.dumps(assistant_msg) + "\n")
            transcript_path = tmp.name

        transcript = Path(transcript_path)

        try:
            cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
                "response_scanner.completion_moderator_enabled": True,
                "prompts.dir": "scripts/config/prompts",
                "prompts.completion_moderator": "completion_moderator.txt",
                "hooks.file": "scripts/config/hooks.yaml",
            }.get(key, default)
            cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

            # Mock load_session_todos to return incomplete todos
            with patch("scripts.automation.hooks.load_session_todos") as mock_load_todos:
                mock_load_todos.return_value = [
                    {"status": "pending", "content": "Fix bug"},
                    {"status": "in_progress", "content": "Run tests"},
                ]

                # Mock agent CLI to return ALLOW
                with patch("scripts.automation.hooks.get_agent_cli") as mock_get_cli:
                    mock_cli = Mock()
                    mock_cli.run_print.return_value = ("ALLOW", None)
                    mock_get_cli.return_value = mock_cli

                    # Call _validate_completion with FEEDBACK message
                    result = scanner._validate_completion("test-session", transcript, "FEEDBACK: Hook already has complete propagation")

                    # Should NOT block on incomplete todos when FEEDBACK is present
                    # Should proceed to moderator and allow
                    assert result.decision == "allow"
        finally:
            transcript.unlink()

    def test_validate_completion_work_done_checks_incomplete_todos(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test that WORK DONE marker still checks for incomplete todos and blocks."""
        cast(Mock, scanner.config.get).return_value = True

        # Mock load_session_todos to return incomplete todos
        with patch("scripts.automation.hooks.load_session_todos") as mock_load_todos:
            mock_load_todos.return_value = [
                {"status": "pending", "content": "Fix bug"},
                {"status": "in_progress", "content": "Run tests"},
            ]

            # Call _validate_completion with WORK DONE message
            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # Should BLOCK on incomplete todos when WORK DONE is present
            assert result.decision == "block"
            assert result.reason is not None
            assert "INCOMPLETE TASKS" in result.reason
            assert "Fix bug" in result.reason
            assert "Run tests" in result.reason

    def test_validate_completion_markdown_code_block(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test parsing ALLOW/BLOCK from markdown code blocks."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        with patch("scripts.automation.hooks.get_agent_cli") as mock_get_cli:
            mock_cli = Mock()
            # Moderator output wrapped in code blocks
            mock_cli.run_print.return_value = ("```\nALLOW\n```", None)
            mock_get_cli.return_value = mock_cli

            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # Should still parse ALLOW correctly
            assert result.decision == "allow"
            # Bare "ALLOW" in code fence triggers legacy format warning, not info log
            cast(Mock, scanner.logger.warning).assert_any_call(
                "completion_moderator_allow_no_explanation", session_id="test-session", note="Moderator used legacy ALLOW format without explanation"
            )
