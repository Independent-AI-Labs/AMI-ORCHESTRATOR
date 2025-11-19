"""Unit tests for moderator todo list integration."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.agents.workflows.core import load_session_todos, prepare_moderator_context

# Test constants
THREE_TODOS = 3
FIRST_TODO = 0
SECOND_TODO = 1
THIRD_TODO = 2


class TestLoadSessionTodos:
    """Tests for load_session_todos() function."""

    def test_load_existing_todos(self, tmp_path: Path) -> None:
        """Test loading existing todo list from file."""
        # Create mock .claude/todos directory
        todos_dir = tmp_path / ".claude" / "todos"
        todos_dir.mkdir(parents=True)

        # Create todo file
        session_id = "test-session-123"
        todo_file = todos_dir / f"{session_id}-agent-{session_id}.json"

        todos = [
            {"content": "Fix authentication bug", "status": "completed", "activeForm": "Fixing authentication bug"},
            {"content": "Add logging", "status": "in_progress", "activeForm": "Adding logging"},
            {"content": "Update tests", "status": "pending", "activeForm": "Updating tests"},
        ]

        with todo_file.open("w") as f:
            json.dump(todos, f)

        # Mock Path.home() to return our tmp_path

        original_path_home = Path.home

        def mock_home():
            return tmp_path

        Path.home = staticmethod(mock_home)

        try:
            result = load_session_todos(session_id)

            assert len(result) == THREE_TODOS
            assert result[FIRST_TODO]["content"] == "Fix authentication bug"
            assert result[FIRST_TODO]["status"] == "completed"
            assert result[SECOND_TODO]["content"] == "Add logging"
            assert result[SECOND_TODO]["status"] == "in_progress"
            assert result[THIRD_TODO]["content"] == "Update tests"
            assert result[THIRD_TODO]["status"] == "pending"
        finally:
            # Restore original Path.home
            Path.home = staticmethod(original_path_home)

    def test_load_nonexistent_todos(self, tmp_path: Path) -> None:
        """Test loading todos when file doesn't exist returns empty list."""
        # Create mock .claude/todos directory but no file
        todos_dir = tmp_path / ".claude" / "todos"
        todos_dir.mkdir(parents=True)

        session_id = "nonexistent-session"

        # Mock Path.home()
        original_path_home = Path.home

        def mock_home():
            return tmp_path

        Path.home = staticmethod(mock_home)

        try:
            result = load_session_todos(session_id)
            assert result == []
        finally:
            Path.home = staticmethod(original_path_home)

    def test_load_invalid_todos_json(self, tmp_path: Path) -> None:
        """Test loading todos with invalid JSON returns empty list."""
        # Create mock .claude/todos directory
        todos_dir = tmp_path / ".claude" / "todos"
        todos_dir.mkdir(parents=True)

        session_id = "test-session-456"
        todo_file = todos_dir / f"{session_id}-agent-{session_id}.json"

        # Write invalid JSON
        with todo_file.open("w") as f:
            f.write("not valid json{")

        # Mock Path.home()
        original_path_home = Path.home

        def mock_home():
            return tmp_path

        Path.home = staticmethod(mock_home)

        try:
            result = load_session_todos(session_id)
            assert result == []
        finally:
            Path.home = staticmethod(original_path_home)

    def test_load_todos_not_list(self, tmp_path: Path) -> None:
        """Test loading todos with non-list data returns empty list."""
        # Create mock .claude/todos directory
        todos_dir = tmp_path / ".claude" / "todos"
        todos_dir.mkdir(parents=True)

        session_id = "test-session-789"
        todo_file = todos_dir / f"{session_id}-agent-{session_id}.json"

        # Write valid JSON but not a list
        with todo_file.open("w") as f:
            json.dump({"not": "a list"}, f)

        # Mock Path.home()
        original_path_home = Path.home

        def mock_home():
            return tmp_path

        Path.home = staticmethod(mock_home)

        try:
            result = load_session_todos(session_id)
            assert result == []
        finally:
            Path.home = staticmethod(original_path_home)


class TestPrepareModeratorContextWithTodos:
    """Tests for prepare_moderator_context() with todo list parameter."""

    def test_context_with_todos_appended(self) -> None:
        """Test that todos are appended to conversation context."""
        # Create test transcript
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            # User message
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Fix the bug"}]},
                "timestamp": "2025-01-01T12:00:00Z",
            }
            tmp.write(json.dumps(user_msg) + "\n")

            # Assistant message
            assistant_msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Fixed the bug in handler.py"}]},
                "timestamp": "2025-01-01T12:00:01Z",
            }
            tmp.write(json.dumps(assistant_msg) + "\n")
            transcript_path = Path(tmp.name)

        try:
            todos = [
                {"content": "Fix the bug", "status": "completed", "activeForm": "Fixing the bug"},
                {"content": "Add tests", "status": "pending", "activeForm": "Adding tests"},
            ]

            context = prepare_moderator_context(transcript_path, todos=todos)

            # Verify conversation context is present
            assert "Fix the bug" in context
            assert "Fixed the bug in handler.py" in context

            # Verify todo list section is present
            assert "# Current Task List" in context
            assert "[✅ completed] Fix the bug" in context
            assert "[⏳ pending] Add tests" in context

        finally:
            transcript_path.unlink()

    def test_context_without_todos(self) -> None:
        """Test that context works without todos parameter."""
        # Create test transcript
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Hello"}]},
                "timestamp": "2025-01-01T12:00:00Z",
            }
            tmp.write(json.dumps(user_msg) + "\n")
            transcript_path = Path(tmp.name)

        try:
            context = prepare_moderator_context(transcript_path, todos=None)

            # Verify conversation context is present
            assert "Hello" in context

            # Verify no todo list section
            assert "# Current Task List" not in context

        finally:
            transcript_path.unlink()

    def test_context_with_empty_todos(self) -> None:
        """Test that empty todo list doesn't add section."""
        # Create test transcript
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Test"}]},
                "timestamp": "2025-01-01T12:00:00Z",
            }
            tmp.write(json.dumps(user_msg) + "\n")
            transcript_path = Path(tmp.name)

        try:
            context = prepare_moderator_context(transcript_path, todos=[])

            # Verify conversation context is present
            assert "Test" in context

            # Verify no todo list section (empty list)
            assert "# Current Task List" not in context

        finally:
            transcript_path.unlink()

    def test_todos_formatting(self) -> None:
        """Test that todos are formatted correctly with emoji status indicators."""
        # Create test transcript
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            user_msg = {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Task"}]},
                "timestamp": "2025-01-01T12:00:00Z",
            }
            tmp.write(json.dumps(user_msg) + "\n")
            transcript_path = Path(tmp.name)

        try:
            todos = [
                {"content": "Task 1", "status": "pending", "activeForm": "Working on task 1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "Working on task 2"},
                {"content": "Task 3", "status": "completed", "activeForm": "Completing task 3"},
                {"content": "Task 4", "status": "unknown_status", "activeForm": "Unknown task"},
            ]

            context = prepare_moderator_context(transcript_path, todos=todos)

            # Verify emojis are present
            assert "1. [⏳ pending] Task 1" in context
            assert "2. [🔄 in_progress] Task 2" in context
            assert "3. [✅ completed] Task 3" in context
            assert "4. [❓ unknown_status] Task 4" in context

        finally:
            transcript_path.unlink()
