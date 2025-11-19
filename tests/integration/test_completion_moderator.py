"""Integration tests for completion moderator functionality."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest

from scripts.agents.cli.exceptions import AgentTimeoutError
from scripts.agents.workflows.core import HookInput, HookResult
from scripts.agents.workflows.response_validators import ResponseScanner


class TestCompletionModeratorIntegration:
    """Tests for ResponseScanner completion moderator integration."""

    @pytest.fixture
    def scanner(self) -> Generator[ResponseScanner, None, None]:
        """Create ResponseScanner instance with mocked config."""
        with patch("scripts.agents.workflows.response_validators.get_config") as mock_config, patch("loguru.logger") as mock_get_logger:
            # Create the mock config and its methods
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = True
            mock_config_instance.root = Path("/fake/root")
            mock_config.return_value = mock_config_instance

            # Create a mock logger to be used consistently
            mock_logger_instance = Mock()
            mock_get_logger.return_value = mock_logger_instance
            scanner = ResponseScanner()
            scanner.config = mock_config_instance
            # Use the same mock logger instance for the scanner
            scanner.logger = mock_logger_instance
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
        # Ensure the transcript exists and contains WORK DONE
        assert test_transcript.exists()

        # Read the content to ensure it has the expected format
        content = test_transcript.read_text()
        assert "WORK DONE" in content

        hook_input = HookInput(
            session_id="test-session",
            hook_event_name="Stop",
            tool_name=None,
            tool_input=None,
            transcript_path=test_transcript,
        )

        with patch.object(scanner, "_validate_completion") as mock_validate:
            # Updated to match new security behavior - now returns block instead of allow for bare ALLOW
            mock_validate.return_value = HookResult(decision="block", reason="Security validation failed")

            result = scanner.validate(hook_input)

            # Should have called _validate_completion for WORK DONE marker
            # If this fails, it means check_early_allow_conditions is returning True (possibly file doesn't exist)
            mock_validate.assert_called_once_with("test-session", test_transcript, "I created hello.py with the function.\n\nWORK DONE")
            assert result.decision == "block"  # Updated for security improvements

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
        """Test validation behavior when moderator is disabled."""
        # Set up the mock to return False for the completion moderator enabled config, defaults for others
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": False,  # disabled
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)

        # Mock load_session_todos to return empty list to avoid todo check blocking
        with (
            patch("scripts.agents.workflows.completion_validator.load_session_todos", return_value=[]),
            patch("scripts.agents.workflows.completion_validator.get_config") as mock_get_config,
        ):
            # Also mock the CompletionValidator's get_config to ensure moderator is disabled there too
            config_instance = Mock()

            # Configure the mock to return False specifically for the completion moderator key
            def config_get(key, default=None):
                if key == "response_scanner.completion_moderator_enabled":
                    return False
                # Return appropriate defaults for other keys
                defaults_map = {
                    "prompts.dir": "scripts/config/prompts",
                    "prompts.completion_moderator": "completion_moderator.txt",
                    "hooks.file": "scripts/config/hooks.yaml",
                }
                return defaults_map.get(key, default if default is not None else True)

            config_instance.get.side_effect = config_get
            # Set the root properly
            config_instance.root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")
            mock_get_config.return_value = config_instance

            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # Should allow when moderator is disabled and no incomplete todos (current behavior)
            assert result.decision == "allow"

    def test_validate_completion_allow_decision(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test parsing decision from moderator output - updated for security improvements."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        with patch("scripts.agents.workflows.completion_validator.run_moderator_with_retry") as mock_run_moderator:
            mock_run_moderator.return_value = ("ALLOW: Implementation complete with tests", None)

            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # With proper ALLOW format, should allow
            assert result.decision == "allow"

    def test_validate_completion_block_decision(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test parsing BLOCK decision from moderator output - updated for security improvements."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        with patch("scripts.agents.workflows.completion_validator.run_moderator_with_retry") as mock_run_moderator, patch("loguru.logger") as mock_get_logger:
            mock_run_moderator.return_value = ("BLOCK: Tests are failing, bug still present", None)

            # Make get_logger return the same mock logger as the scanner
            mock_get_logger.return_value = scanner.logger

            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # Should block (this format is still valid)
            assert result.decision == "block"
            assert result.reason is not None
            assert "Tests are failing" in result.reason

    def test_validate_completion_unclear_decision(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test handling of unclear moderator output - updated for security improvements."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        with patch("scripts.agents.workflows.completion_validator.run_moderator_with_retry") as mock_run_moderator:
            mock_run_moderator.return_value = ("Some unclear output with no decision", None)

            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # Should fail-closed (block)
            assert result.decision == "block"
            assert result.reason is not None
            assert "COMPLETION VALIDATION UNCLEAR" in result.reason
            cast(Mock, scanner.logger.warning).assert_called()

    def test_validate_completion_missing_prompt(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test handling of missing moderator prompt file - updated for security improvements."""

        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "nonexistent_prompt.txt",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        # Mock Path.exists to simulate missing file
        def mock_path_exists(path_self):
            # Only return False for the specific moderator prompt path we're testing
            if "nonexistent_prompt.txt" in str(path_self):
                return False
            # For all other paths, use the original exists method
            return Path(path_self).exists()

        with patch.object(Path, "exists", side_effect=mock_path_exists):
            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # Should fail-closed (block) due to missing prompt file
            assert result.decision == "block"
            assert result.reason is not None
            assert "COMPLETION VALIDATION ERROR" in result.reason
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
        """Test handling of agent execution errors - updated for security improvements."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        with patch("scripts.agents.workflows.completion_validator.run_moderator_with_retry") as mock_run_moderator:
            mock_run_moderator.side_effect = AgentTimeoutError(120, ["claude"], 120.0)

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
        """Test feedback validation behavior with incomplete todos - updated for security improvements."""
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
            with patch("scripts.agents.workflows.completion_validator.load_session_todos") as mock_load_todos:
                mock_load_todos.return_value = [
                    {"status": "pending", "content": "Fix bug"},
                    {"status": "in_progress", "content": "Run tests"},
                ]

                # Mock agent CLI to return ALLOW with explanation
                with (
                    patch("scripts.agents.workflows.completion_validator.run_moderator_with_retry") as mock_run_moderator,
                    patch("loguru.logger") as mock_get_logger,
                ):
                    mock_run_moderator.return_value = ("ALLOW: Feedback provided, continuing work", None)

                    # Make get_logger return the same mock logger as the scanner
                    mock_get_logger.return_value = scanner.logger

                    # Call _validate_completion with FEEDBACK message
                    result = scanner._validate_completion("test-session", transcript, "FEEDBACK: Hook already has complete propagation")

                    # With proper ALLOW format, should allow (and skip todo check for feedback)
                    assert result.decision == "allow"
        finally:
            transcript.unlink()

    def test_validate_completion_work_done_checks_incomplete_todos(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test that WORK DONE marker still checks for incomplete todos and blocks."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,  # Enable moderator to ensure todo check runs
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        # Mock the load_session_todos function to return incomplete tasks
        # Since load_session_todos is imported directly into the completion_validator module,
        # we need to patch it in that module's namespace
        with patch("scripts.agents.workflows.completion_validator.load_session_todos") as mock_load_todos:
            # Return incomplete todos to trigger the blocking condition
            mock_load_todos.return_value = [
                {"status": "pending", "content": "Fix bug"},
                {"status": "in_progress", "content": "Run tests"},
            ]

            # We still need to mock the moderator in case there are issues in the control flow
            # But the todo check should happen first and block before the moderator call
            with patch("scripts.agents.workflows.completion_validator.run_moderator_with_retry"):
                # Call _validate_completion with WORK DONE message
                result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

                # Should BLOCK on incomplete todos when WORK DONE is present
                # The incomplete todo check should prevent the moderator from running
                assert result.decision == "block"
                assert result.reason is not None
                assert "INCOMPLETE TASKS" in result.reason
                assert "Fix bug" in result.reason
                assert "Run tests" in result.reason

    def test_validate_completion_markdown_code_block(self, scanner: ResponseScanner, test_transcript: Path) -> None:
        """Test parsing decision from markdown code blocks - updated for security improvements."""
        cast(Mock, scanner.config.get).side_effect = lambda key, default=None: {
            "response_scanner.completion_moderator_enabled": True,
            "prompts.dir": "scripts/config/prompts",
            "prompts.completion_moderator": "completion_moderator.txt",
            "hooks.file": "scripts/config/hooks.yaml",
        }.get(key, default)
        cast(Any, scanner.config).root = Path("/home/ami/Projects/AMI-ORCHESTRATOR")

        with patch("scripts.agents.workflows.completion_validator.run_moderator_with_retry") as mock_run_moderator:
            # Moderator output wrapped in code blocks with explanation
            mock_run_moderator.return_value = ("```\nALLOW: Task completed successfully\n```", None)

            result = scanner._validate_completion("test-session", test_transcript, "WORK DONE")

            # With proper ALLOW format in code blocks, should allow
            assert result.decision == "allow"
