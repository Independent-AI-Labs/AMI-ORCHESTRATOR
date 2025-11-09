"""Hook execution framework.

Ref: https://docs.claude.com/en/docs/claude-code/hooks.md
"""

import difflib
import json
import re
import signal
import sys
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

import tiktoken

from scripts.automation.agent_cli import AgentConfigPresets, AgentError, AgentExecutionError, AgentTimeoutError, get_agent_cli
from scripts.automation.config import get_config
from scripts.automation.logger import get_logger
from scripts.automation.transcript import format_messages_for_prompt, get_last_n_messages, is_actual_user_message
from scripts.automation.validators import (
    load_bash_patterns,
    load_exemptions,
    parse_code_fence_output,
    run_moderator_with_retry,
    validate_diff_llm,
)

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
        logger = get_logger("hooks")
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
        logger = get_logger("hooks")
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


@dataclass
class HookInput:
    """Hook input data (from Claude Code)."""

    session_id: str
    hook_event_name: str
    tool_name: str | None
    tool_input: dict[str, Any] | None
    transcript_path: Path | None

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


@dataclass
class HookResult:
    """Hook output (to Claude Code)."""

    decision: Literal["allow", "deny", "block"] | None = None
    reason: str | None = None
    system_message: str | None = None
    event_type: Literal["PreToolUse", "Stop", "SubagentStop"] | None = None

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
        self.logger = get_logger("hooks", session_id=session_id)

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

            # Reinitialize logger with session_id for per-session log files
            if hook_input.session_id and not self.session_id:
                self.session_id = hook_input.session_id
                self.logger = get_logger("hooks", session_id=hook_input.session_id)

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
            self.logger.error("invalid_hook_input", error=str(e))
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
            error_log_args: dict[str, Any] = {"error": str(e)}
            if hook_input:
                error_log_args["session_id"] = hook_input.session_id
            self.logger.error("hook_error", **error_log_args)
            # Fail closed - ZERO TOLERANCE
            # Default to block for any hook execution failure
            event_type = hook_input.hook_event_name if hook_input else "Stop"
            result = HookResult(
                decision="block" if event_type in ("Stop", "SubagentStop") else "deny",
                reason=f"Hook execution failed: {e}",
                event_type=cast(Literal["PreToolUse", "Stop", "SubagentStop"], event_type),
            )
            sys.stdout.write(result.to_json() + "\n")
            sys.stdout.flush()
            return 0


class MaliciousBehaviorValidator(HookValidator):
    """Validates Write/Edit/Bash tool usage for malicious bypass attempts.

    This validator runs FIRST before all other checks to catch attempts to:
    - Bypass CI/CD, hooks, or quality checks via script creation
    - Circumvent guardrails through file modification scripts
    - Create backdoors via /tmp or other temp locations
    - Automate git operations to skip validation
    """

    def __init__(self, session_id: str | None = None) -> None:
        """Initialize malicious behavior validator."""
        super().__init__(session_id)
        self.prompt_path = self.config.root / "scripts" / "config" / "prompts" / "malicious_behavior_moderator.txt"

    def _should_skip_validation(self, hook_input: HookInput) -> tuple[bool, HookResult | None]:
        """Check if validation should be skipped early.

        Args:
            hook_input: Hook input containing tool information

        Returns:
            Tuple of (should_skip, result_if_skipped)
        """
        # Only validate Write, Edit, and Bash tools
        if hook_input.tool_name not in ("Write", "Edit", "Bash"):
            return True, HookResult.allow()

        # Skip if no transcript available
        if not hook_input.transcript_path or not hook_input.transcript_path.exists():
            return True, HookResult.allow()

        return False, None

    def _get_conversation_context(self, hook_input: HookInput) -> tuple[str | None, str | None]:
        """Get conversation context from transcript.

        Args:
            hook_input: Hook input containing transcript path

        Returns:
            Tuple of (context, error_message)
        """
        try:
            if hook_input.transcript_path is None:
                return None, "transcript_path_missing"
            context = prepare_moderator_context(hook_input.transcript_path)
            return context, None
        except Exception as e:
            self.logger.error("malicious_behavior_context_error", session_id=hook_input.session_id, error=str(e))
            return None, "context_error"

    def _execute_malicious_behavior_check(self, hook_input: HookInput, conversation_context: str) -> HookResult:
        """Execute the malicious behavior check and parse result.

        Args:
            hook_input: Hook input containing tool information
            conversation_context: Conversation context for moderator

        Returns:
            HookResult with decision and optional reason
        """
        # Load prompt template
        if not self.prompt_path.exists():
            self.logger.error("malicious_behavior_prompt_missing", session_id=hook_input.session_id, path=str(self.prompt_path))
            return HookResult.allow()

        prompt_template = self.prompt_path.read_text()
        prompt = prompt_template.replace("{conversation_context}", conversation_context)

        # Execute moderator
        session_id = hook_input.session_id or "unknown"
        execution_id = str(uuid.uuid4())[:8]

        self.logger.info("malicious_behavior_moderator_start", session_id=session_id, execution_id=execution_id, tool=hook_input.tool_name)

        agent_cli = get_agent_cli()
        malicious_behavior_config = AgentConfigPresets.completion_moderator(f"malicious-behavior-{session_id}")
        malicious_behavior_config.enable_streaming = True

        # Create audit log for hang detection
        config = get_config()
        audit_dir = config.root / "logs" / "agent-cli"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_log_path = audit_dir / f"malicious-behavior-{execution_id}.log"

        output, _ = run_moderator_with_retry(
            cli=agent_cli,
            instruction_file=self.prompt_path,
            stdin=prompt,
            agent_config=malicious_behavior_config,
            audit_log_path=audit_log_path,
            moderator_name="malicious_behavior",
            session_id=session_id,
            execution_id=execution_id,
            max_attempts=2,
            first_output_timeout=3.5,
        )

        self.logger.info("malicious_behavior_moderator_output", session_id=session_id, execution_id=execution_id, output=output)

        # Parse decision - simple ALLOW or BLOCK: format
        # Strip preamble before decision marker for robustness
        cleaned_output = parse_code_fence_output(output)

        # Find first occurrence of ALLOW or BLOCK: (ignores preamble)
        allow_match = re.search(r"\bALLOW\b", cleaned_output, re.IGNORECASE)
        block_match = re.search(r"\bBLOCK:\s*", cleaned_output, re.IGNORECASE)

        if allow_match and (not block_match or allow_match.start() < block_match.start()):
            # ALLOW appears before BLOCK (or no BLOCK)
            self.logger.info("malicious_behavior_allow", session_id=session_id, execution_id=execution_id)
            return HookResult.allow()

        if block_match:
            # Extract reason after BLOCK:
            reason_start = block_match.end()
            reason = cleaned_output[reason_start:].strip()
            if not reason:
                reason = "Malicious behavior detected"
            self.logger.warning("malicious_behavior_block", session_id=session_id, execution_id=execution_id, reason=reason[:200])
            return HookResult.deny(
                reason=f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: PreToolUse ({hook_input.tool_name})\n"
                f"Validator: MaliciousBehaviorValidator\n\n"
                f"🚨 MALICIOUS BEHAVIOR DETECTED\n\n{reason}\n\n"
                f"This operation has been blocked to protect CI/CD integrity.",
                system_message="🚫 Malicious behavior detected - operation blocked",
            )

        # Unparseable output - fail closed for safety
        self.logger.warning("malicious_behavior_unparseable", session_id=session_id, execution_id=execution_id, output=cleaned_output[:300])
        return HookResult.deny(
            reason=f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            f"Hook: PreToolUse ({hook_input.tool_name})\n"
            f"Validator: MaliciousBehaviorValidator (Unparseable)\n\n"
            f"Malicious behavior check returned unparseable response. Blocking for safety.\n\n"
            f"This is likely a temporary issue - please try again.",
            system_message="⚠️ Security check failed - moderator error",
        )

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate tool usage for malicious bypass attempts.

        Args:
            hook_input: Hook input containing tool information

        Returns:
            HookResult with decision (allow/deny) and optional reason
        """
        # Check if validation should be skipped early
        should_skip, skip_result = self._should_skip_validation(hook_input)
        if should_skip:
            return skip_result if skip_result is not None else HookResult.allow()

        # Get conversation context
        context, error = self._get_conversation_context(hook_input)
        if error == "context_error":
            # Fail open for context errors (not the tool usage itself)
            return HookResult.allow()
        if context is None:
            # This shouldn't happen, but just in case
            return HookResult.allow()

        # Execute malicious behavior check with exception handling
        try:
            return self._execute_malicious_behavior_check(hook_input, context)
        except (AgentTimeoutError, AgentExecutionError) as e:
            session_id = hook_input.session_id or "unknown"
            execution_id = str(uuid.uuid4())[:8]

            self.logger.error("malicious_behavior_moderator_error_fail_closed", session_id=session_id, execution_id=execution_id, error=str(e))
            # FAIL-CLOSED: Block on timeout/execution errors to prevent bypass
            return HookResult.deny(
                reason=f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: PreToolUse ({hook_input.tool_name})\n"
                f"Validator: MaliciousBehaviorValidator (Timeout)\n\n"
                f"Malicious behavior check timed out after retry. Blocking for safety.\n\n"
                f"Moderator error: {type(e).__name__}\n\n"
                f"Please retry the operation.",
                system_message="⚠️ Security check timeout - operation blocked",
            )
        except AgentError as e:
            session_id = hook_input.session_id or "unknown"
            execution_id = str(uuid.uuid4())[:8]

            self.logger.error("malicious_behavior_moderator_error_fail_closed", session_id=session_id, execution_id=execution_id, error=str(e))
            # FAIL-CLOSED: Block on other agent errors too
            return HookResult.deny(
                reason=f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: PreToolUse ({hook_input.tool_name})\n"
                f"Validator: MaliciousBehaviorValidator (Error)\n\n"
                f"Malicious behavior check failed. Blocking for safety.\n\n"
                f"Moderator error: {type(e).__name__}\n\n"
                f"Please retry the operation.",
                system_message="⚠️ Security check error - operation blocked",
            )


class CommandValidator(HookValidator):
    """Validates Bash commands using patterns from YAML configuration."""

    def _extract_strings(self, obj: Any) -> Iterator[str]:
        """Recursively extract all string values from nested structures."""
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for value in obj.values():
                yield from self._extract_strings(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from self._extract_strings(item)

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate bash command against patterns from bash_commands.yaml.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        if hook_input.tool_name != "Bash":
            return HookResult.allow()

        # Handle null tool_input
        if hook_input.tool_input is None:
            return HookResult.allow()

        # Load patterns from YAML
        deny_patterns = load_bash_patterns()

        # SECURITY: Only validate the command field, not description/metadata
        # Only "command" is passed to subprocess - description is logging metadata.
        # Checking all fields causes false positives when descriptions mention tools.
        # Malicious code MUST be in command field to execute - checking description adds
        # no security value since it's never passed to shell.
        command = hook_input.tool_input.get("command", "")

        for pattern_config in deny_patterns:
            pattern = pattern_config.get("pattern", "")
            message = pattern_config.get("message", "Pattern violation detected")

            if re.search(pattern, command):
                return HookResult.deny(
                    f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                    f"Hook: PreToolUse (Bash)\n"
                    f"Validator: CommandValidator\n\n"
                    f"{message}\n"
                    f"Pattern: {pattern}"
                )

        return HookResult.allow()


class CoreQualityValidator(HookValidator):
    """Validates code changes for cross-language quality patterns using LLM-based audit."""

    def _extract_old_new_code(self, hook_input: HookInput) -> tuple[str, str]:
        """Extract old and new code with FULL file context for proper validation.

        For Edit operations, reads the complete file and applies the transformation
        to provide full context to validators. This prevents false positives when
        validators need to check patterns like lazy imports that require knowing
        the complete file structure.

        Args:
            hook_input: Hook input containing file edits

        Returns:
            Tuple of (full_old_content, full_new_content) with complete file context
        """
        if hook_input.tool_input is None:
            return "", ""

        file_path = hook_input.tool_input.get("file_path", "")
        file_path_obj = Path(file_path)

        if hook_input.tool_name == "Edit":
            # Read FULL current file content for proper context
            if not file_path_obj.exists():
                return "", ""

            full_old_content = file_path_obj.read_text()
            old_string = hook_input.tool_input.get("old_string", "")
            new_string = hook_input.tool_input.get("new_string", "")

            # Apply edit to get FULL new content
            if old_string in full_old_content:
                full_new_content = full_old_content.replace(old_string, new_string, 1)
            else:
                # Edit will fail anyway, but return fragments so validator can see what was attempted
                return old_string, new_string

            return full_old_content, full_new_content

        # Write operation - already has full content
        old_content = file_path_obj.read_text() if file_path_obj.exists() else ""
        new_content = hook_input.tool_input.get("content", "")
        return old_content, new_content

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate code quality using cross-language patterns.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        # Early exit for invalid inputs
        if hook_input.tool_name not in ("Edit", "Write") or hook_input.tool_input is None:
            return HookResult.allow()

        # Extract file path
        file_path = hook_input.tool_input.get("file_path", "")

        # Extract old/new code
        old_code, new_code = self._extract_old_new_code(hook_input)

        # Load exemptions from YAML

        exemptions = load_exemptions()

        # Check if file is exempt from pattern checks
        # Support both endswith (extensions) and contains (path patterns)
        is_pattern_exempt = any(file_path.endswith(exempt) or exempt in file_path for exempt in exemptions)

        # Skip validation for exempt files
        if is_pattern_exempt:
            return HookResult.allow()

        # Use shared validation logic with patterns_core.txt
        is_valid, reason = validate_diff_llm(
            file_path=file_path,
            old_content=old_code,
            new_content=new_code,
            session_id=hook_input.session_id,
            patterns_file="patterns_core.txt",
        )

        if is_valid:
            return HookResult.allow()
        return HookResult.deny(
            f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            f"Hook: PreToolUse ({hook_input.tool_name})\n"
            f"Validator: CoreQualityValidator\n\n"
            f"{reason}"
        )


class PythonQualityValidator(HookValidator):
    """Validates Python code changes for Python-specific quality patterns using LLM-based audit."""

    def _extract_old_new_code(self, hook_input: HookInput) -> tuple[str, str]:
        """Extract old and new code with FULL file context for proper validation.

        For Edit operations, reads the complete file and applies the transformation
        to provide full context to validators. This prevents false positives when
        validators need to check patterns like lazy imports that require knowing
        the complete file structure.

        Args:
            hook_input: Hook input containing file edits

        Returns:
            Tuple of (full_old_content, full_new_content) with complete file context
        """
        if hook_input.tool_input is None:
            return "", ""

        file_path = hook_input.tool_input.get("file_path", "")
        file_path_obj = Path(file_path)

        if hook_input.tool_name == "Edit":
            # Read FULL current file content for proper context
            if not file_path_obj.exists():
                return "", ""

            full_old_content = file_path_obj.read_text()
            old_string = hook_input.tool_input.get("old_string", "")
            new_string = hook_input.tool_input.get("new_string", "")

            # Apply edit to get FULL new content
            if old_string in full_old_content:
                full_new_content = full_old_content.replace(old_string, new_string, 1)
            else:
                # Edit will fail anyway, but return fragments so validator can see what was attempted
                return old_string, new_string

            return full_old_content, full_new_content

        # Write operation - already has full content
        old_content = file_path_obj.read_text() if file_path_obj.exists() else ""
        new_content = hook_input.tool_input.get("content", "")
        return old_content, new_content

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate Python code quality using Python-specific patterns.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        # Early exit for non-Python edits or invalid inputs
        if hook_input.tool_name not in ("Edit", "Write") or hook_input.tool_input is None or not hook_input.tool_input.get("file_path", "").endswith(".py"):
            return HookResult.allow()

        # Extract file path
        file_path = hook_input.tool_input.get("file_path", "")

        # Extract old/new code
        old_code, new_code = self._extract_old_new_code(hook_input)

        # Load exemptions from YAML

        exemptions = load_exemptions()

        # Check if file is exempt from pattern checks
        # Support both endswith (extensions) and contains (path patterns)
        is_pattern_exempt = any(file_path.endswith(exempt) or exempt in file_path for exempt in exemptions)

        # Skip validation for exempt files
        if is_pattern_exempt:
            return HookResult.allow()

        # Use shared validation logic with patterns_python.txt
        is_valid, reason = validate_diff_llm(
            file_path=file_path,
            old_content=old_code,
            new_content=new_code,
            session_id=hook_input.session_id,
            patterns_file="patterns_python.txt",
        )

        if is_valid:
            return HookResult.allow()
        return HookResult.deny(
            f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            f"Hook: PreToolUse ({hook_input.tool_name})\n"
            f"Validator: PythonQualityValidator\n\n"
            f"{reason}"
        )


class ShebangValidator(HookValidator):
    """Validates Python file shebangs for security and correctness."""

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate shebangs in Python files.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        # Only check Python files on Edit/Write
        if hook_input.tool_name not in ("Edit", "Write") or hook_input.tool_input is None:
            return HookResult.allow()

        file_path_str = hook_input.tool_input.get("file_path", "")
        if not file_path_str.endswith(".py"):
            return HookResult.allow()

        file_path = Path(file_path_str)

        # Get new content
        if hook_input.tool_name == "Write":
            new_content = hook_input.tool_input.get("content", "")
        else:  # Edit
            # For edits, check if shebang is being modified
            old_string = hook_input.tool_input.get("old_string", "")
            new_string = hook_input.tool_input.get("new_string", "")

            # Only check if shebang lines are involved
            if not (old_string.startswith("#!") or new_string.startswith("#!")):
                return HookResult.allow()

            # Read current file and apply edit to get new content
            if file_path.exists():
                current = file_path.read_text()
                new_content = current.replace(old_string, new_string, 1)
            else:
                new_content = new_string

        # Check first 200 bytes for shebang
        first_lines = new_content[:200].encode()

        # Security patterns (fail immediately)
        security_issues = [
            (b"sudo", "Contains sudo (security risk)"),
            (b"/usr/bin/python", "System python path (out-of-sandbox)"),
            (b"/usr/local/bin/python", "System python path (out-of-sandbox)"),
        ]

        for pattern, description in security_issues:
            if pattern in first_lines:
                return HookResult.deny(
                    f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                    f"Hook: PreToolUse ({hook_input.tool_name})\n"
                    f"Validator: ShebangValidator\n\n"
                    f"SECURITY: {description} in {file_path_str}"
                )

        # Incorrect patterns
        incorrect_patterns = [
            (b"#!/usr/bin/env python3", "Direct python3 shebang"),
            (b"#!/usr/bin/env python", "Direct python shebang"),
            (b"#!/usr/bin/python", "Direct python shebang"),
            (b'.venv/bin/python"', "Direct .venv python"),
        ]

        for pattern, description in incorrect_patterns:
            if pattern in first_lines and b"ami-run.sh" not in first_lines:
                return HookResult.deny(
                    f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                    f"Hook: PreToolUse ({hook_input.tool_name})\n"
                    f"Validator: ShebangValidator\n\n"
                    f"Shebang issue: {description} in {file_path_str}. Use ami-run wrapper instead."
                )

        return HookResult.allow()


class ResponseScanner(HookValidator):
    """Scans responses for communication violations and completion markers."""

    PROHIBITED_PATTERNS = [
        (r"\byou'?re\s+(absolutely|completely|totally|entirely|definitely)?\s*(correct|right|spot-on)\b", "you're right variations"),
        (r"\byou\s+are\s+(absolutely|completely|totally|entirely|definitely)?\s*(correct|right|spot-on)\b", "you are right variations"),
        (r"\b(absolutely|completely|totally|entirely|definitely)\s+(correct|right|spot-on)\b", "absolutely correct/right"),
        (r"\bthe\s+issue\s+is\s+clear\b", "the issue is clear"),
        (r"\bi\s+see\s+the\s+(problem|issue)\b", "I see the problem"),
        (r"\bthat'?s\s+(absolutely|completely|totally|exactly)\s+(correct|right|spot-on)\b", "that's absolutely correct/right"),
        (r"\bspot-on\b", "spot-on"),
        (r"\bpre-existing\b", "pre-existing (avoidance)"),
        (r"\bpre\s+existing\b", "pre existing (avoidance)"),
        (r"\balready\s+exists?\b", "already exists (avoidance)"),
        (r"\bexisting\s+(issue|problem|violation|bug|error)s?\b", "existing issues (avoidance)"),
    ]

    COMPLETION_MARKERS = ["WORK DONE", "FEEDBACK:"]

    def _is_greeting_exchange(self, transcript_path: Path, last_assistant_message: str) -> bool:
        """Check if conversation is just a greeting/initialization with no work requested.

        Args:
            transcript_path: Path to transcript file
            last_assistant_message: Last assistant message text

        Returns:
            True if this is a greeting exchange, False if work was requested
        """
        try:
            lines = transcript_path.read_text(encoding="utf-8").splitlines()

            # Count actual user messages (not tool results or hook feedback)
            actual_user_count = 0
            for line in lines:
                if is_actual_user_message(line):
                    actual_user_count += 1

            # Greeting exchange criteria:
            # 1. Very few user messages (≤1)
            # 2. AND last assistant message is asking for work (contains greeting patterns)
            if actual_user_count <= 1:
                greeting_patterns = [
                    r"what would you like",
                    r"what can I help",
                    r"ready to assist",
                    r"ready to help",
                    r"how can I help",
                    r"what do you need",
                    r"waiting for.*task",
                    r"awaiting.*task",
                ]
                for pattern in greeting_patterns:
                    if re.search(pattern, last_assistant_message, re.IGNORECASE):
                        return True

            return False

        except Exception as e:
            self.logger.warning("greeting_check_error", error=str(e))
            # On error, assume not a greeting (safer to require completion markers)
            return False

    def _check_early_allow_conditions(self, hook_input: HookInput) -> tuple[bool, HookResult | None]:
        """Check if validation should allow early based on transcript path conditions.

        Args:
            hook_input: Hook input

        Returns:
            Tuple of (should_allow_early, result_if_allowed)
        """
        # Early allow conditions
        if not hook_input.transcript_path:
            return True, HookResult.allow()

        transcript_path = hook_input.transcript_path
        if not transcript_path.exists():
            return True, HookResult.allow()

        last_message = self._get_last_assistant_message(transcript_path)
        if not last_message or self._is_greeting_exchange(transcript_path, last_message):
            return True, HookResult.allow()

        return False, None

    def _check_prohibited_patterns(self, last_message: str) -> HookResult | None:
        """Check if the message contains prohibited patterns.

        Args:
            last_message: The last assistant message

        Returns:
            HookResult if prohibited pattern found, None otherwise
        """
        # Apply communication rules
        for pattern, description in self.PROHIBITED_PATTERNS:
            if re.search(pattern, last_message, re.IGNORECASE):
                return HookResult.block(
                    f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                    f"Hook: Stop\n"
                    f"Validator: ResponseScanner\n\n"
                    f'CRITICAL COMMUNICATION RULES VIOLATION: "{description}" detected.\n\n'
                    '- NEVER say "The issue is clear", "You are right", "I see the problem", '
                    "or similar definitive statements without FIRST reading and verifying the actual source code/data.\n"
                    "- ALWAYS scrutinize everything. NEVER assume. ALWAYS check before making claims.\n"
                    "- If you don't know something or haven't verified it, say so explicitly.\n\n"
                    "Verify the source code/data before making claims."
                )
        return None

    def _check_api_limit_messages(self, last_message: str) -> tuple[bool, HookResult | None]:
        """Check if message contains API limit messages that should be allowed.

        Args:
            last_message: The last assistant message

        Returns:
            Tuple of (is_api_limit_message, result_if_api_limit)
        """
        # Check for API limit messages - allow without completion marker
        limit_patterns = [
            r"weekly\s+limit\s+reached",
            r"rate\s+limit\s+exceeded",
            r"quota\s+exceeded",
            r"usage\s+limit\s+reached",
        ]
        for pattern in limit_patterns:
            if re.search(pattern, last_message, re.IGNORECASE):
                return True, HookResult.allow()
        return False, None

    def validate(self, hook_input: HookInput) -> HookResult:
        """Scan last assistant message.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        # Check early allow conditions
        should_allow, early_result = self._check_early_allow_conditions(hook_input)
        if should_allow:
            return early_result if early_result is not None else HookResult.allow()

        transcript_path = hook_input.transcript_path
        last_message = self._get_last_assistant_message(transcript_path) if transcript_path is not None else ""

        # Check for completion markers FIRST
        has_completion_marker = any(marker in last_message for marker in self.COMPLETION_MARKERS)

        if has_completion_marker and transcript_path is not None:
            # Completion marker found - let moderator validate everything
            return self._validate_completion(hook_input.session_id, transcript_path, last_message)
        if has_completion_marker:
            # transcript_path is None, allow the completion to proceed
            return HookResult.allow()

        # Check for prohibited patterns
        prohibited_result = self._check_prohibited_patterns(last_message)
        if prohibited_result:
            return prohibited_result

        # Check for API limit messages
        is_api_limit, api_limit_result = self._check_api_limit_messages(last_message)
        if is_api_limit:
            return api_limit_result if api_limit_result is not None else HookResult.allow()

        # No completion markers found, block stop
        return HookResult.block(
            "🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            "Hook: Stop\n"
            "Validator: ResponseScanner\n\n"
            "COMPLETION MARKER REQUIRED.\n\n"
            "You must signal completion before stopping:\n"
            "- Add 'WORK DONE' when task is complete\n"
            "- Add 'FEEDBACK: <reason>' if blocked or need user input\n\n"
            "Never stop without explicitly signaling completion status."
        )

    def _parse_moderator_decision(self, session_id: str, output: str) -> HookResult:
        """Parse moderator output for ALLOW/BLOCK decision.

        Args:
            session_id: Session ID for logging
            output: Raw moderator output

        Returns:
            HookResult based on moderator decision
        """
        cleaned_output = parse_code_fence_output(output)

        # Check for conversational phrases that indicate prompt violation
        conversational_phrases = [
            r"I see\s+(?:the|that)",
            r"Let me\s+(?:check|now|run|see|verify)",
            r"I need to\s+",
            r"I was\s+",
            r"I'm\s+(?:confused|going)",
            r"I've\s+(?:successfully|completed)",
            r"Could you\s+",
            r"Should I\s+",
        ]

        for phrase_pattern in conversational_phrases:
            if re.search(phrase_pattern, cleaned_output, re.IGNORECASE):
                self.logger.warning("completion_moderator_conversational", session_id=session_id, phrase=phrase_pattern, output_preview=cleaned_output[:200])
                return HookResult.block(
                    f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                    f"Hook: Stop\n"
                    f"Validator: ResponseScanner\n\n"
                    f"COMPLETION VALIDATION ERROR\n\n"
                    f"Moderator returned conversational text instead of structured decision.\n"
                    f"This indicates a prompt following failure.\n\n"
                    f"Output preview: {cleaned_output[:300]}\n\n"
                    f"Defaulting to BLOCK for safety."
                )

        # Check for ALLOW: format (with explanation) - NEW FORMAT
        allow_with_reason_match = re.search(r"\bALLOW:\s*(.+)", cleaned_output, re.IGNORECASE | re.DOTALL)
        # Check for legacy bare ALLOW format - BACKWARDS COMPATIBILITY
        allow_bare_match = re.search(r"\bALLOW\b(?!:)", cleaned_output, re.IGNORECASE)
        # Check for BLOCK: format
        block_match = re.search(r"\bBLOCK:\s*", cleaned_output, re.IGNORECASE)

        if allow_with_reason_match:
            # New format: ALLOW: explanation
            explanation = allow_with_reason_match.group(1).strip()
            # Truncate at BLOCK if present (shouldn't happen but be safe)
            if "BLOCK" in explanation.upper():
                explanation = explanation[: explanation.upper().index("BLOCK")].strip()

            system_message = f"✅ MODERATOR: {explanation}"
            self.logger.info("completion_moderator_allow", session_id=session_id, explanation=explanation[:200])
            return HookResult(decision="allow", system_message=system_message)

        if allow_bare_match and (not block_match or allow_bare_match.start() < block_match.start()):
            # Legacy format: bare ALLOW (backwards compatibility)
            self.logger.warning(
                "completion_moderator_allow_no_explanation", session_id=session_id, note="Moderator used legacy ALLOW format without explanation"
            )
            system_message = "✅ MODERATOR: Completion validated (no explanation provided - legacy format)"
            return HookResult(decision="allow", system_message=system_message)

        if block_match:
            # Extract reason after BLOCK:
            reason_start = block_match.end()
            reason = cleaned_output[reason_start:].strip()
            if not reason:
                reason = "Work incomplete or validation failed"
            self.logger.info("completion_moderator_block", session_id=session_id, reason=reason[:200])
            return HookResult.block(
                f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: Stop\n"
                f"Validator: ResponseScanner\n\n"
                f"❌ MODERATOR: {reason}\n\n"
                f"Continue working or provide clarification."
            )

        # No clear decision - fail closed
        self.logger.warning("completion_moderator_unclear", session_id=session_id, output=cleaned_output[:500], raw_output=output[:500])
        return HookResult.block(
            f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            f"Hook: Stop\n"
            f"Validator: ResponseScanner\n\n"
            f"COMPLETION VALIDATION UNCLEAR\n\n"
            f"Moderator output (cleaned):\n{cleaned_output[:500]}\n\n"
            f"Expected 'ALLOW: explanation' or 'BLOCK: reason'. Defaulting to BLOCK for safety."
        )

    def _load_moderator_context(self, session_id: str, execution_id: str, transcript_path: Path) -> tuple[str | None, HookResult | None]:
        """Load and validate conversation context for moderator.

        Args:
            session_id: Session ID for logging
            execution_id: Unique execution ID for this moderator run
            transcript_path: Path to transcript file

        Returns:
            Tuple of (conversation_context, error_result). If error_result is not None, validation should return it.
        """
        try:
            # Load session todos to provide moderator with task context
            todos = load_session_todos(session_id)

            conversation_context = prepare_moderator_context(transcript_path, todos=todos)
            if not conversation_context:
                return None, HookResult.allow()

            token_count = count_tokens(conversation_context)
            context_preview_length = 500
            self.logger.info(
                "completion_moderator_input",
                session_id=session_id,
                execution_id=execution_id,
                transcript_path=str(transcript_path),
                context_size=len(conversation_context),
                token_count=token_count,
                context_preview=conversation_context[-context_preview_length:] if len(conversation_context) > context_preview_length else conversation_context,
            )
            return conversation_context, None
        except Exception as e:
            self.logger.error("completion_moderator_transcript_error", session_id=session_id, execution_id=execution_id, error=str(e))
            error_result = HookResult.block(
                f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: Stop\n"
                f"Validator: ResponseScanner\n\n"
                f"COMPLETION VALIDATION ERROR\n\nFailed to read conversation context: {e}\n\n"
                f"Cannot verify completion without context."
            )
            return None, error_result

    def _handle_moderator_error(self, session_id: str, execution_id: str, error: Exception) -> HookResult:
        """Handle moderator execution errors.

        Args:
            session_id: Session ID for logging
            execution_id: Unique execution ID
            error: Exception that occurred

        Returns:
            Block result with error details
        """
        if isinstance(error, AgentTimeoutError):
            self.logger.error(
                "completion_moderator_timeout",
                session_id=session_id,
                execution_id=execution_id,
                timeout_seconds=error.timeout,
                actual_duration=error.duration,
            )
            return HookResult.block(
                f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: Stop\n"
                f"Validator: ResponseScanner\n\n"
                f"❌ COMPLETION VALIDATION TIMEOUT\n\n"
                f"Moderator exceeded {error.timeout}s timeout while analyzing conversation.\n\n"
                f"This typically indicates:\n"
                f"1. Very large conversation context (>100K tokens)\n"
                f"2. API slowness/throttling\n"
                f"3. Network issues\n\n"
                f"Cannot verify completion due to timeout. Work remains unverified."
            )
        if isinstance(error, AgentExecutionError):
            self.logger.error(
                "completion_moderator_error",
                session_id=session_id,
                execution_id=execution_id,
                error=str(error),
                exit_code=error.exit_code,
                stdout_preview=error.stdout[:2000] if error.stdout else "",
                stderr=error.stderr[:2000] if error.stderr else "",
                cmd_preview=" ".join(error.cmd[:5]) if error.cmd else "",
            )
            stderr_preview = error.stderr[:500] if error.stderr else "No stderr output"
            return HookResult.block(
                f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: Stop\n"
                f"Validator: ResponseScanner\n\n"
                f"❌ COMPLETION VALIDATION ERROR\n\n"
                f"Agent execution failed with exit code {error.exit_code}\n\n"
                f"Error output:\n{stderr_preview}\n\n"
                f"Cannot verify completion due to moderator failure."
            )
        if isinstance(error, AgentError):
            self.logger.error("completion_moderator_error", session_id=session_id, execution_id=execution_id, error=str(error))
            return HookResult.block(
                f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: Stop\n"
                f"Validator: ResponseScanner\n\n"
                f"❌ COMPLETION VALIDATION ERROR\n\n{error}\n\n"
                f"Cannot verify completion due to moderator failure."
            )
        self.logger.error("completion_moderator_error", session_id=session_id, execution_id=execution_id, error=str(error))
        raise error

    def _check_completion_preconditions(self, session_id: str, transcript_path: Path, last_message: str) -> tuple[bool, HookResult | str | None]:
        """Check preconditions for completion validation.

        Args:
            session_id: Session ID for logging
            transcript_path: Path to transcript file
            last_message: Last assistant message text

        Returns:
            Tuple of (should_continue, result). If should_continue is False, return the result.
            If should_continue is True, result is the conversation_context string.
        """
        execution_id = str(uuid.uuid4())[:8]

        if not self.config.get("response_scanner.completion_moderator_enabled", True):
            return False, HookResult.allow()

        # Check for incomplete todos - BLOCK immediately if found
        # BUT: Only check when "WORK DONE" is present (not for "FEEDBACK:" which reports blockers)
        if "WORK DONE" in last_message:
            todos = load_session_todos(session_id)
            if todos:
                incomplete = [t for t in todos if t.get("status") in ("pending", "in_progress")]
                if incomplete:
                    task_list = "\n".join([f"  - {t.get('content', 'Unknown task')}" for t in incomplete])
                    return False, HookResult.block(
                        f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                        f"Hook: Stop\n"
                        f"Validator: ResponseScanner\n\n"
                        f"INCOMPLETE TASKS\n\n"
                        f"The following tasks are not complete:\n\n{task_list}\n\n"
                        f"Complete all tasks before claiming WORK DONE."
                    )

        # Load conversation context
        conversation_context, error_result = self._load_moderator_context(session_id, execution_id, transcript_path)
        if error_result:
            return False, error_result

        if not conversation_context:
            return False, HookResult.block("Cannot validate completion - no conversation context")

        # Check moderator prompt exists
        prompts_dir = self.config.root / self.config.get("prompts.dir")
        moderator_prompt = prompts_dir / self.config.get("prompts.completion_moderator", "completion_moderator.txt")

        if not moderator_prompt.exists():
            self.logger.error("completion_moderator_prompt_missing", session_id=session_id, execution_id=execution_id, path=str(moderator_prompt))
            return False, HookResult.block(
                f"COMPLETION VALIDATION ERROR\n\nModerator prompt not found: {moderator_prompt}\n\nCannot validate completion without prompt."
            )

        return True, conversation_context

    def _run_completion_moderator(self, session_id: str, conversation_context: str, moderator_prompt: Path) -> HookResult:
        """Run the completion moderator and return its decision.

        Args:
            session_id: Session ID for logging
            conversation_context: Conversation context for the moderator
            moderator_prompt: Path to the moderator prompt file

        Returns:
            HookResult from the moderator decision
        """
        execution_id = str(uuid.uuid4())[:8]

        # Create audit log file for debugging/troubleshooting
        audit_dir = self.config.root / "logs" / "agent-cli"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_log_path = audit_dir / f"completion-moderator-{execution_id}.log"

        try:
            with audit_log_path.open("w") as f:
                f.write(f"=== MODERATOR EXECUTION {execution_id} ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Session: {session_id}\n")
                f.write(f"Context size: {len(conversation_context)} chars\n")
                f.write(f"Token count: {count_tokens(conversation_context)}\n\n")
                f.write("=== PROMPT ===\n")
                f.write(moderator_prompt.read_text())
                f.write("\n\n=== CONVERSATION CONTEXT ===\n")
                f.write(conversation_context)
                f.write("\n\n=== STREAMING OUTPUT ===\n")

            self.logger.info("completion_moderator_audit_log_created", session_id=session_id, execution_id=execution_id, path=str(audit_log_path))
        except OSError as e:
            self.logger.warning("completion_moderator_audit_log_failed", session_id=session_id, execution_id=execution_id, error=str(e))

        # Run moderator agent and parse decision
        # Timeout behavior:
        # - agent_cli has 100s timeout (AgentConfigPresets.completion_moderator)
        # - hooks.yaml has 120s timeout (framework level)
        # - If agent_cli times out first: AgentTimeoutError caught → fail-closed (BLOCK)
        # - If framework times out first: process killed → hook framework fails-open (ALLOW)
        # - Timeouts must be aligned to ensure fail-closed behavior (agent < framework)
        try:
            # Set up alarm for framework timeout detection
            # Framework timeout is 120s, set alarm at 115s to log before kill
            framework_timeout = 120
            warning_time = framework_timeout - 5

            def timeout_warning_handler(signum: int, frame: Any) -> None:  # noqa: ARG001
                """Log warning when approaching framework timeout."""
                # NOTE: signum and frame are required by signal module but unused in handler
                self.logger.error(
                    "completion_moderator_approaching_timeout",
                    session_id=session_id,
                    execution_id=execution_id,
                    warning_time=warning_time,
                    framework_timeout=framework_timeout,
                )

            signal.signal(signal.SIGALRM, timeout_warning_handler)
            signal.alarm(warning_time)

            cli = get_agent_cli()
            completion_moderator_config = AgentConfigPresets.completion_moderator(session_id)
            completion_moderator_config.enable_streaming = True

            start_time = time.time()
            self.logger.info("completion_moderator_starting", session_id=session_id, execution_id=execution_id)

            output, _ = run_moderator_with_retry(
                cli=cli,
                instruction_file=moderator_prompt,
                stdin=conversation_context,
                agent_config=completion_moderator_config,
                audit_log_path=audit_log_path,
                moderator_name="completion_moderator",
                session_id=session_id,
                execution_id=execution_id,
                max_attempts=2,  # Original + 1 restart
                first_output_timeout=3.5,  # Seconds to wait for first output
            )

            signal.alarm(0)  # Cancel alarm on success

            elapsed_time = time.time() - start_time
            self.logger.info(
                "completion_moderator_completed",
                session_id=session_id,
                execution_id=execution_id,
                elapsed_seconds=round(elapsed_time, 2),
            )

            slow_threshold_seconds = 60
            if elapsed_time > slow_threshold_seconds:
                self.logger.warning(
                    "completion_moderator_slow",
                    session_id=session_id,
                    execution_id=execution_id,
                    elapsed_seconds=round(elapsed_time, 2),
                    threshold_seconds=slow_threshold_seconds,
                )

            # Log both raw and cleaned output for debugging
            cleaned_output = parse_code_fence_output(output)
            self.logger.info(
                "completion_moderator_raw_output", session_id=session_id, execution_id=execution_id, raw_output=output, cleaned_output=cleaned_output
            )
            return self._parse_moderator_decision(session_id, output)
        except Exception as e:
            return self._handle_moderator_error(session_id, execution_id, e)

    def _validate_completion(self, session_id: str, transcript_path: Path, last_message: str) -> HookResult:
        """Validate completion marker using moderator agent.

        Args:
            session_id: Session ID for logging
            transcript_path: Path to transcript file
            last_message: Last assistant message text (to check which completion marker was used)

        Returns:
            Validation result (ALLOW if work complete, BLOCK if not)
        """
        should_continue, result = self._check_completion_preconditions(session_id, transcript_path, last_message)

        if not should_continue:
            return result if isinstance(result, HookResult) else HookResult.allow()

        # If we get here, should_continue is True and result should be the conversation_context string
        # But if result is None or HookResult (unexpected), we should handle it
        if not isinstance(result, str):
            return HookResult.allow()

        conversation_context = result

        # Check moderator prompt exists (this was already validated in _check_completion_preconditions, but we need the prompt)
        prompts_dir = self.config.root / self.config.get("prompts.dir")
        moderator_prompt = prompts_dir / self.config.get("prompts.completion_moderator", "completion_moderator.txt")

        return self._run_completion_moderator(session_id, conversation_context, moderator_prompt)

    def _get_last_assistant_message(self, transcript_path: Path) -> str:
        """Get last assistant message from transcript.

        Args:
            transcript_path: Path to transcript file

        Returns:
            Last assistant message text
        """
        last_text = ""
        for line in transcript_path.read_text().splitlines():
            try:
                msg = json.loads(line)
                if msg.get("type") == "assistant":
                    # Extract text content
                    for content in msg.get("message", {}).get("content", []):
                        if content.get("type") == "text":
                            last_text = content.get("text", "")
            except Exception as e:
                # Skip invalid lines
                self.logger.warning("transcript_parse_error", line=line[:100], error=str(e))
                continue
        return last_text


class ResearchValidator(HookValidator):
    """Validates that assistant performed adequate research before making code changes."""

    def __init__(self, session_id: str | None = None) -> None:
        """Initialize research validator hook."""
        super().__init__(session_id)
        self.prompt_path = self.config.root / "scripts" / "config" / "prompts" / "research_validator_moderator.txt"
        self.skip_threshold_lines = self.config.get("research_validator.skip_threshold_lines", 5)
        self.lookback_messages = self.config.get("research_validator.lookback_messages", 30)

    def _count_lines_changed(self, tool_name: str, tool_input: dict[str, Any]) -> int:
        """Count lines changed in Write/Edit/NotebookEdit operation.

        Args:
            tool_name: Name of tool (Write, Edit, NotebookEdit)
            tool_input: Tool input parameters

        Returns:
            Number of lines added/removed/modified
        """
        if tool_name == "Write":
            content = tool_input.get("content", "")
            return len(content.splitlines())
        if tool_name == "Edit":
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")
            old_lines = len(old_string.splitlines())
            new_lines = len(new_string.splitlines())
            # Return max to catch both additions and deletions
            return max(old_lines, new_lines)
        if tool_name == "NotebookEdit":
            new_source = tool_input.get("new_source", "")
            return len(new_source.splitlines())
        return 0

    def _extract_old_new_code(self, tool_name: str, tool_input: dict[str, Any]) -> tuple[str, str]:
        """Extract FULL old and new file content for proper validation.

        Similar to CoreQualityValidator._extract_old_new_code, provides complete
        file context to the moderator instead of just diffs.

        Args:
            tool_name: Name of tool (Write, Edit, NotebookEdit)
            tool_input: Tool input parameters

        Returns:
            Tuple of (full_old_content, full_new_content)
        """
        file_path = tool_input.get("file_path", "")
        file_path_obj = Path(file_path)

        if tool_name == "Edit":
            # Read FULL current file content
            if not file_path_obj.exists():
                return "", ""

            full_old_content = file_path_obj.read_text()
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")

            # Apply edit to get FULL new content
            if old_string in full_old_content:
                full_new_content = full_old_content.replace(old_string, new_string, 1)
            else:
                # Edit will fail - return fragments so validator can see what was attempted
                return old_string, new_string

            return full_old_content, full_new_content

        if tool_name == "Write":
            # Write operation - full content provided
            old_content = file_path_obj.read_text() if file_path_obj.exists() else ""
            new_content = tool_input.get("content", "")
            return old_content, new_content

        if tool_name == "NotebookEdit":
            # For notebooks, return cell source
            new_source = tool_input.get("new_source", "")
            return "", new_source

        return "", ""

    def _generate_write_info(self, tool_input: dict[str, Any]) -> str:
        """Generate info for Write tool operations.

        Args:
            tool_input: Tool input parameters

        Returns:
            String describing the Write operation
        """
        file_path = tool_input.get("file_path", "unknown")
        content = tool_input.get("content", "")
        lines = len(content.splitlines())
        return f"Writing {lines} lines to {file_path}"

    def _generate_edit_info(self, tool_input: dict[str, Any]) -> str:
        """Generate info for Edit tool operations.

        Args:
            tool_input: Tool input parameters

        Returns:
            String describing the Edit operation or error message
        """
        file_path = tool_input.get("file_path", "unknown")
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")

        # Try to read the file and check if old_string exists
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return f"ERROR: File {file_path} does not exist. Cannot verify Edit operation."

            current_content = file_path_obj.read_text()

            preview_length = 200  # Character limit for preview strings

            if old_string not in current_content:
                # String not found - this Edit will fail
                old_preview = old_string[:preview_length] + "..." if len(old_string) > preview_length else old_string
                return (
                    f"ERROR: Edit will FAIL. String to replace not found in {file_path}.\n\n"
                    f"String being searched for (first {preview_length} chars):\n{old_preview}\n\n"
                    f"This indicates assistant has not read the file or is using incorrect string match."
                )

            # Generate unified diff
            old_lines = current_content.splitlines(keepends=True)
            new_content = current_content.replace(old_string, new_string, 1)
            new_lines = new_content.splitlines(keepends=True)

            diff_lines = list(difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}", lineterm=""))
            diff_text = "\n".join(diff_lines)

            return f"Edit operation on {file_path}:\n\n{diff_text}"

        except Exception as e:
            return f"ERROR: Could not read {file_path} to verify Edit: {e}"

    def _generate_notebook_edit_info(self, tool_input: dict[str, Any]) -> str:
        """Generate info for NotebookEdit tool operations.

        Args:
            tool_input: Tool input parameters

        Returns:
            String describing the NotebookEdit operation
        """
        notebook_path = tool_input.get("notebook_path", "unknown")
        cell_id = tool_input.get("cell_id", "unknown")
        new_source = tool_input.get("new_source", "")
        lines = len(new_source.splitlines())
        return f"Editing notebook {notebook_path} cell {cell_id} ({lines} lines)"

    def _generate_change_info(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Generate diff or change description for moderator prompt.

        Args:
            tool_name: Name of tool (Write, Edit, NotebookEdit)
            tool_input: Tool input parameters

        Returns:
            String describing the change or diff, or error message if Edit string not found
        """
        if tool_name == "Write":
            return self._generate_write_info(tool_input)
        if tool_name == "Edit":
            return self._generate_edit_info(tool_input)
        if tool_name == "NotebookEdit":
            return self._generate_notebook_edit_info(tool_input)
        return "Unknown change type"

    def _should_skip_validation(self, hook_input: HookInput) -> tuple[bool, HookResult | None]:
        """Check if validation should be skipped based on input conditions.

        Args:
            hook_input: Hook input containing tool information

        Returns:
            Tuple of (should_skip, result_if_skipped)
        """
        # Only validate Write/Edit/NotebookEdit
        if hook_input.tool_name not in ("Write", "Edit", "NotebookEdit"):
            return True, HookResult.allow()

        # Skip if no tool input
        if not hook_input.tool_input:
            return True, HookResult.allow()

        # Count lines changed
        lines_changed = self._count_lines_changed(hook_input.tool_name or "unknown", hook_input.tool_input or {})

        # Skip if below threshold (trivial changes)
        if lines_changed < self.skip_threshold_lines:
            self.logger.info(
                "research_validator_skip_trivial",
                session_id=hook_input.session_id,
                tool_name=hook_input.tool_name,
                lines_changed=lines_changed,
                threshold=self.skip_threshold_lines,
            )
            return True, HookResult.allow()

        # Skip if no transcript available
        if not hook_input.transcript_path or not hook_input.transcript_path.exists():
            return True, HookResult.allow()

        return False, None

    def _get_conversation_context(self, hook_input: HookInput) -> tuple[str | None, HookResult | None]:
        """Get conversation context for the moderator.

        Args:
            hook_input: Hook input containing transcript path

        Returns:
            Tuple of (conversation_context, error_result)
        """
        try:
            # Get last N messages for research tool detection
            if hook_input.transcript_path is None:
                return "", HookResult.allow()
            messages = get_last_n_messages(hook_input.transcript_path, self.lookback_messages)
            conversation_context = format_messages_for_prompt(messages)
            return conversation_context, None
        except Exception as e:
            self.logger.error("research_validator_context_error", session_id=hook_input.session_id, error=str(e))
            # Fail open for context errors
            return None, HookResult.allow()

    def _execute_research_moderator(self, hook_input: HookInput, conversation_context: str) -> HookResult:
        """Execute the research validation moderator.

        Args:
            hook_input: Hook input containing tool information and content
            conversation_context: Conversation context for the moderator

        Returns:
            HookResult from the moderator decision
        """
        # Load prompt
        if not self.prompt_path.exists():
            self.logger.error("research_validator_prompt_missing", session_id=hook_input.session_id, path=str(self.prompt_path))
            return HookResult.allow()

        # Execute moderator
        session_id = hook_input.session_id or "unknown"
        execution_id = str(uuid.uuid4())[:8]

        self.logger.info(
            "research_validator_start",
            session_id=session_id,
            execution_id=execution_id,
            tool_name=hook_input.tool_name,
            lines_changed=self._count_lines_changed(hook_input.tool_name or "unknown", hook_input.tool_input or {}),
        )

        agent_cli = get_agent_cli()
        research_validator_config = AgentConfigPresets.completion_moderator(f"research-validator-{session_id}")
        research_validator_config.enable_streaming = True

        # Create audit log
        audit_dir = self.config.root / "logs" / "agent-cli"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_log_path = audit_dir / f"research-validator-{execution_id}.log"

        # Extract full file content for proper validation (like CoreQualityValidator)
        file_path = (hook_input.tool_input or {}).get("file_path", "unknown")
        old_code, new_code = self._extract_old_new_code(hook_input.tool_name or "unknown", hook_input.tool_input or {})

        # Format change info with full before/after file content
        change_info = f"""FILE: {file_path}

## OLD CODE
```
{old_code}
```

## NEW CODE
```
{new_code}
```
"""
        full_context = f"{conversation_context}\n\n---\n\n## CHANGE BEING MADE\n\n{change_info}\n"

        output, _ = run_moderator_with_retry(
            cli=agent_cli,
            instruction_file=self.prompt_path,
            stdin=full_context,
            agent_config=research_validator_config,
            audit_log_path=audit_log_path,
            moderator_name="research_validator",
            session_id=session_id,
            execution_id=execution_id,
            max_attempts=2,
            first_output_timeout=3.5,
        )

        self.logger.info("research_validator_output", session_id=session_id, execution_id=execution_id, output=output[:500])

        # Parse decision - simple ALLOW or BLOCK: format
        cleaned_output = parse_code_fence_output(output)

        # Find first occurrence of ALLOW or BLOCK: (ignores preamble)
        allow_match = re.search(r"\bALLOW:\s*", cleaned_output, re.IGNORECASE)
        block_match = re.search(r"\bBLOCK:\s*", cleaned_output, re.IGNORECASE)

        if allow_match and (not block_match or allow_match.start() < block_match.start()):
            # ALLOW appears before BLOCK (or no BLOCK)
            self.logger.info("research_validator_allow", session_id=session_id, execution_id=execution_id)
            return HookResult.allow()

        if block_match:
            # Extract reason after BLOCK:
            reason_start = block_match.end()
            reason = cleaned_output[reason_start:].strip()
            if not reason:
                reason = "Inadequate research before code changes. Read docs and existing code before implementing."

            self.logger.warning("research_validator_block", session_id=session_id, execution_id=execution_id, reason=reason[:200])

            file_path = (hook_input.tool_input or {}).get("file_path", "unknown file")
            return HookResult.deny(
                reason=f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: PreToolUse ({hook_input.tool_name})\n"
                f"Validator: ResearchValidator\n\n"
                f"RESEARCH VALIDATION FAILED\n\n{reason}\n\n"
                f"File: {file_path}\n"
                f"Lines changed: {self._count_lines_changed(hook_input.tool_name or 'unknown', hook_input.tool_input or {})}\n\n"
                f"Before making code changes:\n"
                f"- Read official documentation for external APIs/libraries\n"
                f"- Use Read/Grep/Glob to understand existing code patterns\n"
                f"- Verify claims with tools before implementing\n",
                system_message=f"⚠️ Research validation blocked: {reason[:100]}",
            )

        # No clear decision found - fail closed for safety
        self.logger.warning("research_validator_unclear", session_id=session_id, execution_id=execution_id, output=cleaned_output[:200])
        return HookResult.deny(
            reason=f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            f"Hook: PreToolUse ({hook_input.tool_name})\n"
            f"Validator: ResearchValidator\n\n"
            f"MODERATOR OUTPUT UNCLEAR\n\n"
            f"Moderator did not output clear ALLOW or BLOCK decision. Failing closed for safety.\n\n"
            f"Moderator output (first 500 chars):\n{cleaned_output[:500]}\n",
            system_message="⚠️ Research validation unclear - failed closed",
        )

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate research adequacy before code changes.

        Args:
            hook_input: Hook input containing Write/Edit/NotebookEdit data

        Returns:
            HookResult with decision (allow/deny)
        """
        # Check if validation should be skipped
        should_skip, skip_result = self._should_skip_validation(hook_input)
        if should_skip:
            return skip_result if skip_result is not None else HookResult.allow()

        # Get conversation context
        conversation_context, error_result = self._get_conversation_context(hook_input)
        if error_result:
            return error_result
        # If conversation_context is None, it should have been handled by error_result

        if conversation_context is None:
            return HookResult.allow()

        # Execute the research validation
        try:
            return self._execute_research_moderator(hook_input, conversation_context)
        except (AgentTimeoutError, AgentExecutionError, AgentError) as error:
            session_id = hook_input.session_id or "unknown"
            execution_id = str(uuid.uuid4())[:8]

            if isinstance(error, AgentTimeoutError):
                self.logger.error("research_validator_timeout", session_id=session_id, execution_id=execution_id)
            elif isinstance(error, AgentExecutionError):
                self.logger.error("research_validator_execution_error", session_id=session_id, execution_id=execution_id, exit_code=error.exit_code)
            else:  # AgentError
                self.logger.error("research_validator_error", session_id=session_id, execution_id=execution_id, error=str(error))

            # Fail open on all agent errors
            return HookResult.allow()


class TodoValidatorHook(HookValidator):
    """Validates TodoWrite operations - ensures work is actually complete before marking todos complete or editing todo content."""

    def __init__(self, session_id: str | None = None) -> None:
        """Initialize todo validator hook."""
        super().__init__(session_id)
        self.prompt_path = self.config.root / "scripts" / "config" / "prompts" / "todo_validator_moderator.txt"

    def _should_validate_todos(self, hook_input: HookInput) -> tuple[bool, HookResult | list[dict[str, Any]] | None]:
        """Check if todo validation should proceed.

        Args:
            hook_input: Hook input containing TodoWrite data

        Returns:
            Tuple of (should_validate, result_if_not_validate)
        """
        # Only validate TodoWrite
        if hook_input.tool_name != "TodoWrite":
            return False, HookResult.allow()

        # Skip if no transcript available
        if not hook_input.transcript_path or not hook_input.transcript_path.exists():
            return False, HookResult.allow()

        # Extract todos from tool_input
        if not hook_input.tool_input or "todos" not in hook_input.tool_input:
            return False, HookResult.allow()

        todos = hook_input.tool_input.get("todos", [])
        if not todos:
            return False, HookResult.allow()

        return True, todos

    def _analyze_todo_changes(self, todos: list[dict[str, Any]], hook_input: HookInput) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Analyze what todos have changed.

        Args:
            todos: Current todo list
            hook_input: Hook input containing session information

        Returns:
            Tuple of (completed_todos, edited_todos)
        """
        # Load previous todo state to detect changes
        previous_todos = load_session_todos(hook_input.session_id)

        # Find todos being marked as completed in this operation
        completed_todos = [t for t in todos if t.get("status") == "completed"]

        # Find todos with edited content (excluding newly added todos)
        edited_todos = []
        if previous_todos:
            # Create lookup by index position (todos are ordered lists)
            for i, new_todo in enumerate(todos):
                if i < len(previous_todos):
                    prev_todo = previous_todos[i]
                    new_content = new_todo.get("content", "")
                    prev_content = prev_todo.get("content", "")
                    # Check if content changed (not just status)
                    if new_content != prev_content:
                        edited_todos.append(new_todo)

        return completed_todos, edited_todos

    def _get_todo_conversation_context(self, hook_input: HookInput) -> tuple[str | None, HookResult | None]:
        """Get conversation context for todo validation.

        Args:
            hook_input: Hook input containing transcript path

        Returns:
            Tuple of (conversation_context, error_result)
        """
        try:
            if hook_input.transcript_path is None:
                return None, HookResult.allow()
            conversation_context = prepare_moderator_context(hook_input.transcript_path)
            return conversation_context, None
        except Exception as e:
            self.logger.error("todo_validator_context_error", session_id=hook_input.session_id, error=str(e))
            # Fail open for context errors
            return None, HookResult.allow()

    def _build_validation_prompt(self, conversation_context: str, completed_todos: list[dict[str, Any]], edited_todos: list[dict[str, Any]]) -> str | None:
        """Build the validation prompt.

        Args:
            conversation_context: The conversation context
            completed_todos: List of completed todos
            edited_todos: List of edited todos

        Returns:
            Prompt string or None if prompt file is missing
        """
        # Load prompt template
        if not self.prompt_path.exists():
            self.logger.error("todo_validator_prompt_missing")
            return None

        prompt_template = self.prompt_path.read_text()

        # Build todo list for validation (both completed and edited)
        validation_todos = []
        if completed_todos:
            validation_todos.append("## Todos marked as completed:")
            for t in completed_todos:
                validation_todos.append(f"- {t.get('content', 'Unknown task')}")
        if edited_todos:
            validation_todos.append("\n## Todos with edited content:")
            for t in edited_todos:
                validation_todos.append(f"- {t.get('content', 'Unknown task')}")

        todo_list = "\n".join(validation_todos)

        # Replace placeholders
        prompt = prompt_template.replace("{conversation_context}", conversation_context)
        return prompt.replace("{completed_todos}", todo_list)

    def _execute_todo_validation(self, hook_input: HookInput, prompt: str) -> HookResult:
        """Execute the todo validation and return result.

        Args:
            hook_input: Hook input containing session information
            prompt: Built prompt for the moderator

        Returns:
            HookResult from the validation
        """
        # Execute moderator
        session_id = hook_input.session_id or "unknown"
        execution_id = str(uuid.uuid4())[:8]

        # Get completed and edited counts (these are available from earlier steps)
        todos = (hook_input.tool_input or {}).get("todos", [])
        completed_todos = [t for t in todos if t.get("status") == "completed"]
        edited_todos: list[dict[str, Any]] = []  # We'd need to recalculate this in real context

        self.logger.info(
            "todo_validator_start", session_id=session_id, execution_id=execution_id, completed_count=len(completed_todos), edited_count=len(edited_todos)
        )

        agent_cli = get_agent_cli()
        todo_validator_config = AgentConfigPresets.completion_moderator(f"todo-validator-{session_id}")
        todo_validator_config.enable_streaming = True

        # Create audit log for hang detection
        config = get_config()
        audit_dir = config.root / "logs" / "agent-cli"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_log_path = audit_dir / f"todo-validator-{execution_id}.log"

        output, _ = run_moderator_with_retry(
            cli=agent_cli,
            instruction_file=self.prompt_path,
            stdin=prompt,
            agent_config=todo_validator_config,
            audit_log_path=audit_log_path,
            moderator_name="todo_validator",
            session_id=session_id,
            execution_id=execution_id,
            max_attempts=2,
            first_output_timeout=3.5,
        )

        self.logger.info("todo_validator_output", session_id=session_id, execution_id=execution_id, output=output)

        # Parse decision - simple ALLOW or BLOCK: format
        cleaned_output = parse_code_fence_output(output)

        # Find first occurrence of ALLOW or BLOCK: (ignores preamble)
        allow_match = re.search(r"\bALLOW\b", cleaned_output, re.IGNORECASE)
        block_match = re.search(r"\bBLOCK:\s*", cleaned_output, re.IGNORECASE)

        if allow_match and (not block_match or allow_match.start() < block_match.start()):
            # ALLOW appears before BLOCK (or no BLOCK)
            self.logger.info("todo_validator_allow", session_id=session_id, execution_id=execution_id)
            return HookResult.allow()

        if block_match:
            # Extract reason after BLOCK:
            reason_start = block_match.end()
            reason = cleaned_output[reason_start:].strip()
            if not reason:
                reason = "Todo changes do not reflect actual work done"
            self.logger.warning("todo_validator_block", session_id=session_id, execution_id=execution_id, reason=reason[:200])
            return HookResult.deny(
                reason=f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: PreToolUse (TodoWrite)\n"
                f"Validator: TodoValidatorHook\n\n"
                f"TODO VALIDATION FAILED\n\n{reason}\n\n"
                f"Do not mark todos complete or edit todo content until work is actually done.",
                system_message=f"⚠️ Todo validation blocked: {reason}",
            )

        # Unparseable output - fail closed for safety
        self.logger.warning("todo_validator_unparseable", session_id=session_id, execution_id=execution_id, output=cleaned_output[:300])
        return HookResult.deny(
            reason="🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            "Hook: PreToolUse (TodoWrite)\n"
            "Validator: TodoValidatorHook (Unparseable)\n\n"
            "Todo validation returned unparseable response. Blocking for safety.\n\n"
            "This is likely a temporary issue - please try again.",
            system_message="⚠️ Todo validation failed - moderator error",
        )

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate todo completion against conversation context.

        Args:
            hook_input: Hook input containing TodoWrite data

        Returns:
            HookResult with decision (allow/deny)
        """
        # Default result is to allow
        result = HookResult.allow()

        # Check if validation should proceed and handle early returns
        should_validate, result_or_todos = self._should_validate_todos(hook_input)

        # Handle early return conditions
        if not should_validate and (result_or_todos is None or isinstance(result_or_todos, HookResult)):
            early_result = result_or_todos if result_or_todos else HookResult.allow()
            result = early_result or HookResult.allow()
        elif isinstance(result_or_todos, list):
            # Process valid todos list
            todos = result_or_todos
            completed_todos, edited_todos = self._analyze_todo_changes(todos, hook_input)

            # Only proceed with validation if there are changes
            if completed_todos or edited_todos:
                conversation_context, error_result = self._get_todo_conversation_context(hook_input)

                # Handle error result
                if not error_result and conversation_context is not None:
                    prompt = self._build_validation_prompt(conversation_context, completed_todos, edited_todos)

                    if prompt is not None:
                        try:
                            result = self._execute_todo_validation(hook_input, prompt)
                        except (AgentTimeoutError, AgentExecutionError, AgentError) as e:
                            session_id = hook_input.session_id or "unknown"
                            execution_id = str(uuid.uuid4())[:8]
                            self.logger.error("todo_validator_error_fail_closed", session_id=session_id, execution_id=execution_id, error=str(e))
                            error_type = type(e).__name__
                            result = HookResult.deny(
                                reason=f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                                f"Hook: PreToolUse (TodoWrite)\n"
                                f"Validator: TodoValidatorHook ({error_type})\n\n"
                                f"Todo validation failed. Blocking for safety.\n\n"
                                f"Moderator error: {error_type}\n\n"
                                f"Please retry the operation.",
                                system_message="⚠️ Todo validation error - operation blocked",
                            )

        return result
