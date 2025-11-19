"""Common base executor class for LLM-based orchestration tasks.

Security CRITICAL: CACHING IS FORBIDDEN in security-related tasks to ensure real-time analysis.
This module provides a generic framework for orchestrating worker agents,
moderator agents, and retry loops with timeout. Supports both sync and
async parallel modes.
"""

import asyncio
import fnmatch
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

from loguru import logger

from base.backend.utils.uuid_utils import uuid7
from base.backend.workers.manager import WorkerPoolManager
from base.backend.workers.types import PoolConfig, PoolType
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.config import Config, get_config
from scripts.agents.core.constants import COMMON_EXCLUDE_PATTERNS
from scripts.agents.core.models import UnifiedExecutionResult
from scripts.agents.core.utils import parse_completion_marker, parse_moderator_result

T = TypeVar("T", bound=UnifiedExecutionResult)


class BaseExecutor[T: UnifiedExecutionResult](ABC):
    """Abstract base executor for LLM-based orchestration tasks."""

    config: Config

    def __init__(self, result_type: type[T], cli: Any = None) -> None:
        """Initialize base executor.

        Args:
            result_type: The specific UnifiedExecutionResult subclass for this executor
            cli: Optional CLI instance for testing (defaults to get_agent_cli())
        """
        self.result_type = result_type
        self.config = get_config()
        self.session_id = uuid7()
        self.cli = cli or self._get_agent_cli()
        self.prompts_dir = self.config.root / self.config.get("prompts.dir")
        self.logger = logger

    def _get_agent_cli(self) -> Any:  # Return type as Any since we don't have the exact type definition
        """Get the agent CLI instance. Can be overridden by subclasses for testing."""
        return get_agent_cli()

    @abstractmethod
    def get_executor_name(self) -> str:
        """Get the name of this executor for logging purposes."""

    @abstractmethod
    def get_include_patterns(self) -> list[str]:
        """Get the file inclusion patterns for this executor."""

    def get_exclude_patterns(self) -> list[str]:
        """Get the common file exclusion patterns for all executors."""
        result = COMMON_EXCLUDE_PATTERNS
        if self.config is not None:
            config_patterns = self.config.get("common.exclude_patterns", COMMON_EXCLUDE_PATTERNS)
            if isinstance(config_patterns, list):
                result = config_patterns
        return result

    @abstractmethod
    def execute_single_item(self, item_path: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> T:
        """Execute a single item with retry loop.

        Args:
            item_path: Path to the item to execute
            root_dir: Root directory for codebase inspection (defaults to current directory)
            user_instruction: Optional prepended instruction for the worker

        Returns:
            Execution result for the item
        """

    def execute_items(
        self,
        path: Path,
        parallel: bool = False,
        root_dir: Path | None = None,
        user_instruction: str | None = None,
    ) -> list[T]:
        """Execute items from path.

        Args:
            path: Path to item file OR directory containing items
            parallel: Enable parallel execution (async mode)
            root_dir: Root directory for codebase inspection (defaults to current directory)
            user_instruction: Optional prepended instruction for all workers

        Returns:
            List of execution results
        """
        if parallel:
            return asyncio.run(self._execute_async(path, root_dir, user_instruction))
        return self._execute_sync(path, root_dir, user_instruction)

    def _execute_sync(self, path: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> list[T]:
        """Execute items sequentially (sync mode).

        Args:
            path: Path to item file OR directory containing items
            root_dir: Root directory for codebase inspection (defaults to current directory)
            user_instruction: Optional prepended instruction for all workers

        Returns:
            List of execution results
        """
        item_files = self._find_item_files(path)

        self.logger.info(
            "execution_started",
            path=str(path),
            is_single_file=path.is_file(),
            item_count=len(item_files),
            mode="sync",
            root_dir=str(root_dir) if root_dir else None,
            user_instruction=bool(user_instruction),
            session_id=self.session_id,
            executor_name=self.get_executor_name(),
        )

        results = []
        for item_file in item_files:
            result = self.execute_single_item(item_file, root_dir, user_instruction)
            results.append(result)

            self.logger.info(
                "item_completed",
                item=item_file.name,
                status=result.status,
                attempts=len(result.attempts),
                duration=result.total_duration,
                session_id=self.session_id,
                executor_name=self.get_executor_name(),
            )

        return results

    async def _execute_async(self, path: Path, root_dir: Path | None = None, user_instruction: str | None = None) -> list[T]:
        """Execute items in parallel (async mode).

        Args:
            path: Path to item file OR directory containing items
            root_dir: Root directory for codebase inspection (defaults to current directory)
            user_instruction: Optional prepended instruction for all workers

        Returns:
            List of execution results
        """
        item_files = self._find_item_files(path)
        workers = self.config.get("executor.workers", 4)

        self.logger.info(
            "execution_started",
            path=str(path),
            is_single_file=path.is_file(),
            item_count=len(item_files),
            mode="async",
            workers=workers,
            root_dir=str(root_dir) if root_dir else None,
            user_instruction=bool(user_instruction),
            session_id=self.session_id,
            executor_name=self.get_executor_name(),
        )

        # Create thread pool for I/O-bound execution
        pool_config = PoolConfig(
            name="executor",
            pool_type=PoolType.THREAD,
            min_workers=1,
            max_workers=workers,
        )

        manager = WorkerPoolManager()
        pool = await manager.create_pool(pool_config)

        try:
            # Submit all items
            task_ids = []
            for item_file in item_files:
                task_id = await pool.submit(self.execute_single_item, item_file, root_dir, user_instruction)
                task_ids.append(task_id)

            # Collect results
            results = []
            for task_id in task_ids:
                try:
                    result = await pool.get_result(task_id, timeout=None)
                    results.append(result)

                    self.logger.info(
                        "item_completed",
                        item=result.item_path.name,
                        status=result.status,
                        attempts=len(result.attempts),
                        duration=result.total_duration,
                        session_id=self.session_id,
                        executor_name=self.get_executor_name(),
                    )
                except Exception as e:
                    self.logger.error(
                        "item_result_retrieval_error",
                        task_id=task_id,
                        error=str(e),
                        session_id=self.session_id,
                        executor_name=self.get_executor_name(),
                    )
                    raise

            return results

        finally:
            await pool.shutdown()

    def _find_item_files(self, path: Path) -> list[Path]:
        """Find item file(s) from path using include/exclude patterns.

        Args:
            path: Path to item file OR directory to search

        Returns:
            List of item file paths
        """
        include_patterns = self.get_include_patterns()
        exclude_patterns = self.get_exclude_patterns()

        # Handle single file
        if path.is_file():
            if self._has_valid_extension(path):
                if not self._is_file_excluded(path, exclude_patterns):
                    return [path]
                self.logger.warning("item_file_excluded", file=str(path), session_id=self.session_id, executor_name=self.get_executor_name())
                return []
            self.logger.warning("item_file_invalid_extension", file=str(path), session_id=self.session_id, executor_name=self.get_executor_name())
            return []

        # Handle directory
        if not path.is_dir():
            self.logger.error("invalid_path", path=str(path), session_id=self.session_id, executor_name=self.get_executor_name())
            return []

        # Find files in directory
        item_files = []
        for pattern in include_patterns:
            for file_path in path.glob(pattern):
                if file_path.is_file() and not self._is_file_excluded(file_path, exclude_patterns) and self._has_valid_extension(file_path):
                    item_files.append(file_path)

        return sorted(item_files)

    def _has_valid_extension(self, file_path: Path) -> bool:
        """Check if the file has a valid extension for this executor.

        Args:
            file_path: Path to check

        Returns:
            True if file extension is valid
        """
        # Default implementation checks if it's a md file, can be overridden
        return file_path.suffix.lower() == ".md"

    def _is_file_excluded(self, file_path: Path, exclude_patterns: list[str]) -> bool:
        """Check if file matches any exclude pattern.

        Args:
            file_path: Path to check
            exclude_patterns: List of exclude patterns

        Returns:
            True if file should be excluded
        """
        return any(file_path.match(exclude_pattern) or fnmatch.fnmatch(str(file_path), exclude_pattern) for exclude_pattern in exclude_patterns)

    def _parse_completion_marker(self, output: str) -> dict[str, Any]:
        """Parse completion marker from worker output.

        Args:
            output: Worker output text

        Returns:
            Dict with type and content
        """
        return parse_completion_marker(output)

    def _parse_moderator_result(self, output: str) -> dict[str, Any]:
        """Parse moderator validation result.

        Args:
            output: Moderator output text

        Returns:
            Dict with status ('pass' or 'fail') and optional reason
        """
        return parse_moderator_result(output)
