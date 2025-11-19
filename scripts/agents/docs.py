"""Documentation maintenance executor for .md documentation files.

Orchestrates worker agents to maintain docs (UPDATE/ARCHIVE/DELETE),
moderator agents to validate, and retry loops with timeout.
Supports both sync (default) and async parallel modes.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.common import GenericExecutor
from scripts.agents.core.models import UnifiedExecutionAttempt, UnifiedExecutionResult


class DocsExecutor(GenericExecutor[UnifiedExecutionResult]):
    """Maintains .md documentation files using worker and moderator agents."""

    def __init__(self) -> None:
        """Initialize docs executor."""
        super().__init__(UnifiedExecutionResult)

    def get_executor_name(self) -> str:
        """Get the name of this executor for logging purposes."""
        return "docs"

    def get_include_patterns(self) -> list[str]:
        """Get the file inclusion patterns for this executor."""
        result: list[str] = self.config.get("docs.include_patterns", ["**/*.md"])
        return result

    def get_exclude_patterns(self) -> list[str]:
        """Get the file exclusion patterns for this executor."""
        result: list[str] = self.config.get(
            "docs.exclude_patterns",
            [
                "**/CLAUDE.md",
                "**/AGENTS.md",
                "**/archive/**",
                "**/feedback-*.md",
                "**/progress-*.md",
                "**/node_modules/**",
                "**/.git/**",
                "**/.venv/**",
                "**/venv/**",
                "**/__pycache__/**",
                "**/*.egg-info/**",
                "**/.cache/**",
                "**/.pytest_cache/**",
                "**/.mypy_cache/**",
                "**/.ruff_cache/**",
                "**/dist/**",
                "**/build/**",
                "**/ux/ui-concept/**",
            ],
        )
        return result

    def execute_single_item(self, item_path: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> UnifiedExecutionResult:
        """Execute a single item with documentation maintenance.

        Args:
            item_path: Path to the item to process
            root_dir: Root directory for codebase inspection (defaults to current directory)
            user_instruction: Optional prepended instruction for the worker

        Returns:
            Doc result for the item
        """
        # Delegate to the original _execute_single_doc with alias
        return self._execute_single_doc(item_path, root_dir, user_instruction)

    def execute_docs(
        self,
        directory: Path,
        parallel: bool = False,
        root_dir: Path | None = None,
        user_instruction: str | None = None,
    ) -> list[UnifiedExecutionResult]:
        """Execute documentation maintenance for all .md files in directory.

        Args:
            directory: Directory containing .md documentation files
            parallel: Enable parallel execution (async mode)
            root_dir: Root directory for codebase inspection (defaults to current directory)
            user_instruction: Optional prepended instruction for all docs workers

        Returns:
            List of doc results
        """
        # Use the base class execute_items method which handles the orchestration
        # Since this DocsExecutor was initialized with UnifiedExecutionResult type, execute_items should return list[UnifiedExecutionResult]
        return self.execute_items(directory, parallel, root_dir, user_instruction)

    def _execute_single_doc(self, doc_file: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> UnifiedExecutionResult:
        """Execute documentation maintenance for a single doc with retry loop.

        Args:
            doc_file: Path to .md documentation file
            root_dir: Root directory for codebase inspection (defaults to current directory)
            user_instruction: Optional prepended instruction for the docs worker

        Returns:
            Doc result
        """
        start_time: float = time.time()
        attempts: list[UnifiedExecutionAttempt] = []
        timeout: int = self.config.get("docs.timeout_per_doc", 600)
        moderator_enabled: bool = self.config.get("docs.moderator_enabled", True)

        doc_name: str = doc_file.stem

        try:
            # Read doc content
            doc_content: str = doc_file.read_text()

            # Build worker instruction using docs_worker prompt
            worker_prompt_file: Path = self.prompts_dir / "docs_worker.txt"
            worker_prompt_template: str = worker_prompt_file.read_text()

            # Replace template variables in worker prompt
            worker_instruction: str = ""
            if user_instruction:
                worker_instruction = f"{user_instruction}\n\n"

            worker_instruction += worker_prompt_template.format(
                doc_path=str(doc_file),
            )
            worker_instruction += f"\n{doc_content}\n"

            # Retry loop with timeout
            attempt_num: int = 0
            additional_context: str = ""

            while time.time() - start_time < timeout:
                attempt_num += 1
                attempt_start: float = time.time()

                self.logger.info(
                    "worker_attempt",
                    doc=doc_name,
                    attempt=attempt_num,
                )

                # Build worker instruction with additional context if needed
                full_instruction: str = worker_instruction
                if additional_context:
                    full_instruction += f"\n\n{additional_context}"

                # Execute worker with streaming enabled
                worker_config = AgentConfigPresets.task_worker(self.session_id)
                worker_config.enable_streaming = True
                worker_output, _ = self.cli.run_print(
                    instruction=full_instruction,
                    stdin="",
                    agent_config=worker_config,
                    cwd=root_dir,
                )

                attempt_duration: float = time.time() - attempt_start

                # Parse worker output
                completion_marker: dict[str, Any] = self._parse_completion_marker(worker_output)
                action: Literal["UPDATE", "ARCHIVE", "DELETE"] | None = self._detect_action(worker_output)

                if completion_marker["type"] == "feedback":
                    # Worker needs feedback - return feedback status
                    attempts.append(
                        UnifiedExecutionAttempt(
                            attempt_number=attempt_num,
                            worker_output=worker_output,
                            moderator_output=None,
                            timestamp=datetime.now(),
                            duration=attempt_duration,
                        )
                    )

                    return UnifiedExecutionResult(
                        item_path=doc_file,
                        status="feedback",
                        action=action,
                        attempts=attempts,
                        feedback=completion_marker["content"],
                        total_duration=time.time() - start_time,
                    )

                if completion_marker["type"] == "work_done":
                    # Worker claims completion - validate with moderator
                    if not moderator_enabled:
                        # No moderator, accept worker's claim
                        attempts.append(
                            UnifiedExecutionAttempt(
                                attempt_number=attempt_num,
                                worker_output=worker_output,
                                moderator_output=None,
                                timestamp=datetime.now(),
                                duration=attempt_duration,
                            )
                        )

                        return UnifiedExecutionResult(
                            item_path=doc_file,
                            status="completed",
                            action=action,
                            attempts=attempts,
                            total_duration=time.time() - start_time,
                        )

                    # Run moderator
                    moderator_start: float = time.time()
                    self.logger.info(
                        "moderator_check_started",
                        doc=doc_name,
                        attempt=attempt_num,
                    )

                    # Moderator validation - load prompt file and pass doc/worker context
                    moderator_prompt_file: Path = self.prompts_dir / "docs_moderator.txt"
                    moderator_prompt_template: str = moderator_prompt_file.read_text()

                    # Replace template variables in moderator prompt
                    moderator_instruction: str = moderator_prompt_template.format(
                        doc_path=str(doc_file),
                        doc_content=doc_content,
                        worker_output=worker_output,
                        worker_action=action if action else "UNKNOWN",
                    )

                    # Moderator uses streaming too for consistency
                    moderator_config = AgentConfigPresets.task_moderator(self.session_id)
                    moderator_config.enable_streaming = True
                    moderator_output, _ = self.cli.run_print(
                        instruction=moderator_instruction,
                        stdin="",
                        agent_config=moderator_config,
                        cwd=root_dir,
                    )

                    moderator_result: dict[str, Any] = self._parse_moderator_result(moderator_output)

                    moderator_duration: float = time.time() - moderator_start
                    self.logger.info(
                        "moderator_check_completed",
                        doc=doc_name,
                        attempt=attempt_num,
                        duration=round(moderator_duration, 1),
                        final_status=moderator_result["status"],
                    )

                    attempts.append(
                        UnifiedExecutionAttempt(
                            attempt_number=attempt_num,
                            worker_output=worker_output,
                            moderator_output=moderator_output,
                            timestamp=datetime.now(),
                            duration=attempt_duration,
                        )
                    )

                    if moderator_result["status"] == "pass":
                        # Doc maintenance completed successfully
                        return UnifiedExecutionResult(
                            item_path=doc_file,
                            status="completed",
                            action=action,
                            attempts=attempts,
                            total_duration=time.time() - start_time,
                        )

                    # Moderator failed - retry worker with feedback
                    failure_reason: str = moderator_result["reason"] if moderator_result["reason"] else "Validation failed"
                    additional_context = f"PREVIOUS ATTEMPT FAILED VALIDATION:\n{failure_reason}\n\nPlease fix the issues and try again."

                    # Continue retry loop
                    continue

                # No completion marker - worker didn't finish properly
                attempts.append(
                    UnifiedExecutionAttempt(
                        attempt_number=attempt_num,
                        worker_output=worker_output,
                        moderator_output=None,
                        timestamp=datetime.now(),
                        duration=attempt_duration,
                    )
                )

                additional_context = (
                    "PREVIOUS ATTEMPT DID NOT OUTPUT COMPLETION MARKER.\n"
                    "You MUST output either 'WORK DONE' or 'FEEDBACK: <questions>' "
                    "at the end of your response."
                )

                # Continue retry loop
                continue

            # Timeout reached
            return UnifiedExecutionResult(
                item_path=doc_file,
                status="timeout",
                action=None,
                attempts=attempts,
                total_duration=time.time() - start_time,
                error=f"Doc maintenance timed out after {timeout}s",
            )

        except Exception as e:
            self.logger.error(
                "doc_error",
                doc=doc_name,
                error=str(e),
            )

            return UnifiedExecutionResult(
                item_path=doc_file,
                status="failed",
                action=None,
                attempts=attempts,
                total_duration=time.time() - start_time,
                error=str(e),
            )

    def _parse_completion_marker(self, output: str) -> dict[str, Any]:
        """Parse completion marker from worker output.

        Args:
            output: Worker output text

        Returns:
            Dict with type and content
        """
        # Check for "WORK DONE"
        if "WORK DONE" in output:
            return {"type": "work_done", "content": None}

        # Check for "FEEDBACK: xxx"
        feedback_match = re.search(r"FEEDBACK:\s*(.+)", output, re.DOTALL)
        if feedback_match:
            return {"type": "feedback", "content": feedback_match.group(1).strip()}

        # No marker found
        return {"type": "none", "content": None}

    def _parse_moderator_result(self, output: str) -> dict[str, Any]:
        """Parse moderator validation result.

        Args:
            output: Moderator output text

        Returns:
            Dict with status ('pass' or 'fail') and optional reason
        """
        # Check for "PASS"
        if "PASS" in output:
            return {"status": "pass", "reason": None}

        # Check for "FAIL: xxx"
        fail_match = re.search(r"FAIL:\s*(.+)", output, re.DOTALL)
        if fail_match:
            return {"status": "fail", "reason": fail_match.group(1).strip()}

        # Moderator didn't output PASS or FAIL - treat as validation failure
        return {"status": "fail", "reason": "Moderator validation unclear - no explicit PASS or FAIL in output"}

    def _detect_action(self, worker_output: str) -> Literal["UPDATE", "ARCHIVE", "DELETE"] | None:
        """Detect which action the worker took based on output.

        Args:
            worker_output: Worker output text

        Returns:
            Action type or None if unclear
        """
        output_upper: str = worker_output.upper()

        # Look for action indicators in the output
        if "RECOMMEND DELETION" in output_upper or "DELETE" in output_upper:
            return "DELETE"
        if "ARCHIVED" in output_upper or "ARCHIVE" in output_upper:
            return "ARCHIVE"
        if "UPDATED" in output_upper or "UPDATE" in output_upper or "EDIT" in output_upper:
            return "UPDATE"

        return None
