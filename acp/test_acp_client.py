"""
Tests for the AcpClient.
"""

import json
from unittest.mock import MagicMock, call, patch

import pytest

from orchestrator.acp.acp_client import (
    AcpClient,
    InitializeParams,
    InitializeResponse,
    RequestError,
    SendUserMessageParams,
)


@pytest.fixture
def mock_client():
    delegate = MagicMock()
    # In test mode, the client uses a MagicMock for the process
    client = AcpClient("path/to/gemini", delegate, test_mode=True)
    client.start()
    return client, client.process  # Return the client and the mocked process


def test_initialize_success(mock_client):
    # Arrange
    client, mock_process = mock_client
    mock_process.stdout.readline.return_value = '{"jsonrpc": "2.0", "id": 1, "result": {"is_authenticated": true, "protocol_version": "0.0.9"}}'

    # Act
    response = client.initialize(InitializeParams(protocol_version="0.0.9"))

    # Assert
    assert isinstance(response, InitializeResponse)
    assert response.is_authenticated
    assert response.protocol_version == "0.0.9"
    expected_message = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocol_version": "0.0.9"}}) + "\n"
    mock_process.stdin.write.assert_called_once_with(expected_message)


def test_initialize_error(mock_client):
    # Arrange
    client, mock_process = mock_client
    mock_process.stdout.readline.return_value = '{"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "Initialization failed"}}'

    # Act & Assert
    with pytest.raises(RequestError) as excinfo:
        client.initialize(InitializeParams(protocol_version="0.0.9"))
    assert excinfo.value.code == -32000
    assert "Initialization failed" in str(excinfo.value)


def test_send_user_message(mock_client):
    # Arrange
    client, mock_process = mock_client
    mock_process.stdout.readline.return_value = '{"jsonrpc": "2.0", "id": 1, "result": null}'

    # Act
    params = SendUserMessageParams(chunks=[{"text": "Hello"}])
    client.send_user_message(params)

    # Assert
    expected_message = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "sendUserMessage", "params": {"chunks": [{"text": "Hello"}]}}) + "\n"
    mock_process.stdin.write.assert_called_once_with(expected_message)


def test_cancel_send_message(mock_client):
    # Arrange
    client, mock_process = mock_client
    mock_process.stdout.readline.return_value = '{"jsonrpc": "2.0", "id": 1, "result": null}'

    # Act
    client.cancel_send_message()

    # Assert
    expected_message = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "cancelSendMessage", "params": None}) + "\n"
    mock_process.stdin.write.assert_called_once_with(expected_message)
