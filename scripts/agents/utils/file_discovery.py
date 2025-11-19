"""File discovery utilities for task execution."""

import fnmatch
from pathlib import Path
from typing import cast

from loguru import logger

from scripts.agents.config import get_config


def get_exclude_patterns() -> list[str]:
    """Get task file exclude patterns from config."""
    config = get_config()
    return cast(
        list[str],
        config.get(
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


def is_file_excluded(file_path: Path, exclude_patterns: list[str]) -> bool:
    """Check if file matches any exclude pattern.

    Args:
        file_path: Path to check
        exclude_patterns: List of exclude patterns

    Returns:
        True if file should be excluded
    """
    return any(file_path.match(exclude_pattern) or fnmatch.fnmatch(str(file_path), exclude_pattern) for exclude_pattern in exclude_patterns)


def find_files_in_directory(path: Path, exclude_patterns: list[str]) -> list[Path]:
    """Find task files in directory.

    Args:
        path: Directory to search
        exclude_patterns: Patterns to exclude

    Returns:
        List of task file paths
    """
    config = get_config()
    include_patterns = config.get("tasks.include_patterns", ["**/*.md"])
    task_files = []

    for pattern in include_patterns:
        for file_path in path.glob(pattern):
            if file_path.is_file() and not is_file_excluded(file_path, exclude_patterns):
                task_files.append(file_path)

    return sorted(task_files)


def find_task_files(path: Path) -> list[Path]:
    """Find task file(s) from path.

    Args:
        path: Path to .md task file OR directory to search

    Returns:
        List of task file paths
    """

    exclude_patterns = get_exclude_patterns()

    # Handle single file
    if path.is_file():
        if path.suffix != ".md":
            logger.warning("task_file_not_markdown", file=str(path))
            return []

        if is_file_excluded(path, exclude_patterns):
            logger.warning("task_file_excluded", file=str(path))
            return []

        return [path]

    # Handle directory
    if not path.is_dir():
        logger.error("invalid_path", path=str(path))
        return []

    return find_files_in_directory(path, exclude_patterns)
