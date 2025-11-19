"""Utilities for subprocess and execution management.

This module contains subprocess and execution-related utilities extracted from utils.py
to reduce code size and improve maintainability.
"""

import shutil


def validate_executable_exists(cmd: list[str]) -> list[str] | None:
    """Validate that the executable in the command exists in PATH.

    Args:
        cmd: Command list where the first element is the executable

    Returns:
        Updated command list with full path to executable if found, None if not found
    """
    if not cmd or not cmd[0]:
        return None

    executable = shutil.which(cmd[0])
    if not executable:
        return None

    # Return updated command with full path to validated executable
    updated_cmd = cmd.copy()
    updated_cmd[0] = executable
    return updated_cmd
