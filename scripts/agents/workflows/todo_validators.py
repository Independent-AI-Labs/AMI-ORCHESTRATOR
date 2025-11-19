"""Todo validators for validating todo write operations."""

import re
from typing import Any

from base.backend.utils.uuid_utils import uuid7
from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.cli.exceptions import AgentError, AgentExecutionError, AgentTimeoutError
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.validation.moderator_runner import run_moderator_with_retry
from scripts.agents.validation.validation_utils import parse_code_fence_output
from scripts.agents.workflows.core import (
    HookInput,
    HookResult,
    HookValidator,
    load_session_todos,
    prepare_moderator_context,
)


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

        # Replace templates
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
        execution_id = uuid7()[:8]

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
        audit_dir = self.config.root / "logs" / "agent-cli"
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

        # Find first occurrence of ALLOW or BLOCK: (skips preamble)
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
                            execution_id = uuid7()[:8]
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
