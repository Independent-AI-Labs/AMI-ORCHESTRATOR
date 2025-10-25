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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from .agent_cli import AgentConfigPresets, get_agent_cli
from .config import get_config
from .logger import get_logger


@dataclass
class TaskAttempt:
    """Single task execution attempt."""

    attempt_number: int
    worker_output: str
    moderator_output: str | None
    timestamp: datetime
    duration: float


@dataclass
class TaskResult:
    """Result of task execution."""

    task_file: Path
    status: Literal["completed", "feedback", "failed", "timeout"]
    attempts: list[TaskAttempt] = field(default_factory=list)
    feedback: str | None = None
    total_duration: float = 0.0
    error: str | None = None


class TaskExecutor:
    """Executes .md task files using worker and moderator agents."""

    def __init__(self) -> None:
        """Initialize task executor.

        Raises:
            RuntimeError: If AMI_SUDO_PASSWORD environment variable not set
        """
        self.config = get_config()
        self.logger = get_logger("tasks")
        self.cli = get_agent_cli()

        # Validate sudo password is available
        self.sudo_password = os.environ.get("AMI_SUDO_PASSWORD")
        if not self.sudo_password:
            raise RuntimeError("AMI_SUDO_PASSWORD environment variable must be set for task execution. This password is required for file locking with chattr.")

    def execute_tasks(
        self,
        directory: Path,
        parallel: bool = False,
        root_dir: Path | None = None,
        user_instruction: str | None = None,
    ) -> list[TaskResult]:
        """Execute all task files in directory.

        Args:
            directory: Directory containing .md task files
            parallel: Enable parallel execution (async mode)
            root_dir: Root directory where tasks execute (defaults to current directory)
            user_instruction: Optional prepended instruction for all tasks

        Returns:
            List of task results
        """
        if parallel:
            return asyncio.run(self._execute_async(directory, root_dir, user_instruction))
        return self._execute_sync(directory, root_dir, user_instruction)

    def _execute_sync(self, directory: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> list[TaskResult]:
        """Execute tasks sequentially (sync mode).

        Args:
            directory: Directory containing .md task files
            root_dir: Root directory where tasks execute (defaults to current directory)
            user_instruction: Optional prepended instruction for all tasks

        Returns:
            List of task results
        """
        task_files = self._find_task_files(directory)

        self.logger.info(
            "task_execution_started",
            directory=str(directory),
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

        return results

    async def _execute_async(self, directory: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> list[TaskResult]:
        """Execute tasks in parallel (async mode).

        Args:
            directory: Directory containing .md task files
            root_dir: Root directory where tasks execute (defaults to current directory)
            user_instruction: Optional prepended instruction for all tasks

        Returns:
            List of task results
        """
        from base.backend.workers.manager import WorkerPoolManager
        from base.backend.workers.types import PoolConfig, PoolType

        task_files = self._find_task_files(directory)
        workers = self.config.get("tasks.workers", 4)

        self.logger.info(
            "task_execution_started",
            directory=str(directory),
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
        attempts = []
        timeout = self.config.get("tasks.timeout_per_task", 3600)
        moderator_enabled = self.config.get("tasks.moderator_enabled", True)

        # Create progress file
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        task_name = task_file.stem
        progress_file = task_file.parent / f"progress-{timestamp_str}-{task_name}.md"

        try:
            # Lock task file
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

                self.logger.info(
                    "worker_attempt",
                    task=task_name,
                    attempt=attempt_num,
                )

                # Update progress
                with progress_file.open("a") as f:
                    f.write(f"## Attempt {attempt_num} ({datetime.now()})\n\n")

                # Build worker instruction
                worker_instruction = ""
                if user_instruction:
                    worker_instruction = f"{user_instruction}\n\n"
                worker_instruction += task_content
                if additional_context:
                    worker_instruction += f"\n\n{additional_context}"

                # Execute worker
                worker_output = self.cli.run_print(
                    instruction=worker_instruction,
                    stdin="",
                    agent_config=AgentConfigPresets.task_worker(),
                    cwd=root_dir,
                )

                attempt_duration = time.time() - attempt_start

                # Update progress
                with progress_file.open("a") as f:
                    f.write(f"Worker output:\n```\n{worker_output}\n```\n\n")

                # Parse worker output
                completion_marker = self._parse_completion_marker(worker_output)

                if completion_marker["type"] == "feedback":
                    # Worker needs feedback - write feedback file and stop
                    feedback_file = task_file.parent / f"feedback-{timestamp_str}-{task_name}.md"
                    feedback_file.write_text(f"# Feedback Request: {task_name}\n\n{completion_marker['content']}\n")

                    attempts.append(
                        TaskAttempt(
                            attempt_number=attempt_num,
                            worker_output=worker_output,
                            moderator_output=None,
                            timestamp=datetime.now(),
                            duration=attempt_duration,
                        )
                    )

                    return TaskResult(
                        task_file=task_file,
                        status="feedback",
                        attempts=attempts,
                        feedback=completion_marker["content"],
                        total_duration=time.time() - start_time,
                    )

                if completion_marker["type"] == "work_done":
                    # Worker claims completion - validate with moderator
                    if not moderator_enabled:
                        # No moderator, accept worker's claim
                        attempts.append(
                            TaskAttempt(
                                attempt_number=attempt_num,
                                worker_output=worker_output,
                                moderator_output=None,
                                timestamp=datetime.now(),
                                duration=attempt_duration,
                            )
                        )

                        return TaskResult(
                            task_file=task_file,
                            status="completed",
                            attempts=attempts,
                            total_duration=time.time() - start_time,
                        )

                    # Run moderator
                    moderator_start = time.time()
                    self.logger.info(
                        "moderator_check_started",
                        task=task_name,
                        attempt=attempt_num,
                    )

                    with progress_file.open("a") as f:
                        f.write("### Moderator Validation\n\n")

                    moderator_instruction = (
                        f"ORIGINAL TASK:\n{task_content}\n\nWORKER OUTPUT:\n{worker_output}\n\nValidate if the task was completed correctly."
                    )

                    moderator_output = self.cli.run_print(
                        instruction=moderator_instruction,
                        stdin="",
                        agent_config=AgentConfigPresets.task_moderator(),
                        cwd=root_dir,
                    )

                    moderator_duration = time.time() - moderator_start
                    self.logger.info(
                        "moderator_check_completed",
                        task=task_name,
                        attempt=attempt_num,
                        duration=round(moderator_duration, 1),
                    )

                    # Update progress
                    with progress_file.open("a") as f:
                        f.write(f"Moderator output:\n```\n{moderator_output}\n```\n\n")

                    # Parse moderator output
                    moderator_result = self._parse_moderator_result(moderator_output)

                    attempts.append(
                        TaskAttempt(
                            attempt_number=attempt_num,
                            worker_output=worker_output,
                            moderator_output=moderator_output,
                            timestamp=datetime.now(),
                            duration=attempt_duration,
                        )
                    )

                    if moderator_result["status"] == "pass":
                        # Task completed successfully
                        return TaskResult(
                            task_file=task_file,
                            status="completed",
                            attempts=attempts,
                            total_duration=time.time() - start_time,
                        )
                    # Moderator failed - retry with feedback
                    additional_context = f"PREVIOUS ATTEMPT FAILED VALIDATION:\n{moderator_result['reason']}\n\nPlease fix the issues and try again."

                    with progress_file.open("a") as f:
                        f.write(f"❌ Validation failed: {moderator_result['reason']}\n\n")

                    # Continue retry loop
                    continue

                # No completion marker - worker didn't finish properly
                attempts.append(
                    TaskAttempt(
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

                with progress_file.open("a") as f:
                    f.write("⚠️ No completion marker found\n\n")

                # Continue retry loop
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
            # Always unlock task file
            self._unlock_file(task_file)

            # Final progress update
            with progress_file.open("a") as f:
                f.write(f"\nCompleted: {datetime.now()}\n")

    def _find_task_files(self, directory: Path) -> list[Path]:
        """Find all .md task files in directory.

        Args:
            directory: Directory to search

        Returns:
            List of task file paths
        """
        include_patterns = self.config.get("tasks.include_patterns", ["**/*.md"])
        exclude_patterns = self.config.get(
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
            ],
        )

        task_files = []

        for pattern in include_patterns:
            for file_path in directory.glob(pattern):
                # Check exclusions
                excluded = False
                for exclude_pattern in exclude_patterns:
                    if fnmatch.fnmatch(str(file_path), exclude_pattern):
                        excluded = True
                        break

                if not excluded and file_path.is_file():
                    task_files.append(file_path)

        return sorted(task_files)

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
            Dict with status and reason
        """
        # Check for "PASS"
        if "PASS" in output:
            return {"status": "pass", "reason": None}

        # Check for "FAIL: xxx"
        fail_match = re.search(r"FAIL:\s*(.+)", output, re.DOTALL)
        if fail_match:
            return {"status": "fail", "reason": fail_match.group(1).strip()}

        # Default to fail if unclear
        return {"status": "fail", "reason": "Moderator output unclear"}

    def _lock_file(self, file_path: Path) -> None:
        """Lock file using chattr +i with sudo password injection.

        Args:
            file_path: File to lock

        Raises:
            subprocess.CalledProcessError: If chattr command fails
        """
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
            raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)

        self.logger.info("file_locked", file=str(file_path))

    def _unlock_file(self, file_path: Path) -> None:
        """Unlock file using chattr -i with sudo password injection.

        Args:
            file_path: File to unlock

        Raises:
            subprocess.CalledProcessError: If chattr command fails
        """
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
