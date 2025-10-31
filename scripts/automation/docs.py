"""Documentation maintenance executor for .md documentation files.

Orchestrates worker agents to maintain docs (UPDATE/ARCHIVE/DELETE),
moderator agents to validate, and retry loops with timeout.
Supports both sync (default) and async parallel modes.
"""

import asyncio
import fnmatch
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from base.backend.workers.manager import WorkerPoolManager
from base.backend.workers.types import PoolConfig, PoolType
from scripts.automation.agent_cli import AgentConfigPresets, get_agent_cli
from scripts.automation.config import get_config
from scripts.automation.logger import get_logger


class DocAttempt(BaseModel):
    """Single documentation maintenance attempt."""

    attempt_number: int
    worker_output: str
    moderator_output: str | None
    timestamp: datetime
    duration: float


class DocResult(BaseModel):
    """Result of documentation maintenance."""

    doc_file: Path
    status: Literal["completed", "feedback", "failed", "timeout"]
    action: Literal["UPDATE", "ARCHIVE", "DELETE"] | None
    attempts: list[DocAttempt] = Field(default_factory=list)
    feedback: str | None = None
    total_duration: float = 0.0
    error: str | None = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class DocsExecutor:
    """Maintains .md documentation files using worker and moderator agents."""

    def __init__(self) -> None:
        """Initialize docs executor."""
        self.config = get_config()
        self.session_id = str(uuid.uuid4())
        self.logger = get_logger("docs", session_id=self.session_id)
        self.cli = get_agent_cli()
        self.prompts_dir = self.config.root / self.config.get("prompts.dir")

    def execute_docs(
        self,
        directory: Path,
        parallel: bool = False,
        root_dir: Path | None = None,
    ) -> list[DocResult]:
        """Execute documentation maintenance for all .md files in directory.

        Args:
            directory: Directory containing .md documentation files
            parallel: Enable parallel execution (async mode)
            root_dir: Root directory for codebase inspection (defaults to current directory)

        Returns:
            List of doc results
        """
        if parallel:
            return asyncio.run(self._execute_async(directory, root_dir))
        return self._execute_sync(directory, root_dir)

    def _execute_sync(self, directory: Path, root_dir: Path | None = None) -> list[DocResult]:
        """Execute docs maintenance sequentially (sync mode).

        Args:
            directory: Directory containing .md documentation files
            root_dir: Root directory for codebase inspection (defaults to current directory)

        Returns:
            List of doc results
        """
        doc_files: list[Path] = self._find_doc_files(directory)

        self.logger.info(
            "docs_execution_started",
            directory=str(directory),
            doc_count=len(doc_files),
            mode="sync",
            root_dir=str(root_dir) if root_dir else None,
        )

        results: list[DocResult] = []
        for doc_file in doc_files:
            result: DocResult = self._execute_single_doc(doc_file, root_dir)
            results.append(result)

            self.logger.info(
                "doc_completed",
                doc=doc_file.name,
                status=result.status,
                action=result.action,
                attempts=len(result.attempts),
                duration=result.total_duration,
            )

        return results

    async def _execute_async(self, directory: Path, root_dir: Path | None = None) -> list[DocResult]:
        """Execute docs maintenance in parallel (async mode).

        Args:
            directory: Directory containing .md documentation files
            root_dir: Root directory for codebase inspection (defaults to current directory)

        Returns:
            List of doc results
        """
        doc_files: list[Path] = self._find_doc_files(directory)
        workers: int = self.config.get("docs.workers", 4)

        self.logger.info(
            "docs_execution_started",
            directory=str(directory),
            doc_count=len(doc_files),
            mode="async",
            workers=workers,
            root_dir=str(root_dir) if root_dir else None,
        )

        # Create thread pool for I/O-bound doc maintenance execution
        pool_config: PoolConfig = PoolConfig(
            name="docs-executor",
            pool_type=PoolType.THREAD,
            min_workers=1,
            max_workers=workers,
        )

        manager: WorkerPoolManager = WorkerPoolManager()
        pool = await manager.create_pool(pool_config)

        try:
            # Submit all docs
            task_ids: list[str] = []
            for doc_file in doc_files:
                task_id: str = await pool.submit(self._execute_single_doc, doc_file, root_dir)
                task_ids.append(task_id)

            # Collect results
            results: list[DocResult] = []
            for task_id in task_ids:
                try:
                    result: DocResult = await pool.get_result(task_id, timeout=None)
                    results.append(result)

                    self.logger.info(
                        "doc_completed",
                        doc=result.doc_file.name,
                        status=result.status,
                        action=result.action,
                        attempts=len(result.attempts),
                        duration=result.total_duration,
                    )
                except Exception as e:
                    self.logger.error(
                        "doc_result_retrieval_error",
                        task_id=task_id,
                        error=str(e),
                    )
                    raise

            return results

        finally:
            await pool.shutdown()

    def _execute_single_doc(self, doc_file: Path, root_dir: Path | None = None) -> DocResult:
        """Execute documentation maintenance for a single doc with retry loop.

        Args:
            doc_file: Path to .md documentation file
            root_dir: Root directory for codebase inspection (defaults to current directory)

        Returns:
            Doc result
        """
        start_time: float = time.time()
        attempts: list[DocAttempt] = []
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
            worker_instruction: str = worker_prompt_template.format(
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
                worker_output: str = self.cli.run_print(
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
                        DocAttempt(
                            attempt_number=attempt_num,
                            worker_output=worker_output,
                            moderator_output=None,
                            timestamp=datetime.now(),
                            duration=attempt_duration,
                        )
                    )

                    return DocResult(
                        doc_file=doc_file,
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
                            DocAttempt(
                                attempt_number=attempt_num,
                                worker_output=worker_output,
                                moderator_output=None,
                                timestamp=datetime.now(),
                                duration=attempt_duration,
                            )
                        )

                        return DocResult(
                            doc_file=doc_file,
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
                    moderator_output: str = self.cli.run_print(
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
                        DocAttempt(
                            attempt_number=attempt_num,
                            worker_output=worker_output,
                            moderator_output=moderator_output,
                            timestamp=datetime.now(),
                            duration=attempt_duration,
                        )
                    )

                    if moderator_result["status"] == "pass":
                        # Doc maintenance completed successfully
                        return DocResult(
                            doc_file=doc_file,
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
                    DocAttempt(
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
            return DocResult(
                doc_file=doc_file,
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

            return DocResult(
                doc_file=doc_file,
                status="failed",
                action=None,
                attempts=attempts,
                total_duration=time.time() - start_time,
                error=str(e),
            )

    def _find_doc_files(self, directory: Path) -> list[Path]:
        """Find all .md documentation files in directory.

        Args:
            directory: Directory to search

        Returns:
            List of documentation file paths
        """
        include_patterns: list[str] = self.config.get("docs.include_patterns", ["**/*.md"])
        exclude_patterns: list[str] = self.config.get(
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

        doc_files: list[Path] = []

        for pattern in include_patterns:
            for file_path in directory.glob(pattern):
                # Check exclusions using Path.match() which handles ** correctly
                excluded: bool = False
                for exclude_pattern in exclude_patterns:
                    # Use Path.match for proper glob pattern matching
                    if file_path.match(exclude_pattern) or fnmatch.fnmatch(str(file_path), exclude_pattern):
                        excluded = True
                        break

                if not excluded and file_path.is_file():
                    doc_files.append(file_path)

        return sorted(doc_files)

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
