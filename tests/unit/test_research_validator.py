#!/usr/bin/env bash
""":'
exec "$(dirname "$0")/../../scripts/ami-run.sh" "$0" "$@"
"""

from __future__ import annotations

"""Unit tests for ResearchValidator hook."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.automation.agent_cli import AgentExecutionError, AgentTimeoutError
from scripts.automation.hooks import HookInput, ResearchValidator

# Test constants
EXPECTED_WRITE_LINES = 6
EXPECTED_EDIT_LINES = 5
EXPECTED_NOTEBOOK_LINES = 7


@pytest.fixture
def temp_transcript():
    """Create temporary transcript file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        transcript_path = Path(f.name)
        # Write some sample messages
        messages = [
            {"role": "user", "content": "Add feature X"},
            {"role": "assistant", "content": "I'll add feature X"},
        ]
        for msg in messages:
            f.write(json.dumps(msg) + "\n")
    yield transcript_path
    transcript_path.unlink()


@pytest.fixture
def validator(tmp_path):
    """Create ResearchValidator instance."""
    with patch("scripts.automation.hooks.get_config") as mock_config:
        config_mock = Mock()
        config_mock.root = tmp_path  # Use tmp_path instead of /fake/root
        config_mock.get = Mock(
            side_effect=lambda key, default=None: {
                "research_validator.skip_threshold_lines": 5,
                "research_validator.lookback_messages": 30,
            }.get(key, default)
        )
        mock_config.return_value = config_mock
        return ResearchValidator(session_id="test-session")


def test_skip_bash_tool(validator):
    """Test that ResearchValidator skips non-Write/Edit/NotebookEdit tools."""
    hook_input = HookInput(
        session_id="test",
        hook_event_name="PreToolUse",
        tool_name="Bash",
        tool_input={"command": "ls"},
        transcript_path=None,
    )

    result = validator.validate(hook_input)
    assert result.decision is None or result.decision == "allow"


def test_skip_trivial_changes_write(validator):
    """Test that ResearchValidator skips Write with < 5 lines."""
    hook_input = HookInput(
        session_id="test",
        hook_event_name="PreToolUse",
        tool_name="Write",
        tool_input={
            "file_path": "/fake/file.py",
            "content": "line1\nline2\nline3\n",  # 3 lines
        },
        transcript_path=None,
    )

    result = validator.validate(hook_input)
    assert result.decision is None or result.decision == "allow"


def test_skip_trivial_changes_edit(validator):
    """Test that ResearchValidator skips Edit with < 5 lines."""
    hook_input = HookInput(
        session_id="test",
        hook_event_name="PreToolUse",
        tool_name="Edit",
        tool_input={
            "file_path": "/fake/file.py",
            "old_string": "old1\nold2\n",  # 2 lines
            "new_string": "new1\nnew2\nnew3\n",  # 3 lines (max = 3 < 5)
        },
        transcript_path=None,
    )

    result = validator.validate(hook_input)
    assert result.decision is None or result.decision == "allow"


def test_count_lines_changed_write():
    """Test _count_lines_changed for Write tool."""
    validator = ResearchValidator()

    lines = validator._count_lines_changed("Write", {"content": "line1\nline2\nline3\nline4\nline5\nline6\n"})
    assert lines == EXPECTED_WRITE_LINES


def test_count_lines_changed_edit():
    """Test _count_lines_changed for Edit tool."""
    validator = ResearchValidator()

    lines = validator._count_lines_changed(
        "Edit",
        {
            "old_string": "old1\nold2\n",  # 2 lines
            "new_string": "new1\nnew2\nnew3\nnew4\nnew5\n",  # 5 lines
        },
    )
    assert lines == EXPECTED_EDIT_LINES  # max(2, 5) = 5


def test_count_lines_changed_notebookedit():
    """Test _count_lines_changed for NotebookEdit tool."""
    validator = ResearchValidator()

    lines = validator._count_lines_changed("NotebookEdit", {"new_source": "cell1\ncell2\ncell3\ncell4\ncell5\ncell6\ncell7\n"})
    assert lines == EXPECTED_NOTEBOOK_LINES


def test_skip_no_transcript(validator):
    """Test that ResearchValidator skips when no transcript available."""
    hook_input = HookInput(
        session_id="test",
        hook_event_name="PreToolUse",
        tool_name="Write",
        tool_input={
            "file_path": "/fake/file.py",
            "content": "line1\nline2\nline3\nline4\nline5\nline6\n",  # 6 lines > threshold
        },
        transcript_path=None,
    )

    result = validator.validate(hook_input)
    assert result.decision is None or result.decision == "allow"


def test_allow_with_proper_research(validator, temp_transcript, tmp_path):
    """Test that ResearchValidator allows when moderator returns ALLOW."""
    # Create a real prompt file in temp location
    prompt_file = tmp_path / "research_validator_moderator.txt"
    prompt_file.write_text("Test prompt content")
    validator.prompt_path = prompt_file

    hook_input = HookInput(
        session_id="test",
        hook_event_name="PreToolUse",
        tool_name="Write",
        tool_input={
            "file_path": "/fake/file.py",
            "content": "line1\nline2\nline3\nline4\nline5\nline6\n",  # 6 lines > threshold
        },
        transcript_path=temp_transcript,
    )

    # Mock the moderator to return ALLOW
    with patch("scripts.automation.hooks.get_agent_cli"), patch("scripts.automation.hooks.run_moderator_with_retry") as mock_moderator:
        mock_moderator.return_value = ("ALLOW: Proper research shown", None)

        result = validator.validate(hook_input)
        assert result.decision is None or result.decision == "allow"


def test_block_without_research(validator, temp_transcript, tmp_path):
    """Test that ResearchValidator blocks when moderator returns BLOCK."""
    # Create a real prompt file in temp location
    prompt_file = tmp_path / "research_validator_moderator.txt"
    prompt_file.write_text("Test prompt content")
    validator.prompt_path = prompt_file

    hook_input = HookInput(
        session_id="test",
        hook_event_name="PreToolUse",
        tool_name="Write",
        tool_input={
            "file_path": "/fake/file.py",
            "content": "line1\nline2\nline3\nline4\nline5\nline6\n",  # 6 lines > threshold
        },
        transcript_path=temp_transcript,
    )

    # Mock the moderator to return BLOCK
    with patch("scripts.automation.hooks.get_agent_cli"), patch("scripts.automation.hooks.run_moderator_with_retry") as mock_moderator:
        mock_moderator.return_value = ("BLOCK: No WebFetch to read documentation", None)

        result = validator.validate(hook_input)
        assert result.decision == "deny"
        assert "RESEARCH VALIDATION FAILED" in result.reason
        assert "No WebFetch to read documentation" in result.reason


def test_fail_open_on_timeout(validator, temp_transcript, tmp_path):
    """Test that ResearchValidator fails open on timeout."""
    # Create a real prompt file in temp location
    prompt_file = tmp_path / "research_validator_moderator.txt"
    prompt_file.write_text("Test prompt content")
    validator.prompt_path = prompt_file

    hook_input = HookInput(
        session_id="test",
        hook_event_name="PreToolUse",
        tool_name="Write",
        tool_input={
            "file_path": "/fake/file.py",
            "content": "line1\nline2\nline3\nline4\nline5\nline6\n",
        },
        transcript_path=temp_transcript,
    )

    # Mock the moderator to timeout
    with patch("scripts.automation.hooks.get_agent_cli"), patch("scripts.automation.hooks.run_moderator_with_retry") as mock_moderator:
        mock_moderator.side_effect = AgentTimeoutError(100, ["claude"], 100.5)

        result = validator.validate(hook_input)
        # Should fail open (allow) on timeout
        assert result.decision is None or result.decision == "allow"


def test_fail_open_on_agent_error(validator, temp_transcript, tmp_path):
    """Test that ResearchValidator fails open on agent errors."""
    # Create a real prompt file in temp location
    prompt_file = tmp_path / "research_validator_moderator.txt"
    prompt_file.write_text("Test prompt content")
    validator.prompt_path = prompt_file

    hook_input = HookInput(
        session_id="test",
        hook_event_name="PreToolUse",
        tool_name="Write",
        tool_input={
            "file_path": "/fake/file.py",
            "content": "line1\nline2\nline3\nline4\nline5\nline6\n",
        },
        transcript_path=temp_transcript,
    )

    # Mock the moderator to fail
    with patch("scripts.automation.hooks.get_agent_cli"), patch("scripts.automation.hooks.run_moderator_with_retry") as mock_moderator:
        mock_moderator.side_effect = AgentExecutionError(["claude"], 1, "Agent failed", "error output")

        result = validator.validate(hook_input)
        # Should fail open (allow) on agent error
        assert result.decision is None or result.decision == "allow"


def test_fail_closed_on_unclear_output(validator, temp_transcript, tmp_path):
    """Test that ResearchValidator fails closed when moderator output is unclear."""
    # Create a real prompt file in temp location
    prompt_file = tmp_path / "research_validator_moderator.txt"
    prompt_file.write_text("Test prompt content")
    validator.prompt_path = prompt_file

    hook_input = HookInput(
        session_id="test",
        hook_event_name="PreToolUse",
        tool_name="Write",
        tool_input={
            "file_path": "/fake/file.py",
            "content": "line1\nline2\nline3\nline4\nline5\nline6\n",
        },
        transcript_path=temp_transcript,
    )

    # Mock the moderator to return unclear output
    with patch("scripts.automation.hooks.get_agent_cli"), patch("scripts.automation.hooks.run_moderator_with_retry") as mock_moderator:
        mock_moderator.return_value = ("Some unclear output without ALLOW or BLOCK", None)

        result = validator.validate(hook_input)
        # Should fail closed (deny) on unclear output
        assert result.decision == "deny"
        assert "MODERATOR OUTPUT UNCLEAR" in result.reason
