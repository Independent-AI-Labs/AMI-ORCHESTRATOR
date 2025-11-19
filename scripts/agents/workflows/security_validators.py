"""Security-related validators for malicious behavior and command validation."""

import re
from typing import Any

from base.backend.utils.uuid_utils import uuid7
from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.cli.exceptions import AgentError, AgentExecutionError, AgentTimeoutError
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.config import get_config
from scripts.agents.validation.moderator_runner import run_moderator_with_retry
from scripts.agents.validation.validation_utils import (
    load_bash_patterns,
    parse_code_fence_output,
)
from scripts.agents.workflows.core import HookInput, HookResult, HookValidator, prepare_moderator_context


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
        execution_id = uuid7()[:8]

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

        # Find first occurrence of ALLOW or BLOCK: (skips preamble)
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
            execution_id = uuid7()[:8]

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
            execution_id = uuid7()[:8]

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

    def _extract_strings(self, obj: Any) -> tuple[str, ...]:
        """Recursively extract all string values from nested structures."""
        strings = []
        if isinstance(obj, str):
            strings.append(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                strings.extend(self._extract_strings(value))
        elif isinstance(obj, list):
            for item in obj:
                strings.extend(self._extract_strings(item))
        return tuple(strings)

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
        # Only "command" field is actually executed by bash tool.
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
