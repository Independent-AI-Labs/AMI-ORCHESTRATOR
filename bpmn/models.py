"""
Pydantic models for the BPMN 2.0 specification.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Element(BaseModel):
    """Base model for any BPMN element."""

    id: str
    name: str | None = None
    documentation: str | None = None


class Edge(Element):
    """Model for a BPMN sequence flow."""

    source_ref: str
    target_ref: str
    condition_expression: str | None = None


class Event(Element):
    """Base model for an event."""


class StartEvent(Event):
    """Model for a start event."""


class EndEvent(Event):
    """Model for an end event."""


class IntermediateCatchEvent(Event):
    """Model for an intermediate catch event."""


class TimerEventDefinition(BaseModel):
    """Model for a timer event definition."""

    time_duration: str | None = None
    time_date: str | None = None
    time_cycle: str | None = None


class MessageEventDefinition(BaseModel):
    """Model for a message event definition."""

    message_ref: str


class Gateway(Element):
    """Base model for a gateway."""


class ExclusiveGateway(Gateway):
    """Model for an exclusive gateway."""

    default: str | None = None


class ParallelGateway(Gateway):
    """Model for a parallel gateway."""


class Task(Element):
    """Base model for a task."""


class ServiceTask(Task):
    """Model for a service task."""

    implementation: str | None = None


class HumanTask(Task):
    """Model for a human task."""

    assignee: str | None = None
    candidate_users: list[str] = []
    candidate_groups: list[str] = []


class AiTask(Task):
    """Model for an AI task."""

    prompt: str
    context: dict[str, Any] | None = None


class ProcessDefinition(Element):
    """Model for a BPMN process definition."""

    nodes: list[StartEvent | EndEvent | IntermediateCatchEvent | ExclusiveGateway | ParallelGateway | ServiceTask | HumanTask | AiTask]
    edges: list[Edge]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessInstance(BaseModel):
    """Model for a BPMN process instance."""

    id: str
    definition_id: str
    status: str
    variables: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    history: list["AuditLog"] = []


class AuditLog(BaseModel):
    """Model for an audit log entry."""

    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    instance_id: str
    element_id: str
    element_name: str | None = None
    message: str
    details: dict[str, Any] | None = None


# Add a forward reference to AuditLog in ProcessInstance
ProcessInstance.model_rebuild()


class Resource(str, Enum):
    """Enum for resource types."""

    GENERIC = "generic"
    DGRAPH = "dgraph"
    POSTGRES = "postgres"
    GPU = "gpu"
    NPU = "npu"
    CPU = "cpu"


class ResourceUsage(BaseModel):
    """Model for resource usage."""

    cpu_hours: float | None = None
    gpu_hours: float | None = None
    time_seconds: float | None = None


class ResourceCost(BaseModel):
    """Model for resource cost."""

    monetary_cost: float | None = None


class TaskResourceMetrics(BaseModel):
    """Model for task resource metrics."""

    usage: ResourceUsage
    cost: ResourceCost | None = None
