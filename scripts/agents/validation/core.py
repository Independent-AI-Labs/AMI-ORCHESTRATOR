"""Core validation infrastructure and base classes.

Contains the fundamental data structures and base classes needed for validation.
"""

import json
from typing import Any, Literal

# Import HookInput from workflows core since it's used in validation


class HookResult:
    """Hook output (to Claude Code)."""

    def __init__(
        self,
        decision: Literal["allow", "deny", "block"] | None = None,
        reason: str | None = None,
        system_message: str | None = None,
        event_type: Literal["PreToolUse", "Stop", "SubagentStop"] | None = None,
    ):
        self.decision = decision
        self.reason = reason
        self.system_message = system_message
        self.event_type = event_type

    def _to_json_pre_tool_use(self) -> str:
        """Convert PreToolUse hook result to JSON format.

        Returns:
            JSON string for PreToolUse hook
        """
        # PreToolUse hooks require hookSpecificOutput format
        if self.decision == "allow":
            permission_decision = "allow"
        elif self.decision == "deny":
            permission_decision = "deny"
        else:
            permission_decision = "allow"  # Default to allow

        output: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": permission_decision,
            }
        }

        if self.reason:
            output["hookSpecificOutput"]["permissionDecisionReason"] = self.reason

        if self.system_message:
            output["systemMessage"] = self.system_message

        return json.dumps(output)

    def _to_json_stop_event(self) -> str:
        """Convert Stop/SubagentStop hook result to JSON format.

        Returns:
            JSON string for Stop/SubagentStop hook
        """
        # Stop/SubagentStop hooks use decision/reason/systemMessage format
        # Note: Stop hooks use "approve"/"block" not "allow"/"deny"
        result: dict[str, Any] = {}
        if self.decision:
            # Map internal decision to Stop hook decision
            if self.decision == "allow":
                result["decision"] = "approve"
            elif self.decision == "block":
                result["decision"] = "block"
            else:
                result["decision"] = self.decision  # Pass through for other values
        if self.reason:
            result["reason"] = self.reason
        if self.system_message:
            result["systemMessage"] = self.system_message
        return json.dumps(result)

    def to_json(self) -> str:
        """Convert to JSON for Claude Code.

        PreToolUse hooks use hookSpecificOutput format.
        Stop/SubagentStop hooks use decision/reason format.

        Returns:
            JSON string
        """
        if self.event_type == "PreToolUse":
            return self._to_json_pre_tool_use()
        return self._to_json_stop_event()

    @classmethod
    def allow(cls) -> "HookResult":
        """Allow operation.

        Returns:
            Allow result
        """
        return cls()

    @classmethod
    def deny(cls, reason: str, system_message: str | None = None) -> "HookResult":
        """Deny operation (PreToolUse).

        Args:
            reason: Denial reason
            system_message: Optional UI message to display to user

        Returns:
            Deny result
        """
        return cls(decision="deny", reason=reason, system_message=system_message)

    @classmethod
    def block(cls, reason: str) -> "HookResult":
        """Block stop (Stop hooks).

        Args:
            reason: Block reason

        Returns:
            Block result
        """
        return cls(decision="block", reason=reason)
