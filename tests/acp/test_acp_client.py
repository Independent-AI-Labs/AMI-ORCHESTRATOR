# pylint: disable=protected-access
import json
import unittest
from unittest.mock import MagicMock, patch

from orchestrator.acp.acp_client import AcpClient
from orchestrator.acp.protocol import InitializeParams, SendUserMessageParams


class TestAcpClient(unittest.TestCase):
    """Tests for the Gemini CLI adapter."""

    def setUp(self):
        """Set up the test case."""
        self.adapter = AcpClient("path/to/gemini.js", MagicMock(), test_mode=True)
        self.adapter.start()

    @patch("orchestrator.acp.acp_client.Stream")
    def test_initialize(self, mock_stream_class):
        """Test that the adapter sends the correct initialize message."""
        mock_stream = MagicMock()
        mock_stream.read.return_value = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "result": {
                    "is_authenticated": True,
                    "protocol_version": "0.0.9",
                },
            }
        )
        mock_stream_class.return_value = mock_stream

        self.adapter.connection._stream = mock_stream
        response = self.adapter.initialize(InitializeParams(protocol_version="0.0.9"))

        self.assertTrue(response.is_authenticated)
        self.assertEqual(response.protocol_version, "0.0.9")

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocol_version": "0.0.9"},
        }
        mock_stream.write.assert_called_once_with(json.dumps(request) + "\n")

    @patch("orchestrator.acp.acp_client.Stream")
    def test_send_user_message(self, mock_stream_class):
        """Test that the adapter sends the correct sendUserMessage message."""
        mock_stream = MagicMock()
        mock_stream.read.return_value = json.dumps({"jsonrpc": "2.0", "id": 1, "result": None})
        mock_stream_class.return_value = mock_stream

        self.adapter.connection._stream = mock_stream

        self.adapter.send_user_message(SendUserMessageParams(chunks=[{"text": "Hello, world!"}]))

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendUserMessage",
            "params": {"chunks": [{"text": "Hello, world!"}]},
        }
        mock_stream.write.assert_called_once_with(json.dumps(request) + "\n")

    def tearDown(self):
        if hasattr(self, "adapter"):
            self.adapter.stop()


if __name__ == "__main__":
    unittest.main()
