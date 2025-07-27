"""
Pydantic models for the BPMN 2.0 specification.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class Element(BaseModel):
    """Base model for any BPMN element."""

    id: str
    name: Optional[str] = None
    documentation: Optional[str] = None


class Edge(Element):
    """Model for a BPMN sequence flow."""

    source_ref: str
    target_ref: str
    condition_expression: Optional[str] = None


class Event(Element):
    """Base model for an event."""

    pass


class StartEvent(Event):
    """Model for a start event."""

    pass


class EndEvent(Event):
    """Model for an end event."""

    pass


class IntermediateCatchEvent(Event):
    """Model for an intermediate catch event."""

    pass


class TimerEventDefinition(BaseModel):
    """Model for a timer event definition."""

    time_duration: Optional[str] = None
    time_date: Optional[str] = None
    time_cycle: Optional[str] = None


class MessageEventDefinition(BaseModel):
    """Model for a message event definition."""

    message_ref: str


class Gateway(Element):
    """Base model for a gateway."""

    pass


class ExclusiveGateway(Gateway):
    """Model for an exclusive gateway."""

    default: Optional[str] = None


class ParallelGateway(Gateway):
    """Model for a parallel gateway."""

    pass


class Task(Element):
    """Base model for a task."""

    pass


class ServiceTask(Task):
    """Model for a service task."""

    implementation: Optional[str] = None


class HumanTask(Task):
    """Model for a human task."""

    assignee: Optional[str] = None
    candidate_users: List[str] = []
    candidate_groups: List[str] = []


class AiTask(Task):
    """Model for an AI task."""

    prompt: str
    context: Optional[Dict[str, Any]] = None


class ProcessDefinition(Element):
    """Model for a BPMN process definition."""

    nodes: List[Union[StartEvent, EndEvent, IntermediateCatchEvent, ExclusiveGateway, ParallelGateway, ServiceTask, HumanTask, AiTask]]
    edges: List[Edge]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessInstance(BaseModel):
    """Model for a BPMN process instance."""

    id: str
    definition_id: str
    status: str
    variables: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    history: List["AuditLog"] = []


class AuditLog(BaseModel):
    """Model for an audit log entry."""

    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    instance_id: str
    element_id: str
    element_name: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None


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

    cpu_hours: Optional[float] = None
    gpu_hours: Optional[float] = None
    time_seconds: Optional[float] = None


class ResourceCost(BaseModel):
    """Model for resource cost."""

    monetary_cost: Optional[float] = None


class TaskResourceMetrics(BaseModel):
    """Model for task resource metrics."""

    usage: ResourceUsage
    cost: Optional[ResourceCost] = None
