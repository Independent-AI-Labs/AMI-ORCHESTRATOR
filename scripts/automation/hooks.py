"""Hook execution framework.

Ref: https://docs.claude.com/en/docs/claude-code/hooks.md
"""

import json
import re
import sys
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import tiktoken

from scripts.automation.agent_cli import AgentConfigPresets, AgentError, AgentExecutionError, AgentTimeoutError, get_agent_cli
from scripts.automation.config import get_config
from scripts.automation.logger import get_logger
from scripts.automation.transcript import format_messages_for_prompt, get_last_n_messages, is_actual_user_message
from scripts.automation.validators import load_bash_patterns, load_exemptions, parse_code_fence_output, validate_python_full

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


def prepare_moderator_context(transcript_path: Path) -> str:
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

    def to_json(self) -> str:
        """Convert to JSON for Claude Code.

        PreToolUse hooks use hookSpecificOutput format.
        Stop/SubagentStop hooks use decision/reason format.

        Returns:
            JSON string
        """
        if self.event_type == "PreToolUse":
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

            return json.dumps(output)
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

    @classmethod
    def allow(cls) -> "HookResult":
        """Allow operation.

        Returns:
            Allow result
        """
        return cls()

    @classmethod
    def deny(cls, reason: str) -> "HookResult":
        """Deny operation (PreToolUse).

        Args:
            reason: Denial reason

        Returns:
            Deny result
        """
        return cls(decision="deny", reason=reason)

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

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate tool usage for malicious bypass attempts.

        Args:
            hook_input: Hook input containing tool information

        Returns:
            HookResult with decision (allow/deny) and optional reason
        """
        # Only validate Write, Edit, and Bash tools
        if hook_input.tool_name not in ("Write", "Edit", "Bash"):
            return HookResult.allow()

        # Skip if no transcript available
        if not hook_input.transcript_path or not hook_input.transcript_path.exists():
            return HookResult.allow()

        # Get conversation context
        try:
            conversation_context = prepare_moderator_context(hook_input.transcript_path)
        except Exception as e:
            self.logger.error("malicious_behavior_context_error", session_id=hook_input.session_id, error=str(e))
            # Fail open for context errors (not the tool usage itself)
            return HookResult.allow()

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

        try:
            agent_cli = get_agent_cli()
            malicious_behavior_config = AgentConfigPresets.completion_moderator(f"malicious-behavior-{session_id}")

            output, _ = agent_cli.run_print(
                instruction_file=self.prompt_path,
                stdin=prompt,
                agent_config=malicious_behavior_config,
            )

            self.logger.info("malicious_behavior_moderator_output", session_id=session_id, execution_id=execution_id, output=output)

            # Parse decision
            cleaned_output = parse_code_fence_output(output)
            xml_match = re.search(r"<decision>\s*(.+?)\s*</decision>", cleaned_output, re.IGNORECASE | re.DOTALL)

            if xml_match:
                decision_text = xml_match.group(1).strip()

                if re.match(r"^ALLOW$", decision_text, re.IGNORECASE):
                    self.logger.info("malicious_behavior_allow", session_id=session_id, execution_id=execution_id)
                    return HookResult.allow()

                if re.match(r"^BLOCK$", decision_text, re.IGNORECASE):
                    # Extract reason
                    reason_match = re.search(r"<reason>\s*(.+?)\s*</reason>", cleaned_output, re.IGNORECASE | re.DOTALL)
                    reason = reason_match.group(1).strip() if reason_match else "Malicious behavior detected"

                    self.logger.warning("malicious_behavior_block", session_id=session_id, execution_id=execution_id, reason=reason[:200])
                    return HookResult.deny(f"🚨 MALICIOUS BEHAVIOR DETECTED\n\n{reason}\n\nThis operation has been blocked to protect CI/CD integrity.")

            # Unparseable output - fail closed for safety
            self.logger.warning("malicious_behavior_unparseable", session_id=session_id, execution_id=execution_id, output=cleaned_output[:300])
            return HookResult.deny(
                "Malicious behavior check returned unparseable response. Blocking for safety.\n\nThis is likely a temporary issue - please try again."
            )

        except (AgentError, AgentTimeoutError, AgentExecutionError) as e:
            self.logger.error("malicious_behavior_moderator_error", session_id=session_id, execution_id=execution_id, error=str(e))
            # Fail open for moderator execution errors (not malicious behavior itself)
            return HookResult.allow()


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

        # Check all strings in tool_input (handles nested structures)
        all_strings = list(self._extract_strings(hook_input.tool_input))

        for pattern_config in deny_patterns:
            pattern = pattern_config.get("pattern", "")
            message = pattern_config.get("message", "Pattern violation detected")

            for string in all_strings:
                if re.search(pattern, string):
                    return HookResult.deny(f"{message} (pattern: {pattern})")

        return HookResult.allow()


class CodeQualityValidator(HookValidator):
    """Validates code changes for quality regressions using LLM-based audit."""

    def _extract_old_new_code(self, hook_input: HookInput) -> tuple[str, str]:
        """Extract old and new code from hook input.

        Args:
            hook_input: Hook input containing file edits

        Returns:
            Tuple of (old_code, new_code)
        """
        if hook_input.tool_input is None:
            return "", ""

        file_path = hook_input.tool_input.get("file_path", "")

        if hook_input.tool_name == "Edit":
            old_code = hook_input.tool_input.get("old_string", "")
            new_code = hook_input.tool_input.get("new_string", "")
        else:  # Write
            old_code = Path(file_path).read_text() if Path(file_path).exists() else ""
            new_code = hook_input.tool_input.get("content", "")

        return old_code, new_code

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate code quality using patterns and LLM diff audit.

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
        is_pattern_exempt = any(file_path.endswith(exempt) for exempt in exemptions)

        # Skip validation for exempt files
        if is_pattern_exempt:
            return HookResult.allow()

        # Use shared validation logic (eliminates duplication with files/backend validators)
        is_valid, reason = validate_python_full(
            file_path=file_path,
            old_content=old_code,
            new_content=new_code,
            session_id=hook_input.session_id,
        )

        if is_valid:
            return HookResult.allow()
        return HookResult.deny(reason)


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
                return HookResult.deny(f"SECURITY: {description} in {file_path_str}")

        # Incorrect patterns
        incorrect_patterns = [
            (b"#!/usr/bin/env python3", "Direct python3 shebang"),
            (b"#!/usr/bin/env python", "Direct python shebang"),
            (b"#!/usr/bin/python", "Direct python shebang"),
            (b'.venv/bin/python"', "Direct .venv python"),
        ]

        for pattern, description in incorrect_patterns:
            if pattern in first_lines and b"ami-run.sh" not in first_lines:
                return HookResult.deny(f"Shebang issue: {description} in {file_path_str}. Use ami-run wrapper instead.")

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

    def validate(self, hook_input: HookInput) -> HookResult:
        """Scan last assistant message.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        # Early allow conditions
        if not hook_input.transcript_path:
            return HookResult.allow()

        transcript_path = hook_input.transcript_path
        if not transcript_path.exists():
            return HookResult.allow()

        last_message = self._get_last_assistant_message(transcript_path)
        if not last_message or self._is_greeting_exchange(transcript_path, last_message):
            return HookResult.allow()

        # Check for completion markers FIRST
        has_completion_marker = any(marker in last_message for marker in self.COMPLETION_MARKERS)

        if has_completion_marker:
            # Completion marker found - let moderator validate everything
            return self._validate_completion(hook_input.session_id, transcript_path)

        # No completion markers - apply communication rules
        for pattern, description in self.PROHIBITED_PATTERNS:
            if re.search(pattern, last_message, re.IGNORECASE):
                return HookResult.block(
                    f'CRITICAL COMMUNICATION RULES VIOLATION: "{description}" detected.\n\n'
                    '- NEVER say "The issue is clear", "You are right", "I see the problem", '
                    "or similar definitive statements without FIRST reading and verifying the actual source code/data.\n"
                    "- ALWAYS scrutinize everything. NEVER assume. ALWAYS check before making claims.\n"
                    "- If you don't know something or haven't verified it, say so explicitly.\n\n"
                    "Verify the source code/data before making claims."
                )

        # No completion markers found, block stop
        return HookResult.block(
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
                    "COMPLETION VALIDATION ERROR\n\n"
                    "Moderator returned conversational text instead of structured decision.\n"
                    "This indicates a prompt following failure.\n\n"
                    f"Output preview: {cleaned_output[:300]}\n\n"
                    "Defaulting to BLOCK for safety."
                )

        # Try to extract XML decision tags (new format)
        xml_match = re.search(r"<decision>\s*(.+?)\s*</decision>", cleaned_output, re.IGNORECASE | re.DOTALL)
        if xml_match:
            decision_text = xml_match.group(1).strip()

            # Check if it's ALLOW
            if re.match(r"^ALLOW$", decision_text, re.IGNORECASE):
                self.logger.info("completion_moderator_allow", session_id=session_id, format="xml")
                return HookResult(decision="allow", system_message="✅ Completion validated - work meets requirements")

            # Check if it's BLOCK with reason
            block_xml_match = re.match(r"^BLOCK:\s*(.+)$", decision_text, re.IGNORECASE | re.DOTALL)
            if block_xml_match:
                reason = block_xml_match.group(1).strip()
                self.logger.info("completion_moderator_block", session_id=session_id, reason=reason[:100], format="xml")
                return HookResult.block(f"❌ COMPLETION VALIDATION FAILED\n\n{reason}\n\nWork is not complete. Continue working or provide clarification.")

        # Fallback: Check for plain ALLOW/BLOCK (backward compatibility)
        if re.search(r"\bALLOW\b", cleaned_output, re.IGNORECASE):
            self.logger.info("completion_moderator_allow", session_id=session_id, format="plain")
            return HookResult(decision="allow", system_message="✅ Completion validated - work meets requirements")

        block_match = re.search(r"\bBLOCK:\s*(.+)", cleaned_output, re.IGNORECASE | re.DOTALL)
        if block_match:
            reason = block_match.group(1).strip()
            self.logger.info("completion_moderator_block", session_id=session_id, reason=reason[:100], format="plain")
            return HookResult.block(f"❌ COMPLETION VALIDATION FAILED\n\n{reason}\n\nWork is not complete. Continue working or provide clarification.")

        # No clear decision - fail closed
        self.logger.warning("completion_moderator_unclear", session_id=session_id, output=cleaned_output[:200])
        return HookResult.block(
            f"COMPLETION VALIDATION UNCLEAR\n\nModerator output:\n{output}\n\nCannot determine if work is complete. Defaulting to BLOCK for safety."
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
            conversation_context = prepare_moderator_context(transcript_path)
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
                f"COMPLETION VALIDATION ERROR\n\nFailed to read conversation context: {e}\n\nCannot verify completion without context."
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
                f"❌ COMPLETION VALIDATION ERROR\n\n"
                f"Agent execution failed with exit code {error.exit_code}\n\n"
                f"Error output:\n{stderr_preview}\n\n"
                f"Cannot verify completion due to moderator failure."
            )
        if isinstance(error, AgentError):
            self.logger.error("completion_moderator_error", session_id=session_id, execution_id=execution_id, error=str(error))
            return HookResult.block(f"❌ COMPLETION VALIDATION ERROR\n\n{error}\n\nCannot verify completion due to moderator failure.")
        self.logger.error("completion_moderator_error", session_id=session_id, execution_id=execution_id, error=str(error))
        raise error

    def _check_first_output_in_audit_log(self, audit_log_path: Path) -> bool:
        """Check if audit log contains first output marker.

        Args:
            audit_log_path: Path to audit log file

        Returns:
            True if first output marker found, False otherwise
        """
        if not audit_log_path or not audit_log_path.exists():
            return False

        try:
            with audit_log_path.open() as f:
                for line in f:
                    if "=== FIRST OUTPUT:" in line:
                        return True
        except OSError:
            pass

        return False

    def _check_decision_in_output(self, output: str) -> bool:
        """Check if moderator output contains a decision tag.

        Args:
            output: Moderator output string

        Returns:
            True if <decision> tag found, False otherwise
        """
        if not output:
            return False
        return "<decision>" in output.lower()

    def _run_moderator_with_first_output_monitoring(
        self,
        session_id: str,
        execution_id: str,
        cli: Any,
        moderator_prompt: Path,
        conversation_context: str,
        completion_moderator_config: Any,
        audit_log_path: Path | None,
        max_attempts: int = 2,
        first_output_timeout: float = 3.5,
    ) -> tuple[str, dict[str, Any] | None]:
        """Run moderator with automatic restart if hangs during startup or analysis.

        Monitors for TWO types of hangs:
        1. **Startup hang**: No first output within first_output_timeout (default 3.5s)
           - Claude never starts streaming
           - Process appears stuck before any output

        2. **Analysis hang**: First output produced but no <decision> tag
           - Claude starts streaming (system init message)
           - But hangs during thinking/analysis phase
           - Never produces final <decision> output

        If either hang detected, automatically restarts (up to max_attempts total).

        This fixes two historical issues:
        - execution 90858109: hung during analysis phase after first output
        - execution 9101bf43: hung during analysis, no decision after first output

        Args:
            session_id: Session ID
            execution_id: Execution ID
            cli: Agent CLI instance
            moderator_prompt: Path to moderator prompt file
            conversation_context: Conversation context string
            completion_moderator_config: Agent config
            audit_log_path: Audit log path (required for monitoring)
            max_attempts: Maximum attempts (default 2: original + 1 restart)
            first_output_timeout: Seconds to wait for first output (default 3.5s)

        Returns:
            Tuple of (output, metadata)

        Raises:
            AgentTimeoutError: All attempts hung without first output
            AgentError: Other execution errors
        """
        import time

        if not audit_log_path:
            # No audit log - cannot monitor for first output, run directly
            result: tuple[str, dict[str, Any] | None] = cli.run_print(
                instruction_file=moderator_prompt,
                stdin=conversation_context,
                agent_config=completion_moderator_config,
                audit_log_path=audit_log_path,
            )
            return result

        # Use shorter timeout to detect hangs quickly
        # first_output_timeout determines how quickly we detect and retry on hangs
        original_timeout = completion_moderator_config.timeout
        hang_detection_timeout = max(int(first_output_timeout * 2), 10)  # At least 2x first_output_timeout

        for attempt in range(1, max_attempts + 1):
            attempt_execution_id = f"{execution_id}-attempt{attempt}"

            # Clear audit log for this attempt
            if audit_log_path.exists():
                audit_log_path.unlink()

            self.logger.info(
                "completion_moderator_attempt_starting",
                session_id=session_id,
                execution_id=attempt_execution_id,
                attempt=attempt,
                max_attempts=max_attempts,
                timeout=hang_detection_timeout,
            )

            # Set shorter timeout for hang detection
            completion_moderator_config.timeout = hang_detection_timeout

            try:
                start_time = time.time()

                # Start moderator execution
                # Note: first_output_timeout monitoring happens via audit log polling
                # If no first output within first_output_timeout, we check audit log and retry
                output, metadata = cli.run_print(
                    instruction_file=moderator_prompt,
                    stdin=conversation_context,
                    agent_config=completion_moderator_config,
                    audit_log_path=audit_log_path,
                )

                # Success - verify first output was produced
                has_first_output = self._check_first_output_in_audit_log(audit_log_path)
                has_decision = self._check_decision_in_output(output)
                elapsed = time.time() - start_time

                if has_first_output and has_decision:
                    # Complete success - both first output and decision present
                    self.logger.info(
                        "completion_moderator_attempt_success",
                        session_id=session_id,
                        execution_id=attempt_execution_id,
                        attempt=attempt,
                        elapsed=round(elapsed, 2),
                    )
                    # Restore original timeout
                    completion_moderator_config.timeout = original_timeout
                    return output, metadata

                if has_first_output and not has_decision:
                    # Analysis hang: first output present but no decision
                    # This is the case where Claude starts streaming but hangs during analysis
                    if attempt < max_attempts:
                        # Kill hung process before retry
                        cli.kill_current_process()

                        self.logger.warning(
                            "completion_moderator_analysis_hang_restarting",
                            session_id=session_id,
                            execution_id=attempt_execution_id,
                            attempt=attempt,
                            max_attempts=max_attempts,
                            reason="First output present but no decision tag - Claude hung during analysis",
                            output_preview=output[:500] if output else "",
                            output_length=len(output) if output else 0,
                            has_streaming_messages=bool(output and '{"type"' in output),
                            elapsed=elapsed,
                        )
                        continue  # Retry
                    # Last attempt - return output even without decision
                    # Parsing will handle missing decision (fail-closed)
                    self.logger.error(
                        "completion_moderator_analysis_hang_exhausted",
                        session_id=session_id,
                        execution_id=attempt_execution_id,
                        attempt=attempt,
                        reason="No decision tag after all attempts",
                    )
                    completion_moderator_config.timeout = original_timeout
                    return output, metadata

                # No first output but completed (shouldn't happen, but handle it)
                self.logger.warning(
                    "completion_moderator_no_first_output_but_completed",
                    session_id=session_id,
                    execution_id=attempt_execution_id,
                    attempt=attempt,
                )
                # Still return the output - this is unexpected but not necessarily wrong
                completion_moderator_config.timeout = original_timeout
                return output, metadata

            except (AgentTimeoutError, AgentExecutionError) as e:
                # Check if first output was produced before failure
                has_first_output = self._check_first_output_in_audit_log(audit_log_path)

                if not has_first_output and attempt < max_attempts:
                    # No first output - this is a hang, retry
                    # Kill hung process before retry
                    cli.kill_current_process()

                    # Get audit log size for debugging
                    audit_log_size = audit_log_path.stat().st_size if audit_log_path and audit_log_path.exists() else 0

                    self.logger.warning(
                        "completion_moderator_hang_detected_restarting",
                        session_id=session_id,
                        execution_id=attempt_execution_id,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error_type=type(e).__name__,
                        reason="No first output within timeout - likely Claude hang",
                        audit_log_size=audit_log_size,
                        elapsed=time.time() - start_time,
                    )

                    # Restore timeout before retry
                    completion_moderator_config.timeout = original_timeout
                    continue  # Retry

                # First output was produced OR last attempt - re-raise
                completion_moderator_config.timeout = original_timeout
                raise

            except Exception:
                # Other errors - re-raise immediately
                completion_moderator_config.timeout = original_timeout
                raise

        # All attempts exhausted without success
        raise AgentTimeoutError(
            timeout=int(hang_detection_timeout * max_attempts),
            cmd=["claude", "--print"],  # Simplified cmd for error reporting
            duration=float(hang_detection_timeout * max_attempts),
        )

    def _validate_completion(self, session_id: str, transcript_path: Path) -> HookResult:
        """Validate completion marker using moderator agent.

        Args:
            session_id: Session ID for logging
            transcript_path: Path to transcript file

        Returns:
            Validation result (ALLOW if work complete, BLOCK if not)
        """
        execution_id = str(uuid.uuid4())[:8]

        if not self.config.get("response_scanner.completion_moderator_enabled", True):
            return HookResult.allow()

        # Load conversation context
        conversation_context, error_result = self._load_moderator_context(session_id, execution_id, transcript_path)
        if error_result:
            return error_result

        # Check moderator prompt exists
        prompts_dir = self.config.root / self.config.get("prompts.dir")
        moderator_prompt = prompts_dir / self.config.get("prompts.completion_moderator", "completion_moderator.txt")

        if not moderator_prompt.exists():
            self.logger.error("completion_moderator_prompt_missing", session_id=session_id, execution_id=execution_id, path=str(moderator_prompt))
            return HookResult.block(
                f"COMPLETION VALIDATION ERROR\n\nModerator prompt not found: {moderator_prompt}\n\nCannot validate completion without prompt."
            )

        # Create audit log file for debugging/troubleshooting
        audit_dir = self.config.root / "logs" / "agent-cli"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_log_path = audit_dir / f"completion-moderator-{execution_id}.log"

        try:
            from datetime import datetime

            with audit_log_path.open("w") as f:
                f.write(f"=== MODERATOR EXECUTION {execution_id} ===\n")
                if conversation_context:
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
            import signal
            import time

            # Set up alarm for framework timeout detection
            # Framework timeout is 120s, set alarm at 115s to log before kill
            framework_timeout = 120
            warning_time = framework_timeout - 5

            def timeout_warning_handler(signum: int, frame: Any) -> None:
                """Log warning when approaching framework timeout."""
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

            # Run moderator with first-output monitoring and automatic restart
            if not conversation_context:
                return HookResult.block("Cannot validate completion - no conversation context")

            output, _ = self._run_moderator_with_first_output_monitoring(
                session_id=session_id,
                execution_id=execution_id,
                cli=cli,
                moderator_prompt=moderator_prompt,
                conversation_context=conversation_context,
                completion_moderator_config=completion_moderator_config,
                audit_log_path=audit_log_path,
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

            self.logger.info("completion_moderator_raw_output", session_id=session_id, execution_id=execution_id, output=output)
            return self._parse_moderator_decision(session_id, output)
        except Exception as e:
            return self._handle_moderator_error(session_id, execution_id, e)

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
