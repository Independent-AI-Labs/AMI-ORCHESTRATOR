"""Universal task executor for .md task files.

Orchestrates worker agents to execute tasks, moderator agents to validate,
and retry loops with timeout. Supports both sync (default) and async parallel modes.
"""

import asyncio
import fnmatch
import os
import re
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, Field

from .agent_cli import AgentConfigPresets, get_agent_cli
from .config import get_config
from .logger import get_logger


class TaskAttempt(BaseModel):
    """Single task execution attempt."""

    attempt_number: int
    worker_output: str
    moderator_output: str | None
    timestamp: datetime
    duration: float
    worker_metadata: dict[str, Any] | None = None  # Claude execution metadata for worker
    moderator_metadata: dict[str, Any] | None = None  # Claude execution metadata for moderator


class TaskResult(BaseModel):
    """Result of task execution."""

    task_file: Path
    status: Literal["completed", "feedback", "failed", "timeout"]
    attempts: list[TaskAttempt] = Field(default_factory=list)
    feedback: str | None = None
    total_duration: float = 0.0
    error: str | None = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class TaskExecutor:
    """Executes .md task files using worker and moderator agents."""

    def __init__(self) -> None:
        """Initialize task executor.

        Raises:
            RuntimeError: If AMI_SUDO_PASSWORD environment variable not set and file locking enabled
        """
        self.config = get_config()
        self.session_id = str(uuid.uuid4())
        self.logger = get_logger("tasks", session_id=self.session_id)
        self.cli = get_agent_cli()
        self.prompts_dir = self.config.root / self.config.get("prompts.dir")

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

    def execute_tasks(
        self,
        path: Path,
        parallel: bool = False,
        root_dir: Path | None = None,
        user_instruction: str | None = None,
    ) -> list[TaskResult]:
        """Execute task file(s).

        Args:
            path: Path to .md task file OR directory containing task files
            parallel: Enable parallel execution (async mode)
            root_dir: Root directory where tasks execute (defaults to current directory)
            user_instruction: Optional prepended instruction for all tasks

        Returns:
            List of task results
        """
        if parallel:
            return asyncio.run(self._execute_async(path, root_dir, user_instruction))
        return self._execute_sync(path, root_dir, user_instruction)

    def _execute_sync(self, path: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> list[TaskResult]:
        """Execute tasks sequentially (sync mode).

        Args:
            path: Path to .md task file OR directory containing task files
            root_dir: Root directory where tasks execute (defaults to current directory)
            user_instruction: Optional prepended instruction for all tasks

        Returns:
            List of task results
        """
        task_files = self._find_task_files(path)

        self.logger.info(
            "task_execution_started",
            path=str(path),
            is_single_file=path.is_file(),
            task_count=len(task_files),
            mode="sync",
            root_dir=str(root_dir) if root_dir else None,
            user_instruction=bool(user_instruction),
        )

        results = []
        for task_file in task_files:
            result = self._execute_single_task(task_file, root_dir, user_instruction)
            results.append(result)

            self.logger.info(
                "task_completed",
                task=task_file.name,
                status=result.status,
                attempts=len(result.attempts),
                duration=result.total_duration,
            )

            # Display metadata
            self._display_task_metadata(task_file.stem, result.attempts)

        return results

    async def _execute_async(self, path: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> list[TaskResult]:
        """Execute tasks in parallel (async mode).

        Args:
            path: Path to .md task file OR directory containing task files
            root_dir: Root directory where tasks execute (defaults to current directory)
            user_instruction: Optional prepended instruction for all tasks

        Returns:
            List of task results
        """
        from base.backend.workers.manager import WorkerPoolManager
        from base.backend.workers.types import PoolConfig, PoolType

        task_files = self._find_task_files(path)
        workers = self.config.get("tasks.workers", 4)

        self.logger.info(
            "task_execution_started",
            path=str(path),
            is_single_file=path.is_file(),
            task_count=len(task_files),
            mode="async",
            workers=workers,
            root_dir=str(root_dir) if root_dir else None,
            user_instruction=bool(user_instruction),
        )

        # Create thread pool for I/O-bound task execution
        pool_config = PoolConfig(
            name="task-executor",
            pool_type=PoolType.THREAD,
            min_workers=1,
            max_workers=workers,
        )

        manager = WorkerPoolManager()
        pool = await manager.create_pool(pool_config)

        try:
            # Submit all tasks
            task_ids = []
            for task_file in task_files:
                task_id = await pool.submit(self._execute_single_task, task_file, root_dir, user_instruction)
                task_ids.append(task_id)

            # Collect results
            results = []
            for task_id in task_ids:
                try:
                    result = await pool.get_result(task_id, timeout=None)
                    results.append(result)

                    self.logger.info(
                        "task_completed",
                        task=result.task_file.name,
                        status=result.status,
                        attempts=len(result.attempts),
                        duration=result.total_duration,
                    )

                    # Display metadata
                    self._display_task_metadata(result.task_file.stem, result.attempts)
                except Exception as e:
                    self.logger.error(
                        "task_result_retrieval_error",
                        task_id=task_id,
                        error=str(e),
                    )
                    raise

            return results

        finally:
            await pool.shutdown()

    def _handle_feedback_result(
        self,
        task_file: Path,
        task_name: str,
        timestamp_str: str,
        completion_marker: dict[str, str],
        attempts: list[TaskAttempt],
        attempt_num: int,
        worker_output: str,
        worker_metadata: dict[str, Any] | None,
        attempt_duration: float,
        start_time: float,
    ) -> TaskResult:
        """Handle worker feedback request.

        Args:
            task_file: Task file path
            task_name: Task name
            timestamp_str: Timestamp string for file naming
            completion_marker: Parsed completion marker
            attempts: List of attempts so far
            attempt_num: Current attempt number
            worker_output: Worker output text
            attempt_duration: Duration of this attempt
            start_time: Task start time

        Returns:
            TaskResult with feedback status
        """
        feedback_file = task_file.parent / f"feedback-{timestamp_str}-{task_name}.md"
        feedback_file.write_text(f"# Feedback Request: {task_name}\n\n{completion_marker['content']}\n")

        attempts.append(
            TaskAttempt(
                attempt_number=attempt_num,
                worker_output=worker_output,
                moderator_output=None,
                timestamp=datetime.now(),
                duration=attempt_duration,
                worker_metadata=worker_metadata,
                moderator_metadata=None,
            )
        )

        return TaskResult(
            task_file=task_file,
            status="feedback",
            attempts=attempts,
            feedback=completion_marker["content"],
            total_duration=time.time() - start_time,
        )

    def _validate_with_moderator(
        self,
        task_name: str,
        task_content: str,
        worker_output: str,
        progress_file: Path,
        root_dir: Path | None,
        attempt_num: int,
    ) -> tuple[dict[str, Any], str, dict[str, Any] | None]:
        """Run moderator validation on worker output.

        Args:
            task_name: Task name
            task_content: Original task content
            worker_output: Worker output to validate
            progress_file: Progress file to update
            root_dir: Working directory
            attempt_num: Current attempt number

        Returns:
            Tuple of (moderator_result dict, moderator_output text, moderator_metadata dict or None)
        """
        moderator_start = time.time()
        self.logger.info("moderator_check_started", task=task_name, attempt=attempt_num)

        with progress_file.open("a") as f:
            f.write("### Moderator Validation\n\n")

        moderator_prompt = self.prompts_dir / "task_moderator.txt"
        validation_context = f"""ORIGINAL TASK:
{task_content}

WORKER OUTPUT:
{worker_output}

Validate if the task was completed correctly."""

        moderator_config = AgentConfigPresets.task_moderator(self.session_id)
        moderator_config.enable_streaming = True
        moderator_output, moderator_metadata = self.cli.run_print(
            instruction_file=moderator_prompt,
            stdin=validation_context,
            agent_config=moderator_config,
            cwd=root_dir,
        )

        moderator_result = self._parse_moderator_result(moderator_output)
        moderator_duration = time.time() - moderator_start
        self.logger.info(
            "moderator_check_completed",
            task=task_name,
            attempt=attempt_num,
            duration=round(moderator_duration, 1),
            final_status=moderator_result["status"],
        )

        with progress_file.open("a") as f:
            f.write(f"Moderator output:\n```\n{moderator_output}\n```\n\n")

        return moderator_result, moderator_output, moderator_metadata

    def _execute_worker_attempt(
        self,
        task_name: str,
        task_content: str,
        user_instruction: str | None,
        additional_context: str,
        root_dir: Path | None,
        progress_file: Path,
        attempt_num: int,
    ) -> tuple[str, dict[str, Any] | None]:
        """Execute single worker attempt.

        Args:
            task_name: Task name
            task_content: Task content
            user_instruction: Optional user instruction
            additional_context: Additional context from previous attempts
            root_dir: Root directory
            progress_file: Progress file to update
            attempt_num: Current attempt number

        Returns:
            Tuple of (worker output text, execution metadata or None)
        """
        self.logger.info("worker_attempt", task=task_name, attempt=attempt_num)

        with progress_file.open("a") as f:
            f.write(f"## Attempt {attempt_num} ({datetime.now()})\n\n")

        # Build worker context (task content passed via stdin, just like moderator)
        worker_context = ""
        if user_instruction:
            worker_context = f"{user_instruction}\n\n"
        worker_context += task_content
        if additional_context:
            worker_context += f"\n\n{additional_context}"

        # Execute worker with prompt file (matches moderator pattern)
        worker_prompt = self.prompts_dir / "task_worker.txt"
        worker_config = AgentConfigPresets.task_worker(self.session_id)
        worker_config.enable_streaming = True
        worker_output, worker_metadata = self.cli.run_print(
            instruction_file=worker_prompt,
            stdin=worker_context,
            agent_config=worker_config,
            cwd=root_dir,
        )
        return worker_output, worker_metadata

    def _execute_single_task(self, task_file: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> TaskResult:
        """Execute a single task with retry loop.

        Args:
            task_file: Path to .md task file
            root_dir: Root directory where tasks execute (defaults to current directory)
            user_instruction: Optional prepended instruction

        Returns:
            Task result
        """
        start_time = time.time()
        attempts: list[TaskAttempt] = []
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
                self._lock_file(task_file)

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

                # Execute worker
                worker_output, worker_metadata = self._execute_worker_attempt(
                    task_name, task_content, user_instruction, additional_context, root_dir, progress_file, attempt_num
                )

                attempt_duration = time.time() - attempt_start

                # Update progress
                with progress_file.open("a") as f:
                    f.write(f"Worker output:\n```\n{worker_output}\n```\n\n")

                # Parse worker output
                completion_marker = self._parse_completion_marker(worker_output)

                if completion_marker["type"] == "feedback":
                    return self._handle_feedback_result(
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
                            TaskAttempt(
                                attempt_number=attempt_num,
                                worker_output=worker_output,
                                moderator_output=None,
                                timestamp=datetime.now(),
                                duration=attempt_duration,
                                worker_metadata=worker_metadata,
                                moderator_metadata=None,
                            )
                        )
                        return TaskResult(
                            task_file=task_file,
                            status="completed",
                            attempts=attempts,
                            total_duration=time.time() - start_time,
                        )

                    # Validate with moderator
                    moderator_result, moderator_output, moderator_metadata = self._validate_with_moderator(
                        task_name, task_content, worker_output, progress_file, root_dir, attempt_num
                    )

                    attempts.append(
                        TaskAttempt(
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
                        return TaskResult(
                            task_file=task_file,
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
                    TaskAttempt(
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
            return TaskResult(
                task_file=task_file,
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

            return TaskResult(
                task_file=task_file,
                status="failed",
                attempts=attempts,
                total_duration=time.time() - start_time,
                error=str(e),
            )

        finally:
            # Always unlock task file (if locking was enabled)
            if file_locking_enabled:
                self._unlock_file(task_file)

            # Final progress update
            with progress_file.open("a") as f:
                f.write(f"\nCompleted: {datetime.now()}\n")

    def _get_exclude_patterns(self) -> list[str]:
        """Get task file exclude patterns from config."""
        return cast(
            list[str],
            self.config.get(
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
            ),
        )

    def _is_file_excluded(self, file_path: Path, exclude_patterns: list[str]) -> bool:
        """Check if file matches any exclude pattern.

        Args:
            file_path: Path to check
            exclude_patterns: List of exclude patterns

        Returns:
            True if file should be excluded
        """
        return any(file_path.match(exclude_pattern) or fnmatch.fnmatch(str(file_path), exclude_pattern) for exclude_pattern in exclude_patterns)

    def _find_files_in_directory(self, path: Path, exclude_patterns: list[str]) -> list[Path]:
        """Find task files in directory.

        Args:
            path: Directory to search
            exclude_patterns: Patterns to exclude

        Returns:
            List of task file paths
        """
        include_patterns = self.config.get("tasks.include_patterns", ["**/*.md"])
        task_files = []

        for pattern in include_patterns:
            for file_path in path.glob(pattern):
                if file_path.is_file() and not self._is_file_excluded(file_path, exclude_patterns):
                    task_files.append(file_path)

        return sorted(task_files)

    def _find_task_files(self, path: Path) -> list[Path]:
        """Find task file(s) from path.

        Args:
            path: Path to .md task file OR directory to search

        Returns:
            List of task file paths
        """
        exclude_patterns = self._get_exclude_patterns()

        # Handle single file
        if path.is_file():
            if path.suffix != ".md":
                self.logger.warning("task_file_not_markdown", file=str(path))
                return []

            if self._is_file_excluded(path, exclude_patterns):
                self.logger.warning("task_file_excluded", file=str(path))
                return []

            return [path]

        # Handle directory
        if not path.is_dir():
            self.logger.error("invalid_path", path=str(path))
            return []

        return self._find_files_in_directory(path, exclude_patterns)

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

    def _display_task_metadata(self, task_name: str, attempts: list[TaskAttempt]) -> None:
        """Display aggregated metadata for a task.

        Args:
            task_name: Name of the task
            attempts: List of task attempts with metadata
        """
        total_cost = 0.0
        total_duration_ms = 0.0
        total_api_ms = 0.0
        total_turns = 0

        for attempt in attempts:
            # Worker metadata
            if attempt.worker_metadata:
                total_cost += attempt.worker_metadata.get("cost_usd", 0) or 0
                total_duration_ms += attempt.worker_metadata.get("duration_ms", 0) or 0
                total_api_ms += attempt.worker_metadata.get("duration_api_ms", 0) or 0
                total_turns += attempt.worker_metadata.get("num_turns", 0) or 0

            # Moderator metadata
            if attempt.moderator_metadata:
                total_cost += attempt.moderator_metadata.get("cost_usd", 0) or 0
                total_duration_ms += attempt.moderator_metadata.get("duration_ms", 0) or 0
                total_api_ms += attempt.moderator_metadata.get("duration_api_ms", 0) or 0
                total_turns += attempt.moderator_metadata.get("num_turns", 0) or 0

        # Only display if we have any metadata
        if total_cost > 0 or total_turns > 0:
            print(f"\n{'=' * 60}")
            print(f"Task Metadata: {task_name}")
            print(f"{'=' * 60}")
            print(f"Total Cost:         ${total_cost:.4f}")
            print(f"Total Duration:     {total_duration_ms / 1000:.1f}s")
            print(f"API Duration:       {total_api_ms / 1000:.1f}s")
            print(f"Total Turns:        {total_turns}")
            print(f"{'=' * 60}\n")

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

    def _filesystem_supports_chattr(self, file_path: Path) -> bool:
        """Check if filesystem supports chattr by getting mount point.

        Args:
            file_path: File to check

        Returns:
            True if chattr is supported, False otherwise
        """
        # Get absolute resolved path
        abs_path = file_path.resolve()

        # Find mount point by walking up the directory tree
        current = abs_path
        while current != current.parent:
            if str(current) in self._unsupported_filesystems:
                return False
            current = current.parent

        # Check root too
        return str(current) not in self._unsupported_filesystems

    def _mark_filesystem_unsupported(self, file_path: Path) -> None:
        """Mark a filesystem as not supporting chattr.

        Args:
            file_path: File on the unsupported filesystem
        """
        # Get the directory (mount point will be a parent)
        current = file_path.resolve().parent
        self._unsupported_filesystems.add(str(current))
        self.logger.info("filesystem_chattr_unsupported", path=str(current))

    def _lock_file(self, file_path: Path) -> None:
        """Lock file using chattr +i with sudo password injection.

        Args:
            file_path: File to lock

        Raises:
            subprocess.CalledProcessError: If chattr command fails
        """
        # Skip if filesystem doesn't support chattr
        if not self._filesystem_supports_chattr(file_path):
            return

        if self.is_root:
            # Already running as root, no sudo needed
            cmd = ["chattr", "+i", str(file_path)]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if result.returncode != 0:
                # Check if filesystem doesn't support it
                if "Operation not supported" in result.stderr:
                    self._mark_filesystem_unsupported(file_path)
                    return
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        else:
            # Not root, use sudo with password
            cmd = ["sudo", "-S", "chattr", "+i", str(file_path)]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=f"{self.sudo_password}\n")

            if process.returncode != 0:
                # Check if filesystem doesn't support it
                if "Operation not supported" in stderr:
                    self._mark_filesystem_unsupported(file_path)
                    return
                raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)

        self.logger.info("file_locked", file=str(file_path))

    def _unlock_file(self, file_path: Path) -> None:
        """Unlock file using chattr -i with sudo password injection.

        Args:
            file_path: File to unlock

        Raises:
            subprocess.CalledProcessError: If chattr command fails
        """
        if self.is_root:
            # Already running as root, no sudo needed
            cmd = ["chattr", "-i", str(file_path)]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(
                    "file_unlock_error",
                    file=str(file_path),
                    returncode=result.returncode,
                    stderr=result.stderr,
                )
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        else:
            # Not root, use sudo with password
            cmd = ["sudo", "-S", "chattr", "-i", str(file_path)]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=f"{self.sudo_password}\n")

            if process.returncode != 0:
                self.logger.error(
                    "file_unlock_error",
                    file=str(file_path),
                    returncode=process.returncode,
                    stderr=stderr,
                )
                raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)
