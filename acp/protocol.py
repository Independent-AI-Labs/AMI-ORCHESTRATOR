"""
Defines the Agent-Coordinator Protocol (ACP) data structures.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RegisterAgent:
    """Message sent by an agent to register with the orchestrator."""

    agent_id: str
    capabilities: List[str]


@dataclass
class TaskRequest:
    """Message sent by the orchestrator to request a task from an agent."""

    task_id: str
    task_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskCompleted:
    """Message sent by an agent to report task completion."""

    task_id: str
    result: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskFailed:
    """Message sent by an agent to report task failure."""

    task_id: str
    error_message: str
