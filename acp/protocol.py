"""
This module defines the Agent-Coordinator Protocol (ACP), which facilitates
communication between the orchestrator and various agents.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# region: Generic JSON-RPC Structures


@dataclass
class Request:
    """Represents a JSON-RPC request."""

    jsonrpc: str
    id: int
    method: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class Response:
    """Represents a JSON-RPC response."""

    jsonrpc: str
    id: int
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


@dataclass
class Error:
    """Represents a JSON-RPC error."""

    code: int
    message: str
    data: Optional[Any] = None


# endregion: Generic JSON-RPC Structures

# region: ACP Method Parameters


@dataclass
class InitializeParams:
    """Parameters for the 'initialize' method."""

    protocol_version: str


@dataclass
class SendUserMessageParams:
    """Parameters for the 'sendUserMessage' method."""

    chunks: List[Dict[str, Any]]


# endregion: ACP Method Parameters

# region: ACP Method Responses


@dataclass
class InitializeResponse:
    """Response for the 'initialize' method."""

    is_authenticated: bool
    protocol_version: str


# endregion: ACP Method Responses

# region: Agent-to-Coordinator Notification Parameters


@dataclass
class StreamAssistantMessageChunkParams:
    """Parameters for the 'streamAssistantMessageChunk' notification."""

    chunk: Dict[str, Any]


@dataclass
class ToolCallLocation:
    """Represents a location for a tool call."""

    path: str
    line: Optional[int] = None


@dataclass
class RequestToolCallConfirmationParams:
    """Parameters for the 'requestToolCallConfirmation' notification."""

    confirmation: Dict[str, Any]
    label: str
    content: Optional[Dict[str, Any]] = None
    locations: Optional[List[ToolCallLocation]] = None


@dataclass
class PushToolCallParams:
    """Parameters for the 'pushToolCall' notification."""

    label: str
    content: Optional[Dict[str, Any]] = None
    locations: Optional[List[ToolCallLocation]] = None


@dataclass
class UpdateToolCallParams:
    """Parameters for the 'updateToolCall' notification."""

    content: Optional[Dict[str, Any]]
    status: str
    tool_call_id: int


# endregion: Agent-to-Coordinator Notification Parameters

# region: Coordinator-to-Agent Responses to Notifications


@dataclass
class RequestToolCallConfirmationResponse:
    """Response to 'requestToolCallConfirmation'."""

    id: int
    outcome: str


@dataclass
class PushToolCallResponse:
    """Response to 'pushToolCall'."""

    id: int


# endregion: Coordinator-to-Agent Responses to Notifications

# region: AI


@dataclass
class AIRequest:
    """Represents a request to an AI agent."""

    prompt: str
    context: Optional[Dict[str, Any]] = None


# endregion: AI

# region: Task Management


@dataclass
class TaskRequest:
    """Represents a request to a worker to execute a task."""

    task_id: str
    task_type: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class TaskResult:
    """Represents the result of a task execution."""

    task_id: str
    result: Any
    error: Optional[Error] = None


# endregion: Task Management
