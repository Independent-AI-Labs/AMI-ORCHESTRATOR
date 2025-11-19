"""Research validators to ensure adequate research before code changes."""

import difflib
import re
from pathlib import Path
from typing import Any

import scripts.agents.validation.moderator_runner
import scripts.agents.workflows.core
from base.backend.utils.uuid_utils import uuid7
from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.cli.exceptions import AgentError, AgentExecutionError, AgentTimeoutError
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.transcript import format_messages_for_prompt, get_last_n_messages
from scripts.agents.validation.validation_utils import parse_code_fence_output
from scripts.agents.workflows.core import HookInput, HookResult, HookValidator


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
        execution_id = uuid7()[:8]

        self.logger.info(
            "research_validator_start",
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

        output, _ = scripts.agents.validation.moderator_runner.run_moderator_with_retry(
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

        # Find first occurrence of ALLOW or BLOCK: (skips preamble)
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
            execution_id = uuid7()[:8]

            if isinstance(error, AgentTimeoutError):
                self.logger.error("research_validator_timeout", session_id=session_id, execution_id=execution_id)
            elif isinstance(error, AgentExecutionError):
                self.logger.error("research_validator_execution_error", session_id=session_id, execution_id=execution_id, exit_code=error.exit_code)
            else:  # AgentError
                self.logger.error("research_validator_error", session_id=session_id, execution_id=execution_id, error=str(error))

            # Fail open on all agent errors
            return HookResult.allow()
