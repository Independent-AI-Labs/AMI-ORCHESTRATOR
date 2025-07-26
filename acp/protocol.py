"""
Defines the Agent-Coordinator Protocol (ACP) data structures.
"""
from enum import Enum


class TaskType(Enum):
    AI_REQUEST = "ai_request"
    GENERIC_TASK = "generic_task"


class Resource(Enum):
    DGRAPH = "dgraph"
    POSTGRES = "postgres"
    GPU = "gpu"
    NPU = "npu"
    CPU = "cpu"
    GENERIC = "generic"


from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
@dataclass
class AIRequest:
    """Defines a standardized request for an AI agent."""

    task_type: str  # e.g., "decision_request", "content_analysis", "code_generation"
    input_data: Dict[str, Any] = field(default_factory=dict)  # Input for the AI task, can include references to large data
    parameters: Dict[str, Any] = field(default_factory=dict)  # Additional parameters for the AI task


@dataclass
class AIResponse:
    """Defines a standardized response from an AI agent."""

    status: str  # e.g., "success", "failure", "partial_success"
    output_data: Dict[str, Any] = field(default_factory=dict)  # Output from the AI task, can include references to large data
    confidence_score: float = 0.0  # Confidence score of the AI's response
    extracted_entities: Dict[str, Any] = field(default_factory=dict)  # Extracted entities or key-value pairs
    error_message: str = ""  # Error message if status is "failure"


class RegisterAgent:
    """Message sent by an agent to register with the orchestrator."""

    agent_id: str
    capabilities: List[str]
    resource_capabilities: List[Resource] = field(default_factory=list)


@dataclass
class TaskRequest:
    """Message sent by the orchestrator to request a task from an agent."""

    task_id: str
    task_name: str
    task_type: TaskType = TaskType.GENERIC_TASK
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskCompleted:
    """Message sent by an agent to report task completion."""

    task_id: str
    result: Dict[str, Any] | AIResponse = field(default_factory=dict)


@dataclass
class TaskFailed:
    """Message sent by an agent to report task failure."""

    task_id: str
    error_message: str
