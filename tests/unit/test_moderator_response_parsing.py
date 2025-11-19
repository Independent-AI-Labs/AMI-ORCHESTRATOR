"""Unit tests for completion moderator response parsing.

Tests the _parse_moderator_decision method to verify:
1. New ALLOW: format with explanation is parsed correctly
2. Legacy bare ALLOW format is supported with warning
3. BLOCK: format shows full moderator reasoning
4. System messages propagate full moderator response
"""

from unittest.mock import Mock

import pytest

from scripts.agents.workflows.completion_validator import CompletionValidator


class TestModeratorResponseParsing:
    """Test parsing of moderator responses for new and legacy formats."""

    @pytest.fixture
    def validator(self):
        """Create CompletionValidator instance."""
        return CompletionValidator()

    def test_new_allow_format_with_explanation(self, validator):
        """Verify new ALLOW: format extracts and shows explanation."""
        output = "ALLOW: User requested fix auth bug. Assistant fixed auth/validator.py and added test. All verified."

        result = validator._parse_moderator_decision("test-session", output, Mock())

        assert result.decision == "allow"
        assert result.system_message == "✅ MODERATOR: User requested fix auth bug. Assistant fixed auth/validator.py and added test. All verified."

    def test_legacy_bare_allow_format_blocks_for_security(self, validator):
        """Verify legacy bare ALLOW format is blocked for security (no longer allowed)."""
        output = "ALLOW"

        result = validator._parse_moderator_decision("test-session", output, Mock())

        assert result.decision == "block"
        assert "BLOCKED: ALLOW without explanation" in result.reason

    def test_block_format_shows_full_reason(self, validator):
        """Verify BLOCK: format shows full moderator reasoning."""
        output = "BLOCK: 8 tasks pending from current request. FEEDBACK reports hook block for LSP violation which is code quality issue to fix."

        result = validator._parse_moderator_decision("test-session", output, Mock())

        assert result.decision == "block"
        assert "❌ MODERATOR: 8 tasks pending" in result.reason
        assert "LSP violation" in result.reason
        assert "code quality issue" in result.reason

    def test_allow_with_code_fence(self, validator):
        """Verify ALLOW: format works when wrapped in code fence."""
        output = """```
ALLOW: Task complete. User requested X, assistant delivered X with verification.
```"""

        result = validator._parse_moderator_decision("test-session", output, Mock())

        assert result.decision == "allow"
        assert "MODERATOR: Task complete" in result.system_message

    def test_block_with_code_fence(self, validator):
        """Verify BLOCK: format works when wrapped in code fence."""
        output = """```
BLOCK: Work incomplete. Only 2 of 3 tasks finished.
```"""

        result = validator._parse_moderator_decision("test-session", output, Mock())

        assert result.decision == "block"
        assert "❌ MODERATOR: Work incomplete" in result.reason

    def test_unclear_output_fails_closed(self, validator):
        """Verify unclear output defaults to BLOCK for safety."""
        output = "I'm not sure if this work is complete or not."

        result = validator._parse_moderator_decision("test-session", output, Mock())

        assert result.decision == "block"
        assert "UNCLEAR" in result.reason

    def test_pattern_e_block_message(self, validator):
        """Verify Pattern E block message format is parsed correctly."""
        output = """BLOCK: 8 phases pending from current request (user approved full 9-phase Multi-CLI plan). FEEDBACK reports hook block for LSP violation which is a code quality issue to fix by implementing Phase 1.2 and 1.3 together as assistant suggested. Continue working to complete all phases."""

        result = validator._parse_moderator_decision("test-session", output, Mock())

        assert result.decision == "block"
        assert "8 phases pending" in result.reason
        assert "LSP violation" in result.reason
        assert "code quality issue" in result.reason

    def test_allow_truncates_at_block(self, validator):
        """Verify ALLOW explanation is truncated if BLOCK appears (safety check)."""
        output = "ALLOW: Work is complete. BLOCK: Just kidding, it's not."

        result = validator._parse_moderator_decision("test-session", output, Mock())

        assert result.decision == "allow"
        assert "Work is complete" in result.system_message
        assert "Just kidding" not in result.system_message
