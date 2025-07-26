import json
import unittest
from unittest.mock import MagicMock, patch

from orchestrator.acp.gemini_acp_protocol import InitializeParams, SendUserMessageParams
from orchestrator.acp.gemini_cli_adapter import GeminiCliAdapter


class TestGeminiCliAdapter(unittest.TestCase):
    """Tests for the Gemini CLI adapter."""

    @patch("subprocess.Popen")
    def test_initialize(self, mock_popen):
        """Test that the adapter sends the correct initialize message."""
        mock_process = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdout.readline = MagicMock(
            return_value=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "result": {
                        "is_authenticated": True,
                        "protocol_version": "0.0.9",
                    },
                }
            )
        )
        mock_popen.return_value = mock_process

        self.adapter = GeminiCliAdapter("path/to/gemini.js")
        response = self.adapter.initialize(InitializeParams(protocol_version="0.0.9"))

        self.assertTrue(response.is_authenticated)
        self.assertEqual(response.protocol_version, "0.0.9")

        request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {"protocol_version": "0.0.9"},
        }
        mock_process.stdin.write.assert_called_once_with(json.dumps(request) + "\n")

    @patch("subprocess.Popen")
    def test_send_user_message(self, mock_popen):
        """Test that the adapter sends the correct sendUserMessage message."""
        mock_process = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_popen.return_value = mock_process

        self.adapter = GeminiCliAdapter("path/to/gemini.js")
        self.adapter.process = mock_process

        self.adapter.send_user_message(SendUserMessageParams(chunks=[{"text": "Hello, world!"}]))

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendUserMessage",
            "params": {"chunks": [{"text": "Hello, world!"}]},
        }
        mock_process.stdin.write.assert_called_once_with(json.dumps(request) + "\n")

    def tearDown(self):
        if hasattr(self, "adapter") and self.adapter.process:
            self.adapter.stop()


if __name__ == "__main__":
    unittest.main()
