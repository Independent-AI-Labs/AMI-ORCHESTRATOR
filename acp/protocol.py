"""
This module defines the Agent-Coordinator Protocol (ACP), which facilitates
communication between the orchestrator and various agents.
"""

from dataclasses import dataclass
from typing import Any

# region: Generic JSON-RPC Structures


@dataclass
class Request:
    """Represents a JSON-RPC request."""

    jsonrpc: str
    id: int
    method: str
    params: dict[str, Any] | None = None


@dataclass
class Response:
    """Represents a JSON-RPC response."""

    jsonrpc: str
    id: int
    result: Any | None = None
    error: dict[str, Any] | None = None


@dataclass
class Error:
    """Represents a JSON-RPC error."""

    code: int
    message: str
    data: Any | None = None


# endregion: Generic JSON-RPC Structures

# region: ACP Method Parameters


@dataclass
class InitializeParams:
    """Parameters for the 'initialize' method."""

    protocol_version: str


@dataclass
class SendUserMessageParams:
    """Parameters for the 'sendUserMessage' method."""

    chunks: list[dict[str, Any]]


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

    chunk: dict[str, Any]


@dataclass
class ToolCallLocation:
    """Represents a location for a tool call."""

    path: str
    line: int | None = None


@dataclass
class RequestToolCallConfirmationParams:
    """Parameters for the 'requestToolCallConfirmation' notification."""

    confirmation: dict[str, Any]
    label: str
    content: dict[str, Any] | None = None
    locations: list["ToolCallLocation"] | None = None


@dataclass
class PushToolCallParams:
    """Parameters for the 'pushToolCall' notification."""

    label: str
    content: dict[str, Any] | None = None
    locations: list[ToolCallLocation] | None = None


@dataclass
class UpdateToolCallParams:
    """Parameters for the 'updateToolCall' notification."""

    content: dict[str, Any] | None
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
    context: dict[str, Any] | None = None


# endregion: AI

# region: Task Management


@dataclass
class TaskRequest:
    """Represents a request to a worker to execute a task."""

    task_id: str
    task_type: str
    params: dict[str, Any] | None = None


@dataclass
class TaskResult:
    """Represents the result of a task execution."""

    task_id: str
    result: Any
    error: Error | None = None


# endregion: Task Management
