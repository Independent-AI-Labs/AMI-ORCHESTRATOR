"""Unit tests for HookResult functionality."""

import json

# Import the implemented hooks functionality
from scripts.agents.workflows.core import HookResult


class TestHookResult:
    """Unit tests for HookResult."""

    def test_allow_result(self):
        """HookResult.allow() creates allow result."""
        result = HookResult.allow()

        assert result.decision is None or result.decision == "allow"
        json_output = result.to_json()
        # Empty JSON or minimal JSON for allow
        data = json.loads(json_output)
        assert data.get("decision") in (None, "allow")

    def test_deny_result(self):
        """HookResult.deny() creates deny result."""
        result = HookResult.deny("test reason")

        assert result.decision == "deny"
        assert result.reason == "test reason"

        json_output = result.to_json()
        data = json.loads(json_output)
        assert data["decision"] == "deny"
        assert data["reason"] == "test reason"

    def test_block_result(self):
        """HookResult.block() creates block result."""
        result = HookResult.block("block reason")

        assert result.decision == "block"
        assert result.reason == "block reason"

        json_output = result.to_json()
        data = json.loads(json_output)
        assert data["decision"] == "block"
        assert data["reason"] == "block reason"
