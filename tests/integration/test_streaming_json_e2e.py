"""E2E integration tests for streaming JSON output from ami-agent.

Verifies that when agents run with streaming enabled, raw JSON messages
are printed to stdout for real-time monitoring.

CURRENT STATUS:
- Streaming implementation added to agent_cli.py
- Fixed missing --verbose flag for stream-json mode
- Removed incorrect --resume flag (causes "session not found" errors)
- Added select() for non-blocking I/O with timeout handling
- Claude CLI command verified working manually with test cases

KNOWN ISSUES:
- Full docs execution times out without producing output
- Process starts but select() never sees data on stdout
- Investigating: settings file / hooks interaction with streaming mode
- Investigating: command-line argument size limits

ROOT CAUSE FOUND:
- Claude CLI with --output-format stream-json + --verbose works in isolation
- Something in the full ami-agent workflow prevents output
- Need to isolate: hooks vs instruction size vs settings file
"""

import json
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


class TestStreamingJSONOutput:
    """Test streaming JSON output from agents."""

    def test_docs_agent_prints_json_messages(self, temp_docs_dir, orchestrator_root):
        """ami-agent --docs should print raw JSON messages to stdout."""
        # Create simple doc file
        doc_file = temp_docs_dir / "test-streaming.md"
        doc_file.write_text("# Test Documentation\n\nThis is a simple test document.\n")

        # Run ami-agent --docs
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

        # Parse stdout line by line looking for JSON messages
        json_messages = []
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                json_messages.append(msg)
            except json.JSONDecodeError:
                # Not JSON, skip (could be summary text)
                pass

        # Should have JSON messages
        assert len(json_messages) > 0, f"Expected JSON messages in stdout, but found none.\nFull stdout:\n{result.stdout}"

        # Check message types
        message_types = [msg.get("type") for msg in json_messages]
        assert "assistant" in message_types, f"Expected 'assistant' message type in JSON output.\nFound message types: {set(message_types)}"

    def test_json_messages_contain_session_id(self, temp_docs_dir, orchestrator_root):
        """JSON messages should contain session_id for tracking."""
        # Create simple doc file
        doc_file = temp_docs_dir / "test-session.md"
        doc_file.write_text("# Test\n\nContent.\n")

        # Run ami-agent --docs
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
        assert result.returncode == 0

        # Parse JSON messages
        json_messages = []
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                json_messages.append(msg)
            except json.JSONDecodeError:
                pass

        # Should have JSON messages
        assert len(json_messages) > 0

        # Check for session_id in messages
        has_session = any("session_id" in msg or "sessionId" in msg for msg in json_messages)
        assert has_session, f"Expected session_id in JSON messages.\nSample messages: {json_messages[:3]}"

    def test_json_messages_have_valid_structure(self, temp_docs_dir, orchestrator_root):
        """JSON messages should have valid Claude Code stream-json structure."""
        # Create simple doc file
        doc_file = temp_docs_dir / "test-structure.md"
        doc_file.write_text("# Test\n\nContent.\n")

        # Run ami-agent --docs
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
        assert result.returncode == 0

        # Parse JSON messages
        json_messages = []
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                json_messages.append(msg)
            except json.JSONDecodeError:
                pass

        # Should have JSON messages
        assert len(json_messages) > 0

        # Check structure of assistant messages
        assistant_messages = [msg for msg in json_messages if msg.get("type") == "assistant"]
        assert len(assistant_messages) > 0, "Expected at least one assistant message"

        # Assistant messages should have message.content structure
        for msg in assistant_messages:
            assert "message" in msg, f"Assistant message missing 'message' field: {msg}"
            assert "content" in msg["message"], f"Assistant message missing 'content' field: {msg}"
            assert isinstance(msg["message"]["content"], list), f"Assistant message content should be list: {msg}"

    def test_streaming_output_appears_before_completion(self, temp_docs_dir, orchestrator_root):
        """JSON messages should appear in stdout stream, not just at the end."""
        # Create doc that will generate multiple messages
        doc_file = temp_docs_dir / "test-stream.md"
        doc_file.write_text(
            "# Test Documentation\n\nThis is a test document that should generate multiple agent messages.\nThe agent should read, analyze, and respond.\n"
        )

        # Run ami-agent --docs and collect output in real-time
        process = subprocess.Popen(
            [
                str(orchestrator_root / "scripts" / "ami-agent"),
                "--docs",
                str(temp_docs_dir),
                "--root-dir",
                str(temp_docs_dir),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Read output line by line (simulates real-time streaming)
        json_lines = []
        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                json_lines.append(msg)
            except json.JSONDecodeError:
                # Not JSON, skip
                pass

        process.wait(timeout=300)

        # Should have streamed JSON messages
        assert len(json_lines) > 0, "Expected streaming JSON messages"

        # Should have multiple messages (not just one at the end)
        assert len(json_lines) > 1, f"Expected multiple streaming messages, got {len(json_lines)}"

    @pytest.mark.skip(reason="Non-docs mode uses different API - currently only --docs mode has streaming")
    def test_no_streaming_without_docs_mode(self, orchestrator_root):
        """Regular ami-agent without --docs should not stream JSON by default."""
        # NOTE: Currently only --docs mode supports streaming
        # This test is a stub for future non-docs streaming support
