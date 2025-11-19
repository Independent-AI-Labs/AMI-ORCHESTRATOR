"""Utilities for streaming and timeout management.

This module contains streaming and timeout-related utilities extracted from utils.py
to reduce code size and improve maintainability.
"""

from datetime import datetime
from pathlib import Path


def calculate_timeout(base_timeout: int | float | None, line_count: int) -> float:
    """Calculate timeout for the next streaming line.

    Args:
        base_timeout: Base timeout value
        line_count: Current line number

    Returns:
        Timeout value in seconds
    """
    # Use the base timeout if set, otherwise default to 30s
    effective_timeout = base_timeout or 30

    # Define constant for initial line count threshold
    initial_line_threshold = 5

    # For the first few lines, we might want shorter timeouts
    if line_count < initial_line_threshold:
        return min(10.0, effective_timeout / 2)  # 10s or half of base timeout

    # For ongoing stream, use the base timeout
    return float(effective_timeout)


def load_instruction_with_replacements(instruction_file: Path) -> str:
    """Load instruction from file with pattern replacement.

    Args:
        instruction_file: Path to instruction file

    Returns:
        Loaded instruction with patterns replaced
    """

    content = instruction_file.read_text()

    # Replace patterns templates if they exist
    if "{PATTERNS}" in content:
        patterns_file = instruction_file.parent / "patterns_core.txt"
        if patterns_file.exists():
            patterns_content = patterns_file.read_text()
            content = content.replace("{PATTERNS}", patterns_content)

    # Use str.replace() instead of .format() to avoid conflicts with code examples containing braces
    return content.replace("{date}", datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"))
