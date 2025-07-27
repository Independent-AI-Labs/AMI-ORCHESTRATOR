"""
Defines the Agent-Coordinator Protocol (ACP) data structures for the JSON-RPC protocol used by the Gemini CLI.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from orchestrator.acp.agent import Icon


@dataclass
class StreamAssistantMessageChunkParams:
    chunk: Dict[str, Any]


@dataclass
class ToolCallLocation:
    path: str
    line: Optional[int] = None


@dataclass
class RequestToolCallConfirmationParams:
    confirmation: Dict[str, Any]
    icon: Icon
    label: str
    content: Optional[Dict[str, Any]] = None
    locations: Optional[List[ToolCallLocation]] = None


@dataclass
class PushToolCallParams:
    icon: Icon
    label: str
    content: Optional[Dict[str, Any]] = None
    locations: Optional[List[ToolCallLocation]] = None


@dataclass
class UpdateToolCallParams:
    content: Optional[Dict[str, Any]]
    status: str
    tool_call_id: int


@dataclass
class RequestToolCallConfirmationResponse:
    id: int
    outcome: str


@dataclass
class PushToolCallResponse:
    id: int


@dataclass
class InitializeParams:
    protocol_version: str


@dataclass
class SendUserMessageParams:
    chunks: List[Dict[str, Any]]


@dataclass
class InitializeResponse:
    is_authenticated: bool
    protocol_version: str


@dataclass
class Error:
    code: int
    message: str
    data: Optional[Any] = None


class Client:
    def stream_assistant_message_chunk(self, params: StreamAssistantMessageChunkParams) -> None:
        raise NotImplementedError

    def request_tool_call_confirmation(self, params: RequestToolCallConfirmationParams) -> RequestToolCallConfirmationResponse:
        raise NotImplementedError

    def push_tool_call(self, params: PushToolCallParams) -> PushToolCallResponse:
        raise NotImplementedError

    def update_tool_call(self, params: UpdateToolCallParams) -> None:
        raise NotImplementedError


class Agent:
    def initialize(self, params: InitializeParams) -> InitializeResponse:
        raise NotImplementedError

    def authenticate(self) -> None:
        raise NotImplementedError

    def send_user_message(self, params: SendUserMessageParams) -> None:
        raise NotImplementedError

    def cancel_send_message(self) -> None:
        raise NotImplementedError
