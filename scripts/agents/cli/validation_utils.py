"""Utilities for validation.

This module contains validation-related utilities extracted from utils.py
to reduce code size and improve maintainability.
"""

from pathlib import Path


def validate_path_exists(path: str | Path) -> bool:
    """Validate that a given path exists.

    Args:
        path: Path to validate

    Returns:
        True if path exists, False otherwise
    """
    path_obj = Path(path)
    return path_obj.exists()


def validate_path_and_return_code(path: str | Path | None) -> int:
    """Validate that a path exists and return exit code.

    Args:
        path: Path to validate

    Returns:
        1 if path doesn't exist or is None, 0 if it exists
    """
    if path is None:
        return 1

    path_obj = Path(path)
    return 0 if path_obj.exists() else 1
