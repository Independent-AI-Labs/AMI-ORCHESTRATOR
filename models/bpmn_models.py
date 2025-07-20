from datetime import datetime
from typing import List, Optional, Union
from enum import Enum

class ProcessStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"

class TaskType(str, Enum):
    USER_TASK = "UserTask"
    SERVICE_TASK = "ServiceTask"
    SCRIPT_TASK = "ScriptTask"

class TaskStatus(str, Enum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"

class EventType(str, Enum):
    START_EVENT = "StartEvent"
    END_EVENT = "EndEvent"
    INTERMEDIATE_CATCH_EVENT = "IntermediateCatchEvent"
    INTERMEDIATE_THROW_EVENT = "IntermediateThrowEvent"

class EventStatus(str, Enum):
    TRIGGERED = "TRIGGERED"
    COMPLETED = "COMPLETED"

class GatewayType(str, Enum):
    EXCLUSIVE_GATEWAY = "ExclusiveGateway"
    PARALLEL_GATEWAY = "ParallelGateway"
    INCLUSIVE_GATEWAY = "InclusiveGateway"

class GatewayStatus(str, Enum):
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"

class AgentType(str, Enum):
    ORCHESTRATOR = "Orchestrator"
    WORKER = "Worker"

class AgentStatus(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"

class SequenceFlow:
    def __init__(self, id: str, source_ref: str, target_ref: str):
        self.id = id
        self.source_ref = source_ref
        self.target_ref = target_ref

class BPMNElement:
    id: str
    name: str
    process_id: str
    outgoing_flows: List[SequenceFlow] = []

class Task(BPMNElement):
    def __init__(
        self,
        id: str,
        name: str,
        process_id: str,
        task_type: TaskType,
        status: TaskStatus = TaskStatus.READY,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        assigned_agent_id: Optional[str] = None,
        input_data: Optional[str] = None,
        output_data: Optional[str] = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ):
        self.id = id
        self.name = name
        self.process_id = process_id
        self.task_type = task_type
        self.status = status
        self.start_time = start_time if start_time else datetime.now()
        self.end_time = end_time
        self.assigned_agent_id = assigned_agent_id
        self.input_data = input_data
        self.output_data = output_data

class Event(BPMNElement):
    def __init__(
        self,
        id: str,
        name: str,
        process_id: str,
        event_type: EventType,
        status: EventStatus = EventStatus.TRIGGERED,
        triggered_by_id: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.process_id = process_id
        self.event_type = event_type
        self.status = status
        self.triggered_by_id = triggered_by_id

class Gateway(BPMNElement):
    def __init__(
        self,
        id: str,
        name: str,
        process_id: str,
        gateway_type: GatewayType,
        status: GatewayStatus = GatewayStatus.EVALUATING,
    ):
        self.id = id
        self.name = name
        self.process_id = process_id
        self.gateway_type = gateway_type
        self.status = status

class Agent:
    def __init__(
        self,
        id: str,
        name: str,
        agent_type: AgentType = AgentType.WORKER,
        status: AgentStatus = AgentStatus.IDLE,
        current_task_id: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.agent_type = agent_type
        self.status = status
        self.current_task_id = current_task_id

class Process:
    def __init__(
        self,
        id: str,
        name: str,
        status: ProcessStatus = ProcessStatus.RUNNING,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        current_elements_ids: Optional[List[str]] = None,
        sequence_flows: Optional[List["SequenceFlow"]] = None, # Add sequence flows to the process
    ):
        self.id = id
        self.name = name
        self.status = status
        self.start_time = start_time if start_time else datetime.now()
        self.end_time = end_time
        self.current_elements_ids = current_elements_ids if current_elements_ids else []
        self.sequence_flows = sequence_flows if sequence_flows else []

# Union type for BPMN elements that can be 'currentElements'
BPMNElementType = Union[Task, Event, Gateway]
