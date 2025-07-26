"""
Adapter for the Gemini CLI agent.
"""

import json
import subprocess
from threading import Thread

from orchestrator.acp.gemini_acp_protocol import (
    Agent,
    InitializeParams,
    InitializeResponse,
    SendUserMessageParams,
)


class GeminiCliAdapter(Agent):
    """Adapter for the Gemini CLI agent."""

    def __init__(self, gemini_cli_path: str):
        self.gemini_cli_path = gemini_cli_path
        self.process = None
        self.thread = None
        self._running = False

    def initialize(self, params: InitializeParams) -> InitializeResponse:
        """Initialize the Gemini CLI agent."""
        self.process = subprocess.Popen(
            ["node", self.gemini_cli_path, "--experimental-acp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.thread = Thread(target=self._listen_for_messages)
        self.thread.start()

        request = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": params.__dict__}
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()

        response_str = self.process.stdout.readline()
        response = json.loads(response_str)

        return InitializeResponse(**response["result"])

    def _listen_for_messages(self):
        self._running = True
        while self._running:
            line = self.process.stdout.readline()
            if not line:
                break
            message = json.loads(line)
            # Process message

    def stop(self):
        self._running = False
        if self.process:
            self.process.terminate()
            self.process.wait()
        if self.thread:
            self.thread.join()

    def send_user_message(self, params: SendUserMessageParams) -> None:
        """Send a user message to the Gemini CLI agent."""
        request = {"jsonrpc": "2.0", "id": 1, "method": "sendUserMessage", "params": params.__dict__}
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()

    def cancel_send_message(self) -> None:
        """Cancel the current send message operation."""
        request = {"jsonrpc": "2.0", "id": 2, "method": "cancelSendMessage", "params": {}}
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
