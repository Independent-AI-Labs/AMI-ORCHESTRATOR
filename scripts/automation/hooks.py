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

from scripts.automation.agent_cli import AgentConfigPresets, AgentError, AgentExecutionError, get_agent_cli
from scripts.automation.config import get_config
from scripts.automation.logger import get_logger
from scripts.automation.transcript import format_messages_for_prompt, get_last_n_messages, is_actual_user_message
from scripts.automation.validators import parse_code_fence_output, validate_python_full

# Resource limits (DoS protection)
MAX_HOOK_INPUT_SIZE = 10 * 1024 * 1024  # 10MB

# Token limits for moderator context
# Claude CLI has input size limits beyond model context window - stay conservative
MAX_MODERATOR_CONTEXT_TOKENS = 100_000  # Leave buffer for prompt + CLI input limits

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
    """Prepare conversation context for moderator with token truncation.

    Gets LAST N messages from transcript and applies binary search truncation
    to fit within MAX_MODERATOR_CONTEXT_TOKENS limit (100K tokens).

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
    conversation_context = format_messages_for_prompt(all_messages)
    token_count = count_tokens(conversation_context)

    # If transcript is too large, use binary search to find how many messages fit
    if token_count > MAX_MODERATOR_CONTEXT_TOKENS:
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
        # Stop/SubagentStop hooks use decision/reason format
        result: dict[str, Any] = {}
        if self.decision:
            result["decision"] = self.decision
        if self.reason:
            result["reason"] = self.reason
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

            # Output result
            print(result.to_json())

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
            # Fail open on error
            print(HookResult.allow().to_json())
            return 0

        except Exception as e:
            error_log_args: dict[str, Any] = {"error": str(e)}
            if hook_input:
                error_log_args["session_id"] = hook_input.session_id
            self.logger.error("hook_error", **error_log_args)
            # Fail open on error (safety)
            print(HookResult.allow().to_json())
            return 0


class CommandValidator(HookValidator):
    """Validates Bash commands."""

    DENY_PATTERNS = [
        (r"\bpython3?\b", "Use ami-run instead of direct python"),
        (r"\bpip3?\b", "Add to pyproject.toml and use ami-uv sync"),
        (r"(?<!i-)\buv\s+", "Use ami-uv wrapper"),
        (r"(?<![/\w])pytest\s+", "Use ami-run scripts/run_tests.py instead of direct pytest"),
        (r"\bcat\s+>", "Use Write/Edit tools instead of cat - bypasses code quality validation"),
        (r"\becho\s+.*>", "Use Write/Edit tools instead of echo - bypasses code quality validation"),
        (r"\btee\s+", "Use Write/Edit tools instead of tee - bypasses code quality validation"),
        (r"--no-verify", "Git hook bypass forbidden"),
        (r"\bgit\b.*\bcommit\b", "Use scripts/git_commit.sh"),
        (r"\bgit\b.*\bpush\b", "Use scripts/git_push.sh"),
        (r"\bgit\b.*\brestore\b", "Git restore forbidden - modifies staging/working tree"),
        (r"\bgit\b.*\breset\b", "Git reset forbidden - modifies HEAD/staging/working tree"),
        (r"\bgit\b.*\bcheckout\b", "Git checkout forbidden - modifies working tree"),
        (r"\bgit\b.*\bpull\b", "Git pull forbidden - modifies working tree"),
        (r"\bgit\b.*\brebase\b", "Git rebase forbidden - rewrites history"),
        (r"\bgit\b.*\bmerge\b", "Git merge forbidden - modifies working tree"),
        (r"\bgit\b.*\brm\b.*--cached", "Git rm --cached forbidden - removes files from git index"),
        # Check && before & to avoid false matches (second & in && would match &(?!&))
        (r"&&", "Use separate Bash calls instead of &&"),
        (r"&(?!&)", "Use run_in_background parameter instead of &"),
        (r";", "Use separate Bash calls instead of ;"),
        (r"\|\|", "Use separate Bash calls instead of ||"),
        (r"\|", "Use dedicated tools (Read/Grep) instead of pipes"),
        (r">>", "Use Edit/Write tools instead of >>"),
        (r"\bsed\b", "Use Edit tool instead of sed"),
        (r"\bawk\b", "Use Read/Grep tools instead of awk"),
        (r"\bnode\b", "Use nodes launcher for Node.js operations"),
        (r"\bwget\b", "Use Read/WebFetch tools instead of wget"),
        (r"\bpkill\b", "Use KillShell tool for background process management"),
        (r"\bkill\b", "Use KillShell tool for background process management"),
        (r"\bkillall\b", "Use KillShell tool for background process management"),
        (r"\bsudo\b", "Sudo commands not allowed (except in approved scripts)"),
        (r"(?<!--)\bchmod\b", "File permission changes not allowed (git update-index --chmod is allowed)"),
        (r"\bchown\b", "File ownership changes not allowed"),
    ]

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
        """Validate bash command.

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

        # Check all strings in tool_input (handles nested structures)
        all_strings = list(self._extract_strings(hook_input.tool_input))

        for pattern, message in self.DENY_PATTERNS:
            for string in all_strings:
                if re.search(pattern, string):
                    return HookResult.deny(f"{message} (pattern: {pattern})")

        return HookResult.allow()


class CodeQualityValidator(HookValidator):
    """Validates code changes for quality regressions using LLM-based audit."""

    # Files exempt from pattern checks (contain error messages with forbidden patterns)
    PATTERN_CHECK_EXEMPTIONS = {
        "scripts/automation/hooks.py",
        "scripts/automation/validators.py",
    }

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
        """Validate code quality using LLM diff audit.

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

        # Check if file is exempt from pattern checks
        is_pattern_exempt = any(file_path.endswith(exempt) for exempt in self.PATTERN_CHECK_EXEMPTIONS)

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

        # Check for ALLOW decision
        if re.search(r"\bALLOW\b", cleaned_output, re.IGNORECASE):
            self.logger.info("completion_moderator_allow", session_id=session_id)
            return HookResult.allow()

        # Check for BLOCK decision
        block_match = re.search(r"\bBLOCK:\s*(.+)", cleaned_output, re.IGNORECASE | re.DOTALL)
        if block_match:
            reason = block_match.group(1).strip()
            self.logger.info("completion_moderator_block", session_id=session_id, reason=reason[:100])
            return HookResult.block(f"❌ COMPLETION VALIDATION FAILED\n\n{reason}\n\nWork is not complete. Continue working or provide clarification.")

        # No clear decision - fail closed
        self.logger.warning("completion_moderator_unclear", session_id=session_id, output=cleaned_output[:200])
        return HookResult.block(f"COMPLETION VALIDATION UNCLEAR\n\nModerator output:\n{output}\n\nCannot determine if work is complete.")

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

        # Run moderator agent and parse decision
        try:
            cli = get_agent_cli()
            completion_moderator_config = AgentConfigPresets.completion_moderator(session_id)
            completion_moderator_config.enable_streaming = True
            output, _ = cli.run_print(
                instruction_file=moderator_prompt,
                stdin=conversation_context,
                agent_config=completion_moderator_config,
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
