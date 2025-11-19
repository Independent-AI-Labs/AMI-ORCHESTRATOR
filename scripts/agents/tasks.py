"""Universal task executor for .md task files.

Orchestrates worker agents to execute tasks, moderator agents to validate,
and retry loops with timeout. Supports both sync (default) and async parallel modes.
"""

import os
import time
from datetime import datetime
from pathlib import Path

from scripts.agents.common import GenericExecutor, parse_completion_marker
from scripts.agents.core.models import UnifiedExecutionAttempt, UnifiedExecutionResult
from scripts.agents.task_utils.execution import execute_worker_attempt, handle_feedback_result, validate_with_moderator
from scripts.agents.utils.file_locker import FileLockManager


class TaskExecutor(GenericExecutor[UnifiedExecutionResult]):
    """Executes .md task files using worker and moderator agents."""

    def __init__(self) -> None:
        """Initialize task executor.

        Raises:
            RuntimeError: If AMI_SUDO_PASSWORD environment variable not set and file locking enabled
        """
        super().__init__(UnifiedExecutionResult)

        # Check if file locking is enabled (can be disabled for tests)
        file_locking_enabled = self.config.get("tasks.file_locking", True)

        # Check if running as root
        self.is_root = os.geteuid() == 0

        # Validate sudo password is available (only needed if not running as root and file locking enabled)
        if file_locking_enabled and not self.is_root:
            self.sudo_password = os.environ.get("AMI_SUDO_PASSWORD")
            if not self.sudo_password:
                raise RuntimeError(
                    "AMI_SUDO_PASSWORD environment variable must be set for task execution. This password is required for file locking with chattr."
                )
        else:
            self.sudo_password = None  # Not needed when running as root or file locking disabled

        # Cache for filesystems that don't support chattr
        self._unsupported_filesystems: set[str] = set()

        # Initialize file lock manager for task file locking
        self.file_lock_manager = FileLockManager(sudo_password=self.sudo_password)

    def get_executor_name(self) -> str:
        """Get the name of this executor for logging purposes."""
        return "tasks"

    def get_include_patterns(self) -> list[str]:
        """Get the file inclusion patterns for this executor."""
        result: list[str] = self.config.get("tasks.include_patterns", ["**/*.md"])
        return result

    def get_exclude_patterns(self) -> list[str]:
        """Get the file exclusion patterns for this executor."""
        exclude_result: list[str] = self.config.get(
            "tasks.exclude_patterns",
            [
                "**/README.md",
                "**/CLAUDE.md",
                "**/AGENTS.md",
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
                "**/.gcloud/**",
                "**/google-cloud-sdk/**",
            ],
        )
        return exclude_result

    def execute_single_item(self, item_path: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> UnifiedExecutionResult:
        """Execute a single item with retry loop.

        Args:
            item_path: Path to the item to execute
            root_dir: Root directory for codebase inspection (defaults to current directory)
            user_instruction: Optional prepended instruction for the worker

        Returns:
            Task result for the item
        """
        # Delegate to the original _execute_single_task with alias
        return self._execute_single_task(item_path, root_dir, user_instruction)

    def _has_valid_extension(self, file_path: Path) -> bool:
        """Check if the file has a valid extension for this executor.

        Args:
            file_path: Path to check

        Returns:
            True if file extension is valid
        """
        # For tasks, we want .md files
        return file_path.suffix.lower() == ".md"

    def execute_tasks(
        self,
        path: Path,
        parallel: bool = False,
        root_dir: Path | None = None,
        user_instruction: str | None = None,
    ) -> list[UnifiedExecutionResult]:
        """Execute task file(s).

        Args:
            path: Path to .md task file OR directory containing task files
            parallel: Enable parallel execution (async mode)
            root_dir: Root directory where tasks execute (defaults to current directory)
            user_instruction: Optional prepended instruction for all tasks

        Returns:
            List of task results
        """
        # Call the base class execute_items method which handles the orchestration
        return self.execute_items(path, parallel, root_dir, user_instruction)

    def _execute_single_task(self, task_file: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> UnifiedExecutionResult:
        """Execute a single task with retry loop.

        Args:
            task_file: Path to .md task file
            root_dir: Root directory where tasks execute (defaults to current directory)
            user_instruction: Optional prepended instruction

        Returns:
            Task result
        """
        start_time = time.time()
        attempts: list[UnifiedExecutionAttempt] = []
        timeout = self.config.get("tasks.timeout_per_task", 3600)
        moderator_enabled = self.config.get("tasks.moderator_enabled", True)

        # Create progress file
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        task_name = task_file.stem
        progress_file = task_file.parent / f"progress-{timestamp_str}-{task_name}.md"

        file_locking_enabled = self.config.get("tasks.file_locking", True)

        try:
            # Lock task file
            if file_locking_enabled:
                self.file_lock_manager.lock_file(task_file)

            # Initialize progress file
            progress_file.parent.mkdir(parents=True, exist_ok=True)
            progress_file.write_text(f"# Task Execution Progress: {task_name}\n\n")
            with progress_file.open("a") as f:
                f.write(f"Started: {datetime.now()}\n\n")

            # Read task content
            task_content = task_file.read_text()

            # Retry loop with timeout
            attempt_num = 0
            additional_context = ""

            while time.time() - start_time < timeout:
                attempt_num += 1
                attempt_start = time.time()

                # Execute worker using imported utility function
                worker_output, worker_metadata = execute_worker_attempt(
                    task_name,
                    task_content,
                    user_instruction,
                    additional_context,
                    root_dir,
                    progress_file,
                    attempt_num,
                    self.session_id,
                    self.prompts_dir,
                    self.cli,
                )

                attempt_duration = time.time() - attempt_start

                # Update progress
                with progress_file.open("a") as f:
                    f.write(f"Worker output:\n```\n{worker_output}\n```\n\n")

                # Parse worker output
                completion_marker = parse_completion_marker(worker_output)

                if completion_marker["type"] == "feedback":
                    return handle_feedback_result(
                        task_file,
                        task_name,
                        timestamp_str,
                        completion_marker,
                        attempts,
                        attempt_num,
                        worker_output,
                        worker_metadata,
                        attempt_duration,
                        start_time,
                    )

                if completion_marker["type"] == "work_done":
                    # Worker claims completion
                    if not moderator_enabled:
                        attempts.append(
                            UnifiedExecutionAttempt(
                                attempt_number=attempt_num,
                                worker_output=worker_output,
                                moderator_output=None,
                                timestamp=datetime.now(),
                                duration=attempt_duration,
                                worker_metadata=worker_metadata,
                                moderator_metadata=None,
                            )
                        )
                        return UnifiedExecutionResult(
                            item_path=task_file,
                            status="completed",
                            attempts=attempts,
                            total_duration=time.time() - start_time,
                        )

                    # Validate with moderator using imported utility function
                    moderator_result, moderator_output, moderator_metadata = validate_with_moderator(
                        task_name, task_content, worker_output, progress_file, root_dir, attempt_num, self.session_id, self.prompts_dir, self.cli
                    )

                    attempts.append(
                        UnifiedExecutionAttempt(
                            attempt_number=attempt_num,
                            worker_output=worker_output,
                            moderator_output=moderator_output,
                            timestamp=datetime.now(),
                            duration=attempt_duration,
                            worker_metadata=worker_metadata,
                            moderator_metadata=moderator_metadata,
                        )
                    )

                    if moderator_result["status"] == "pass":
                        return UnifiedExecutionResult(
                            item_path=task_file,
                            status="completed",
                            attempts=attempts,
                            total_duration=time.time() - start_time,
                        )

                    # Moderator failed - retry with feedback
                    failure_reason = moderator_result["reason"] if moderator_result["reason"] else "Validation failed"
                    additional_context = f"PREVIOUS ATTEMPT FAILED VALIDATION:\n{failure_reason}\n\nPlease fix the issues and try again."

                    with progress_file.open("a") as f:
                        f.write(f"❌ Validation failed: {failure_reason}\n\n")
                    continue

                # No completion marker - worker didn't finish properly
                attempts.append(
                    UnifiedExecutionAttempt(
                        attempt_number=attempt_num,
                        worker_output=worker_output,
                        moderator_output=None,
                        timestamp=datetime.now(),
                        duration=attempt_duration,
                        worker_metadata=worker_metadata,
                        moderator_metadata=None,
                    )
                )

                additional_context = (
                    "PREVIOUS ATTEMPT DID NOT OUTPUT COMPLETION MARKER.\n"
                    "You MUST output either 'WORK DONE' or 'FEEDBACK: <questions>' "
                    "at the end of your response."
                )

                with progress_file.open("a") as f:
                    f.write("⚠️ No completion marker found\n\n")
                continue

            # Timeout reached
            return UnifiedExecutionResult(
                item_path=task_file,
                status="timeout",
                attempts=attempts,
                total_duration=time.time() - start_time,
                error=f"Task timed out after {timeout}s",
            )

        except Exception as e:
            self.logger.error(
                "task_error",
                task=task_name,
                error=str(e),
            )

            return UnifiedExecutionResult(
                item_path=task_file,
                status="failed",
                attempts=attempts,
                total_duration=time.time() - start_time,
                error=str(e),
            )

        finally:
            # Always unlock task file (if locking was enabled)
            if file_locking_enabled:
                self.file_lock_manager.unlock_file(task_file)

            # Final progress update
            with progress_file.open("a") as f:
                f.write(f"\nCompleted: {datetime.now()}\n")
