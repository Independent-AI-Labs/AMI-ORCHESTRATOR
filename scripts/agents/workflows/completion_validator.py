"""Completion validation logic for response validators."""

import re
import signal
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from base.backend.utils.uuid_utils import uuid7
from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.cli.exceptions import AgentError, AgentExecutionError, AgentTimeoutError
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.config import get_config
from scripts.agents.validation.moderator_runner import run_moderator_with_retry
from scripts.agents.validation.validation_utils import parse_code_fence_output
from scripts.agents.workflows.core import HookResult, count_tokens, load_session_todos, prepare_moderator_context


class CompletionValidator:
    """Handles completion-specific validation logic."""

    def validate_completion(self, session_id: str, transcript_path: Path, last_message: str, logger: Any) -> HookResult:
        """Validate completion marker using internal logic with instance logger.

        Args:
            session_id: Session ID for logging
            transcript_path: Path to transcript file
            last_message: Last assistant message text
            logger: Logger instance

        Returns:
            Validation result (ALLOW if work complete, BLOCK if not)
        """
        # Replicate the check_completion_preconditions logic with instance logger

        execution_id = uuid7()[:8]

        config = get_config()
        if not config.get("response_scanner.completion_moderator_enabled", True):
            return HookResult.allow()

        # Check for incomplete todos - BLOCK immediately if found
        # BUT: Only check when "WORK DONE" is present (not for "FEEDBACK:" which reports blockers)
        if "WORK DONE" in last_message:
            todos = load_session_todos(session_id)
            if todos:
                incomplete = [t for t in todos if t.get("status") in ("pending", "in_progress")]
                if incomplete:
                    task_list = "\n".join([f"  - {t.get('content', 'Unknown task')}" for t in incomplete])
                    return HookResult.block(
                        f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                        f"Hook: Stop\n"
                        f"Validator: ResponseScanner\n\n"
                        f"INCOMPLETE TASKS\n\n"
                        f"The following tasks are not complete:\n\n{task_list}\n\n"
                        f"Complete all tasks before claiming WORK DONE."
                    )

        # Load conversation context using internal method
        conversation_context, error_result = self._load_moderator_context(session_id, execution_id, transcript_path, logger)
        if error_result:
            return error_result

        if not conversation_context:
            return HookResult.block("Cannot validate completion - no conversation context")

        # Check moderator prompt exists
        prompts_dir = config.root / config.get("prompts.dir")
        moderator_prompt = prompts_dir / config.get("prompts.completion_moderator", "completion_moderator.txt")

        if not moderator_prompt.exists():
            logger.error("completion_moderator_prompt_missing", session_id=session_id, execution_id=execution_id, path=str(moderator_prompt))
            return HookResult.block(
                f"COMPLETION VALIDATION ERROR\n\nModerator prompt not found: {moderator_prompt}\n\nCannot validate completion without prompt."
            )

        return self._run_completion_moderator(session_id, conversation_context, moderator_prompt, logger)

    def _load_moderator_context(self, session_id: str, execution_id: str, transcript_path: Path, logger: Any) -> tuple[str | None, HookResult | None]:
        """Load and validate conversation context for moderator with instance logger.

        Args:
            session_id: Session ID for logging
            execution_id: Unique execution ID for this moderator run
            transcript_path: Path to transcript file
            logger: Logger instance

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

            logger.info(
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
            logger.error("completion_moderator_transcript_error", session_id=session_id, execution_id=execution_id, error=str(e))
            error_result = HookResult.block(
                f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: Stop\n"
                f"Validator: ResponseScanner\n\n"
                f"COMPLETION VALIDATION ERROR\n\nFailed to read conversation context: {e}\n\n"
                f"Cannot verify completion without context."
            )
            return None, error_result

    def _run_completion_moderator(self, session_id: str, conversation_context: str, moderator_prompt: Path, logger: Any) -> HookResult:
        """Run the completion moderator with instance logger."""

        execution_id = uuid7()[:8]

        # Create audit log file for debugging/troubleshooting
        audit_dir = get_config().root / "logs" / "agent-cli"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_log_path = audit_dir / f"completion-moderator-{execution_id}.log"

        try:
            with audit_log_path.open("w") as f:
                f.write(f"=== MODERATOR EXECUTION {execution_id} ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Session: {session_id}\n")
                f.write(f"Context size: {len(conversation_context)} chars\n")
                f.write(f"Token count: {self._count_tokens(conversation_context)}\n\n")
                f.write("=== PROMPT ===\n")
                f.write(moderator_prompt.read_text())
                f.write("\n\n=== CONVERSATION CONTEXT ===\n")
                f.write(conversation_context)
                f.write("\n\n=== STREAMING OUTPUT ===\n")

            logger.info("completion_moderator_audit_log_created", session_id=session_id, execution_id=execution_id, path=str(audit_log_path))
        except OSError as e:
            logger.warning("completion_moderator_audit_log_failed", session_id=session_id, execution_id=execution_id, error=str(e))

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

            def timeout_warning_handler(signum: int, frame: Any) -> None:
                """Log warning when approaching framework timeout."""
                # NOTE: signum and frame are required by signal module but unused in handler
                _ = signum  # Explicitly mark as unused
                _ = frame  # Explicitly mark as unused

                logger.error(
                    "completion_moderator_approaching_timeout",
                    session_id=session_id,
                    execution_id=execution_id,
                    warning_time=warning_time,
                    framework_timeout=framework_timeout,
                )

            signal.signal(signal.SIGALRM, timeout_warning_handler)
            signal.alarm(warning_time)

            cli = get_agent_cli()
            completion_moderator_config = AgentConfigPresets.completion_moderator(f"completion-moderator-{session_id}")
            completion_moderator_config.enable_streaming = True

            start_time = time.time()

            logger.info("completion_moderator_starting", session_id=session_id, execution_id=execution_id)

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
            logger.info(
                "completion_moderator_completed",
                session_id=session_id,
                execution_id=execution_id,
                elapsed_seconds=round(elapsed_time, 2),
            )

            slow_threshold_seconds = 60
            if elapsed_time > slow_threshold_seconds:
                logger.warning(
                    "completion_moderator_slow",
                    session_id=session_id,
                    execution_id=execution_id,
                    elapsed_seconds=round(elapsed_time, 2),
                    threshold_seconds=slow_threshold_seconds,
                )

            # Log both raw and cleaned output for debugging
            cleaned_output = parse_code_fence_output(output)
            logger.info("completion_moderator_raw_output", session_id=session_id, execution_id=execution_id, raw_output=output, cleaned_output=cleaned_output)
            return self._parse_moderator_decision(session_id, output, logger)
        except Exception as e:
            return self._handle_moderator_error(session_id, execution_id, e, logger)

    def _parse_moderator_decision(self, session_id: str, output: str, logger: Any) -> HookResult:
        """Parse moderator output for ALLOW/BLOCK decision with instance logger.

        Args:
            session_id: Session ID for logging
            output: Raw moderator output
            logger: Logger instance

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
                logger.warning("completion_moderator_conversational", session_id=session_id, phrase=phrase_pattern, output_preview=cleaned_output[:200])
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

        # Check for ALLOW: format (with explanation) - REQUIRED FORMAT
        allow_with_reason_match = re.search(r"\bALLOW:\s*(.+)", cleaned_output, re.IGNORECASE | re.DOTALL)
        # Check for BLOCK: format
        block_match = re.search(r"\bBLOCK:\s*", cleaned_output, re.IGNORECASE)

        if allow_with_reason_match:
            # Required format: ALLOW: explanation
            explanation = allow_with_reason_match.group(1).strip()
            # Truncate at BLOCK if present (shouldn't happen but be safe)
            if "BLOCK" in explanation.upper():
                explanation = explanation[: explanation.upper().index("BLOCK")].strip()

            system_message = f"✅ MODERATOR: {explanation}"

            logger.info("completion_moderator_allow", session_id=session_id, explanation=explanation[:200])
            return HookResult(decision="allow", system_message=system_message)

        # Check for bare ALLOW (format without explanation) - block for safety
        bare_allow_match = re.search(r"^\s*ALLOW\s*$|^\s*ALLOW\s+(?!\:)", cleaned_output, re.IGNORECASE)
        if bare_allow_match:
            # Log warning for format without explanation

            logger.warning(
                "completion_moderator_allow_no_explanation", session_id=session_id, note="Moderator used deprecated ALLOW format without explanation"
            )
            return HookResult.block(
                "🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                "Hook: Stop\n"
                "Validator: ResponseScanner\n\n"
                "BLOCKED: ALLOW without explanation\n\n"
                "Moderator returned bare 'ALLOW' without explanation.\n"
                "This format is blocked - explanation required.\n\n"
                "Required format: 'ALLOW: <explanation>'\n\n"
                "Defaulting to BLOCK for safety."
            )

        if block_match:
            # Extract reason after BLOCK:
            reason_start = block_match.end()
            reason = cleaned_output[reason_start:].strip()
            if not reason:
                reason = "Work incomplete or validation failed"

            logger.info("completion_moderator_block", session_id=session_id, reason=reason[:200])
            return HookResult.block(
                f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: Stop\n"
                f"Validator: ResponseScanner\n\n"
                f"❌ MODERATOR: {reason}\n\n"
                f"Continue working or provide clarification."
            )

        # No clear decision - fail closed

        logger.warning("completion_moderator_unclear", session_id=session_id, output=cleaned_output[:500], raw_output=output[:500])
        return HookResult.block(
            f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            f"Hook: Stop\n"
            f"Validator: ResponseScanner\n\n"
            f"COMPLETION VALIDATION UNCLEAR\n\n"
            f"Moderator output (cleaned):\n{cleaned_output[:500]}\n\n"
            f"Expected 'ALLOW: explanation' or 'BLOCK: reason'. Defaulting to BLOCK for safety."
        )

    def _handle_moderator_error(self, session_id: str, execution_id: str, error: Exception, logger: Any) -> HookResult:
        """Handle moderator execution errors with instance logger.

        Args:
            session_id: Session ID for logging
            execution_id: Unique execution ID
            error: Exception that occurred
            logger: Logger instance

        Returns:
            Block result with error details
        """

        if isinstance(error, AgentTimeoutError):
            logger.error(
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
            logger.error(
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
            logger.error("completion_moderator_error", session_id=session_id, execution_id=execution_id, error=str(error))
            return HookResult.block(
                f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: Stop\n"
                f"Validator: ResponseScanner\n\n"
                f"❌ COMPLETION VALIDATION ERROR\n\n{error}\n\n"
                f"Cannot verify completion due to moderator failure."
            )

        logger.error("completion_moderator_error", session_id=session_id, execution_id=execution_id, error=str(error))
        raise error

    def _count_tokens(self, text: str) -> int:
        """Helper method to count tokens in text."""

        return count_tokens(text)
