"""Hook execution framework.

Ref: https://docs.claude.com/en/docs/claude-code/hooks.md
"""

import json
import re
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from .config import get_config
from .logger import get_logger

# Resource limits (DoS protection)
MAX_HOOK_INPUT_SIZE = 10 * 1024 * 1024  # 10MB

# Code fence parsing
MIN_CODE_FENCE_LINES = 2  # Minimum lines for valid code fence (opening + closing)


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

    def __init__(self) -> None:
        """Initialize hook validator."""
        self.config = get_config()
        self.logger = get_logger("hooks")

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
        try:
            hook_input = HookInput.from_stdin()

            # Log execution
            self.logger.info(
                "hook_execution",
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
            self.logger.error("hook_error", error=str(e))
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
        (r"\bchmod\b", "File permission changes not allowed"),
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

    def _parse_code_fence_output(self, output: str) -> str:
        """Parse output, removing markdown code fences if present.

        Args:
            output: Raw output from LLM

        Returns:
            Cleaned output with code fences removed
        """
        cleaned = output.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if len(lines) > MIN_CODE_FENCE_LINES and lines[-1] == "```":
                cleaned = "\n".join(lines[1:-1]).strip()
            elif len(lines) > 1:
                cleaned = "\n".join(lines[1:]).strip()
        return cleaned

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

        # Build diff context for LLM audit
        diff_context = f"""FILE: {file_path}

## OLD CODE
```
{old_code}
```

## NEW CODE
```
{new_code}
```
"""

        # Run LLM-based diff audit
        # Lazy import to avoid circular dependency
        try:
            from .agent_cli import AgentConfigPresets, get_agent_cli
        except ImportError:
            # agent_cli not implemented yet - allow for now
            return HookResult.allow()

        cli = get_agent_cli()
        prompts_dir = self.config.root / self.config.get("prompts.dir")
        audit_diff_instruction = prompts_dir / self.config.get("prompts.audit_diff")

        try:
            output = cli.run_print(
                instruction_file=audit_diff_instruction,
                stdin=diff_context,
                agent_config=AgentConfigPresets.audit_diff(),
            )

            # Check result - parse output for PASS/FAIL
            cleaned_output = self._parse_code_fence_output(output)

            # Check if PASS appears in the cleaned output
            if re.search(r"\bPASS\b", cleaned_output, re.IGNORECASE):
                return HookResult.allow()
            # Extract failure reason from output
            reason = output if output else "Code quality regression detected"
            return HookResult.deny(f"❌ CODE QUALITY CHECK FAILED\n\n{reason}\n\nZero-tolerance policy: NO regression allowed.")

        except Exception as e:
            # On agent errors (timeout, execution failure), deny the edit
            # This ensures we fail-closed on infrastructure failures
            from .agent_cli import AgentError

            if isinstance(e, AgentError):
                return HookResult.deny(f"❌ CODE QUALITY CHECK ERROR\n\n{e}\n\nZero-tolerance policy: Cannot verify quality.")
            raise


class ResponseScanner(HookValidator):
    """Scans responses for communication violations and completion markers."""

    def _parse_code_fence_output(self, output: str) -> str:
        """Parse output, removing markdown code fences if present.

        Args:
            output: Raw output from LLM

        Returns:
            Cleaned output with code fences removed
        """
        cleaned = output.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if len(lines) > MIN_CODE_FENCE_LINES and lines[-1] == "```":
                cleaned = "\n".join(lines[1:-1]).strip()
            elif len(lines) > 1:
                cleaned = "\n".join(lines[1:]).strip()
        return cleaned

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

    def validate(self, hook_input: HookInput) -> HookResult:
        """Scan last assistant message.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        if not hook_input.transcript_path:
            return HookResult.allow()

        transcript_path = hook_input.transcript_path

        if not transcript_path.exists():
            return HookResult.allow()

        # Read transcript
        last_message = self._get_last_assistant_message(transcript_path)
        if not last_message:
            return HookResult.allow()

        # Check for completion markers FIRST
        has_completion_marker = any(marker in last_message for marker in self.COMPLETION_MARKERS)

        if has_completion_marker:
            # Completion marker found - let moderator validate everything
            return self._validate_completion(transcript_path)

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

    def _check_moderator_dependencies(
        self,
    ) -> tuple[bool, Callable[[], Any] | None, tuple[Callable[..., str], Callable[..., list[Any]]] | None]:
        """Check if moderator dependencies are available.

        Returns:
            Tuple of (deps_available, agent_cli, transcript_module) or (False, None, None)
        """
        try:
            from .agent_cli import get_agent_cli
            from .transcript import format_messages_for_prompt, get_messages_from_last_user_forward

            return True, get_agent_cli, (format_messages_for_prompt, get_messages_from_last_user_forward)
        except ImportError:
            self.logger.warning("completion_moderator_deps_missing")
            return False, None, None

    def _load_conversation_context(
        self,
        transcript_path: Path,
        get_messages_fn: Callable[[Path], list[Any]],
        format_fn: Callable[[list[Any]], str],
    ) -> str:
        """Load and format conversation context from transcript.

        Args:
            transcript_path: Path to transcript file
            get_messages_fn: Function to get messages from transcript
            format_fn: Function to format messages for prompt

        Returns:
            Formatted conversation context string

        Raises:
            RuntimeError: If transcript cannot be read or parsed
        """
        messages = get_messages_fn(transcript_path)
        if not messages:
            raise RuntimeError("No messages found in transcript")
        return format_fn(messages)

    def _parse_moderator_decision(self, output: str) -> HookResult:
        """Parse moderator output for ALLOW/BLOCK decision.

        Args:
            output: Raw moderator output

        Returns:
            HookResult based on moderator decision
        """
        cleaned_output = self._parse_code_fence_output(output)

        # Check for ALLOW decision
        if re.search(r"\bALLOW\b", cleaned_output, re.IGNORECASE):
            self.logger.info("completion_moderator_allow")
            return HookResult.allow()

        # Check for BLOCK decision
        block_match = re.search(r"\bBLOCK:\s*(.+)", cleaned_output, re.IGNORECASE | re.DOTALL)
        if block_match:
            reason = block_match.group(1).strip()
            self.logger.info("completion_moderator_block", reason=reason[:100])
            return HookResult.block(f"❌ COMPLETION VALIDATION FAILED\n\n{reason}\n\nWork is not complete. Continue working or provide clarification.")

        # No clear decision - fail closed
        self.logger.warning("completion_moderator_unclear", output=cleaned_output[:200])
        return HookResult.block(f"COMPLETION VALIDATION UNCLEAR\n\nModerator output:\n{output}\n\nCannot determine if work is complete.")

    def _validate_completion(self, transcript_path: Path) -> HookResult:
        """Validate completion marker using moderator agent.

        Args:
            transcript_path: Path to transcript file

        Returns:
            Validation result (ALLOW if work complete, BLOCK if not)
        """
        # Check if completion moderator is enabled
        if not self.config.get("response_scanner.completion_moderator_enabled", True):
            return HookResult.allow()

        # Check dependencies
        deps_ok, get_cli, transcript_fns = self._check_moderator_dependencies()
        if not deps_ok or get_cli is None or transcript_fns is None:
            return HookResult.allow()  # Fail open if deps missing

        format_fn, get_messages_fn = transcript_fns

        # Load conversation context
        try:
            conversation_context = self._load_conversation_context(transcript_path, get_messages_fn, format_fn)
            # Log conversation context for debugging
            context_preview_length = 500
            self.logger.info(
                "completion_moderator_input",
                transcript_path=str(transcript_path),
                context_size=len(conversation_context),
                context_preview=conversation_context[-context_preview_length:] if len(conversation_context) > context_preview_length else conversation_context,
            )
        except Exception as e:
            self.logger.error("completion_moderator_transcript_error", error=str(e))
            return HookResult.block(f"COMPLETION VALIDATION ERROR\n\nFailed to read conversation context: {e}\n\nCannot verify completion without context.")

        # Check moderator prompt exists
        prompts_dir = self.config.root / self.config.get("prompts.dir")
        moderator_prompt = prompts_dir / self.config.get("prompts.completion_moderator", "completion_moderator.txt")

        if not moderator_prompt.exists():
            self.logger.error("completion_moderator_prompt_missing", path=str(moderator_prompt))
            return HookResult.block(
                f"COMPLETION VALIDATION ERROR\n\nModerator prompt not found: {moderator_prompt}\n\nCannot validate completion without prompt."
            )

        # Run moderator agent and parse decision
        try:
            from .agent_cli import AgentConfigPresets

            cli = get_cli()
            output = cli.run_print(
                instruction_file=moderator_prompt,
                stdin=conversation_context,
                agent_config=AgentConfigPresets.completion_moderator(),
            )
            # Log full moderator output for debugging
            self.logger.info("completion_moderator_raw_output", output=output)
            return self._parse_moderator_decision(output)

        except Exception as e:
            from .agent_cli import AgentError

            self.logger.error("completion_moderator_error", error=str(e))
            if isinstance(e, AgentError):
                return HookResult.block(f"❌ COMPLETION VALIDATION ERROR\n\n{e}\n\nCannot verify completion due to moderator failure.")
            raise

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
