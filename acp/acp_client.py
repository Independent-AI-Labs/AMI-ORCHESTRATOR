"""
Client for the Agent-Coordinator Protocol (ACP).
"""

import json
import subprocess
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, cast
from unittest.mock import MagicMock

from orchestrator.acp.protocol import (
    InitializeParams,
    InitializeResponse,
    SendUserMessageParams,
)

# region: Data Classes


# endregion: Data Classes


class RequestError(Exception):
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.data = data


D = TypeVar("D")


class Stream:
    def __init__(self, process: subprocess.Popen):
        self._process = process

    def read(self) -> Optional[str]:
        if self._process.stdout:
            return self._process.stdout.readline()
        return None

    def write(self, message: str):
        if self._process.stdin:
            try:
                self._process.stdin.write(message)
                self._process.stdin.flush()
            except IOError:
                pass

    def close(self):
        if self._process.stdout:
            try:
                self._process.stdout.close()
            except IOError:
                pass


class Connection(Generic[D]):
    def __init__(self, delegate: D, stream: Stream, test_mode=False):
        self._delegate = delegate
        self._stream = stream
        self._next_request_id = 0
        self._pending_responses: Dict[int, Callable[[Any], None]] = {}
        self._lock = Lock()
        self._running = False
        self._test_mode = test_mode
        self._listener_thread: Optional[Thread] = None

    def start(self):
        if not self._test_mode:
            self._running = True
            self._listener_thread = Thread(target=self._listen)
            self._listener_thread.daemon = True
            self._listener_thread.start()

    def stop(self):
        if not self._test_mode and self._running:
            self._running = False
            self._stream.close()
            if self._listener_thread and self._listener_thread.is_alive():
                self._listener_thread.join(timeout=1)

    def _listen(self):
        while self._running:
            try:
                line = self._stream.read()
                if not line:
                    break
                message = json.loads(line)
                self._process_message(message)
            except (IOError, json.JSONDecodeError):
                break

    def _process_message(self, message: Dict[str, Any]):
        if "method" in message:
            self._handle_request(message)
        else:
            self._handle_response(message)

    def _handle_request(self, request: Dict[str, Any]):
        method_name = request["method"]
        params = request.get("params")
        request_id = request.get("id")

        if not hasattr(self._delegate, method_name):
            if request_id is not None:
                self._send_error(request_id, -32601, "Method not found")
            return

        method = getattr(self._delegate, method_name)
        try:
            result = method(params)
            if request_id is not None:
                self._send_response(request_id, result)
        except (TypeError, AttributeError) as e:
            if request_id is not None:
                self._send_error(request_id, -32603, str(e))

    def _handle_response(self, response: Dict[str, Any]):
        response_id = response["id"]
        with self._lock:
            callback = self._pending_responses.pop(response_id, None)

        if callback:
            if "result" in response:
                callback(response["result"])
            elif "error" in response:
                error = response["error"]
                callback(RequestError(error["code"], error["message"], error.get("data")))

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        request_id = self._get_next_request_id()
        request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        self._send_message(json.dumps(request) + "\n")

        if self._test_mode:
            # In test mode, we manually read the response
            response_line = self._stream.read()
            if response_line:
                response = json.loads(response_line)
                if "result" in response:
                    return response["result"]
                if "error" in response:
                    err = response["error"]
                    raise RequestError(err["code"], err["message"], err.get("data"))
            return None  # Should not happen in tests

        # In normal mode, wait for the listener thread
        event = Event()
        result: Optional[Any] = None

        def callback(response):
            nonlocal result
            result = response
            event.set()

        with self._lock:
            self._pending_responses[request_id] = callback

        event.wait(timeout=5)
        if not event.is_set():
            raise TimeoutError(f"Request '{method}' timed out")

        if isinstance(result, RequestError):
            raise result
        if result is None:
            raise TimeoutError(f"Request '{method}' timed out")
        return result

    def _send_response(self, request_id: int, result: Any):
        response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        self._send_message(json.dumps(response) + "\n")

    def _send_error(self, request_id: int, code: int, message: str, data: Optional[Any] = None):
        error = {"code": code, "message": message}
        if data:
            error["data"] = data
        response = {"jsonrpc": "2.0", "id": request_id, "error": error}
        self._send_message(json.dumps(response) + "\n")

    def _send_message(self, message: str):
        self._stream.write(message)

    def _get_next_request_id(self) -> int:
        with self._lock:
            self._next_request_id += 1
            return self._next_request_id


class AcpClient:
    """Client for the Agent-Coordinator Protocol (ACP)."""

    def __init__(self, gemini_cli_path: str, delegate: Any, test_mode=False):
        self.gemini_cli_path = gemini_cli_path
        self.process: Optional[subprocess.Popen] = None
        self.connection: Optional[Connection] = None
        self._delegate = delegate
        self._test_mode = test_mode

    def start(self):
        if not self._test_mode:
            self.process = cast(
                subprocess.Popen,
                subprocess.Popen(
                    ["node", self.gemini_cli_path, "--experimental-acp"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ),
            )
            stream = Stream(self.process)
        else:
            # In test mode, the stream is a mock
            stream = MagicMock()

        self.connection = Connection(self._delegate, stream, self._test_mode)
        self.connection.start()

    def stop(self):
        if self.connection:
            self.connection.stop()
        if self.process and not self._test_mode:
            self.process.terminate()
            self.process.wait()

    def initialize(self, params: InitializeParams) -> InitializeResponse:
        if self.connection is None:
            raise ConnectionError("Connection not initialized.")
        result = self.connection.send_request("initialize", params.__dict__)  # type: ignore
        return InitializeResponse(**result)

    def send_user_message(self, params: SendUserMessageParams) -> None:
        if self.connection is None:
            raise ConnectionError("Connection not initialized.")
        self.connection.send_request("sendUserMessage", params.__dict__)  # type: ignore

    def cancel_send_message(self) -> None:
        if self.connection is None:
            raise ConnectionError("Connection not initialized.")
        self.connection.send_request("cancelSendMessage")  # type: ignore
