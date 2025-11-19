"""Core hook infrastructure and base classes.

Contains the fundamental data structures and base classes needed for hook validation.
"""

import json
import sys
from pathlib import Path
from typing import Any, Literal, cast

import tiktoken
from loguru import logger

from scripts.agents.config import get_config
from scripts.agents.transcript import format_messages_for_prompt, get_last_n_messages

# Resource limits (DoS protection)
MAX_HOOK_INPUT_SIZE = 10 * 1024 * 1024  # 10MB

# Token limits for moderator context
# Claude CLI has input size limits beyond model context window - stay conservative
MAX_MODERATOR_CONTEXT_TOKENS = 100_000  # Leave buffer for prompt + CLI input limits

# Message count limits - moderator gets confused with too many messages (>100)
# Even with token limit, high message count causes incorrect decisions
MAX_MODERATOR_MESSAGE_COUNT = 100  # Hard cap on message count

# Code fence parsing
MIN_CODE_FENCE_LINES = 2  # Minimum lines for valid code fence (opening + closing)


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken (GPT-4 tokenizer).

    Args:
        text: Text to count tokens for

    Returns:
        Token count

    Raises:
        Exception: If tokenization fails
    """
    encoding = tiktoken.encoding_for_model("gpt-4")
    return len(encoding.encode(text))


def load_session_todos(session_id: str) -> list[dict[str, Any]]:
    """Load todo list for a given session.

    Args:
        session_id: Claude Code session ID

    Returns:
        List of todo items, or empty list if file doesn't exist or can't be read
    """
    todo_file = Path.home() / ".claude" / "todos" / f"{session_id}-agent-{session_id}.json"

    try:
        if not todo_file.exists():
            return []

        with todo_file.open() as f:
            todos = json.load(f)

        # Validate it's a list
        if not isinstance(todos, list):
            return []

        return todos
    except Exception:
        # Fail gracefully if we can't read the todo file
        return []


def prepare_moderator_context(
    transcript_path: Path,
    todos: list[dict[str, Any]] | None = None,
) -> str:
    """Prepare conversation context for moderator with token and message count limits.

    Gets LAST N messages from transcript and applies:
    1. Hard cap at MAX_MODERATOR_MESSAGE_COUNT (100 messages)
    2. Binary search truncation to fit within MAX_MODERATOR_CONTEXT_TOKENS (100K tokens)

    Message count limit is CRITICAL - moderator gives incorrect decisions above 100 messages
    even when token count is within limits.

    This is the PRODUCTION function used by completion moderator hook.
    Tests MUST use this function to ensure they test production behavior.

    Args:
        transcript_path: Path to transcript JSONL file
        todos: Optional list of todo items to append to context
        background_tasks: Optional list of background tasks to append to context

    Returns:
        Formatted conversation context string ready for moderator

    Raises:
        Exception: If transcript extraction or formatting fails
    """

    # Count total messages first
    all_messages = get_last_n_messages(transcript_path, 99999)
    if not all_messages:
        return ""

    total_messages = len(all_messages)

    # CRITICAL: Apply message count hard cap FIRST (before token-based truncation)
    # Moderator gets confused with >100 messages and gives incorrect ALLOW decisions
    if total_messages > MAX_MODERATOR_MESSAGE_COUNT:
        all_messages = get_last_n_messages(transcript_path, MAX_MODERATOR_MESSAGE_COUNT)
        logger.warning(
            "moderator_message_count_capped",
            original_messages=total_messages,
            capped_messages=MAX_MODERATOR_MESSAGE_COUNT,
            reason="Moderator accuracy degrades above 100 messages",
        )
        total_messages = MAX_MODERATOR_MESSAGE_COUNT

    conversation_context = format_messages_for_prompt(all_messages)
    token_count = count_tokens(conversation_context)

    # If transcript is too large, use binary search to find how many messages fit
    if token_count > MAX_MODERATOR_CONTEXT_TOKENS:
        original_token_count = token_count

        # Binary search to find appropriate window size
        left_window = 1
        right_window = total_messages
        best_window = 1

        while left_window <= right_window:
            mid_window = (left_window + right_window) // 2
            test_messages = get_last_n_messages(transcript_path, mid_window)
            test_context = format_messages_for_prompt(test_messages)
            test_tokens = count_tokens(test_context)

            if test_tokens <= MAX_MODERATOR_CONTEXT_TOKENS:
                best_window = mid_window
                left_window = mid_window + 1
            else:
                right_window = mid_window - 1

        messages = get_last_n_messages(transcript_path, best_window)
        conversation_context = format_messages_for_prompt(messages)
        truncated_token_count = count_tokens(conversation_context)

        # Log warning about context truncation
        logger.warning(
            "moderator_context_truncated",
            original_messages=total_messages,
            truncated_messages=best_window,
            original_tokens=original_token_count,
            truncated_tokens=truncated_token_count,
            max_tokens=MAX_MODERATOR_CONTEXT_TOKENS,
        )

    # Append todo list if provided
    if todos:
        todo_section = "\n\n# Current Task List\n\n"
        for i, todo in enumerate(todos, 1):
            status = todo.get("status", "unknown")
            content = todo.get("content", "Unknown task")
            status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(status, "❓")
            todo_section += f"{i}. [{status_emoji} {status}] {content}\n"

        conversation_context += todo_section

    return conversation_context


class HookInput:
    """Hook input data (from Claude Code)."""

    def __init__(
        self,
        session_id: str,
        hook_event_name: str,
        tool_name: str | None,
        tool_input: dict[str, Any] | None,
        transcript_path: Path | None,
    ):
        self.session_id = session_id
        self.hook_event_name = hook_event_name
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.transcript_path = transcript_path

    @classmethod
    def from_stdin(cls) -> "HookInput":
        """Parse hook input from stdin.

        Returns:
            Parsed HookInput

        Raises:
            ValueError: If input too large
            json.JSONDecodeError: If input not valid JSON
        """
        # Read with size limit
        data_str = sys.stdin.read(MAX_HOOK_INPUT_SIZE + 1)

        if len(data_str) > MAX_HOOK_INPUT_SIZE:
            raise ValueError(f"Hook input too large (>{MAX_HOOK_INPUT_SIZE} bytes)")

        data = json.loads(data_str)
        return cls(
            session_id=data.get("session_id", ""),
            hook_event_name=data.get("hook_event_name", ""),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input"),
            transcript_path=Path(data["transcript_path"]) if data.get("transcript_path") else None,
        )


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


class HookValidator:
    """Base class for hook validators."""

    def __init__(self, session_id: str | None = None) -> None:
        """Initialize hook validator.

        Args:
            session_id: Optional session ID for per-session logging
        """
        self.config = get_config()
        self.session_id = session_id
        self.logger = logger

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate hook input. Override in subclasses.

        Args:
            hook_input: Input to validate

        Returns:
            Validation result
        """
        raise NotImplementedError

    def run(self) -> int:
        """Execute hook validation (CLI entry point).

        Returns:
            Exit code (0=success)
        """
        hook_input: HookInput | None = None
        try:
            hook_input = HookInput.from_stdin()

            # Log execution
            self.logger.info(
                "hook_execution",
                session_id=hook_input.session_id,
                hook_name=self.__class__.__name__,
                event=hook_input.hook_event_name,
                tool=hook_input.tool_name,
            )

            # Validate
            result = self.validate(hook_input)

            # Set event type for correct JSON format
            result.event_type = cast(Literal["PreToolUse", "Stop", "SubagentStop"], hook_input.hook_event_name)

            # Output result to stdout for Claude Code
            sys.stdout.write(result.to_json() + "\n")
            sys.stdout.flush()

            # Log result
            self.logger.info(
                "hook_result",
                session_id=hook_input.session_id,
                decision=result.decision or "allow",
                reason=result.reason,
            )

            return 0

        except json.JSONDecodeError as e:
            error_log_args: dict[str, Any] = {"error": str(e)}
            if hook_input:
                error_log_args["session_id"] = hook_input.session_id
            self.logger.error("invalid_hook_input", **error_log_args)
            # Fail closed - ZERO TOLERANCE
            result = HookResult(
                decision="block" if hook_input and hook_input.hook_event_name in ("Stop", "SubagentStop") else "deny",
                reason=f"Hook input parsing failed: {e}",
                event_type="Stop",  # Default to Stop format
            )
            sys.stdout.write(result.to_json() + "\n")
            sys.stdout.flush()
            return 0

        except Exception as e:
            error_log_args_general: dict[str, Any] = {"error": str(e)}
            if hook_input:
                error_log_args_general["session_id"] = hook_input.session_id
            self.logger.error("hook_error", **error_log_args_general)
            # Fail closed - ZERO TOLERANCE
            # Default to block for any hook execution failure to maintain security
            event_type = hook_input.hook_event_name if hook_input else "Stop"
            result = HookResult(
                decision="block" if event_type in ("Stop", "SubagentStop") else "deny",
                reason=f"Hook execution failed: {e}",
                event_type=cast(Literal["PreToolUse", "Stop", "SubagentStop"], event_type),
            )
            sys.stdout.write(result.to_json() + "\n")
            sys.stdout.flush()
            return 0
