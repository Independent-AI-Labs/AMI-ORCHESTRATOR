"""Utilities for result processing.

This module contains result processing-related utilities extracted from utils.py
to reduce code size and improve maintainability.
"""

from scripts.agents.core.models import UnifiedExecutionResult


def process_execution_results(results: list[UnifiedExecutionResult], failure_statuses: list[str] | None = None) -> int:
    """Process execution results and return appropriate exit code.

    Args:
        results: List of result objects with status attribute
        failure_statuses: List of statuses that indicate failure (default: ["failed", "timeout", "ERROR"])

    Returns:
        0 if no failures, 1 if any failures found
    """
    if failure_statuses is None:
        failure_statuses = ["failed", "timeout", "ERROR"]

    failure_count = sum(1 for r in results if r.status in failure_statuses)
    return 1 if failure_count > 0 else 0


def count_status_types(results: list[UnifiedExecutionResult], status_types: list[str]) -> dict[str, int]:
    """Count occurrences of specific status types in results.

    Args:
        results: List of result objects with status attribute
        status_types: List of status types to count

    Returns:
        Dictionary with status names as keys and counts as values
    """
    counts = {}
    for status_type in status_types:
        counts[status_type] = sum(1 for r in results if r.status == status_type)
    return counts
