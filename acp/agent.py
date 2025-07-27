"""
Defines the base classes for the Agent-Coordinator Protocol (ACP).
"""

from enum import Enum


class Icon(Enum):
    """An icon to display in the UI."""

    DEFAULT = "default"
    FILE = "file"
    SEARCH = "search"
    EDIT = "edit"
    EXECUTE = "execute"
    FETCH = "fetch"
    INFO = "info"
