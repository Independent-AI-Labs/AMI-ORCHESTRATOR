import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from sda.services.worker_agent import WorkerAgent
from orchestrator.models.bpmn_models import TaskType, AgentStatus, AgentType, Agent

@pytest.fixture
def mock_dgraph_client():
    return AsyncMock()

@pytest.fixture
def mock_gemini_acp_client():
    mock_client = AsyncMock()
    mock_client.start_cli.return_value = True
    return mock_client

@pytest.fixture
def mock_redis_client():
    return AsyncMock()

@pytest.fixture
def worker_agent(mock_dgraph_client, mock_gemini_acp_client, mock_redis_client):
    with (
        patch('sda.services.worker_agent.DgraphClient') as MockDgraphClientClass,
        patch('sda.services.worker_agent.redis.Redis') as MockRedisClass,
        patch('sda.services.worker_agent.GeminiACPClient') as MockGeminiACPClientClass
    ):
        MockDgraphClientClass.return_value = mock_dgraph_client
        MockRedisClass.return_value = mock_redis_client
        MockGeminiACPClientClass.return_value = mock_gemini_acp_client
        agent = WorkerAgent(worker_id="test-worker")
        yield agent, MockDgraphClientClass, MockGeminiACPClientClass, MockRedisClass

@pytest.mark.asyncio
async def test_worker_agent_initialization(worker_agent, mock_dgraph_client, mock_gemini_acp_client, mock_redis_client):
    agent, MockDgraphClientClass, MockGeminiACPClientClass, MockRedisClass = worker_agent
    assert agent.worker_id == "test-worker"
    assert isinstance(agent.worker_agent_model, Agent)
    assert agent.worker_agent_model.id == "test-worker"
    assert agent.worker_agent_model.agent_type == AgentType.WORKER
    assert agent.worker_agent_model.status == AgentStatus.OFFLINE # Initial status
    MockDgraphClientClass.assert_called_once() # DgraphClient constructor should be called
    MockGeminiACPClientClass.assert_called_once() # GeminiACPClient constructor should be called
    MockRedisClass.assert_called_once() # redis.Redis constructor should be called

@pytest.mark.asyncio
async def test_worker_agent_start_and_stop(worker_agent, mock_dgraph_client, mock_gemini_acp_client):
    agent, MockDgraphClientClass, MockGeminiACPClientClass, MockRedisClass = worker_agent
    start_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1) # Give the worker a moment to start

    assert agent.running is True
    assert agent.worker_agent_model.status == AgentStatus.IDLE
    mock_dgraph_client.upsert_agent.assert_called_once_with(agent.worker_agent_model)
    MockGeminiACPClientClass.return_value.start_cli.assert_called_once()

    agent.stop()
    await start_task # Wait for the start task to complete after stopping
    assert agent.running is False
    MockGeminiACPClientClass.return_value.close.assert_called_once()

@pytest.mark.asyncio
async def test_handle_orchestrator_message_execute_service_task_with_command(worker_agent, mock_dgraph_client, mock_redis_client):
    agent, MockDgraphClientClass, MockGeminiACPClientClass, MockRedisClass = worker_agent
    message = {
        "method": "execute_task",
        "params": {
            "task_id": "task123",
            "task_name": "test_service_task",
            "task_type": TaskType.SERVICE_TASK.value,
            "process_id": "proc456",
            "input_data": {"command": "echo hello"}
        }
    }

    # Mock asyncio.create_subprocess_shell
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"hello\n", b"")
    mock_process.returncode = 0
    with patch('asyncio.create_subprocess_shell', return_value=mock_process) as mock_sub_shell:
        await agent._handle_orchestrator_message(message)
        mock_sub_shell.assert_called_once_with(
            "echo hello",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    assert agent.worker_agent_model.status == AgentStatus.BUSY
    assert agent.worker_agent_model.current_task_id == "task123"
    mock_dgraph_client.upsert_agent.assert_called_once_with(agent.worker_agent_model)

    mock_redis_client.xadd.assert_called_once()
    args, kwargs = mock_redis_client.xadd.call_args
    assert args[0] == "worker_results"
    payload = json.loads(args[1]["message"])
    assert payload["task_id"] == "task123"
    assert payload["success"] is True
    output_data = json.loads(payload["output_data"])
    assert output_data["status"] == "completed"
    assert "Command executed successfully." in output_data["result"]
    assert "hello" in output_data["result"]

@pytest.mark.asyncio
async def test_handle_orchestrator_message_execute_service_task_no_command(worker_agent, mock_dgraph_client, mock_redis_client):
    agent, MockDgraphClientClass, MockGeminiACPClientClass, MockRedisClass = worker_agent
    message = {
        "method": "execute_task",
        "params": {
            "task_id": "task124",
            "task_name": "test_service_task_no_cmd",
            "task_type": TaskType.SERVICE_TASK.value,
            "process_id": "proc457",
            "input_data": {"some_other_key": "value"}
        }
    }

    with patch('asyncio.create_subprocess_shell') as mock_sub_shell:
        await agent._handle_orchestrator_message(message)
        mock_sub_shell.assert_not_called() # No command should be executed

    assert agent.worker_agent_model.status == AgentStatus.BUSY
    assert agent.worker_agent_model.current_task_id == "task124"
    mock_dgraph_client.upsert_agent.assert_called_once_with(agent.worker_agent_model)

    mock_redis_client.xadd.assert_called_once()
    args, kwargs = mock_redis_client.xadd.call_args
    assert args[0] == "worker_results"
    payload = json.loads(args[1]["message"])
    assert payload["task_id"] == "task124"
    assert payload["success"] is True
    output_data = json.loads(payload["output_data"])
    assert output_data["status"] == "completed"
    assert "no command provided" in output_data["result"]

@pytest.mark.asyncio
async def test_handle_orchestrator_message_execute_script_task(worker_agent, mock_dgraph_client, mock_redis_client):
    agent, MockDgraphClientClass, MockGeminiACPClientClass, MockRedisClass = worker_agent
    message = {
        "method": "execute_task",
        "params": {
            "task_id": "task125",
            "task_name": "test_script_task",
            "task_type": TaskType.SCRIPT_TASK.value,
            "process_id": "proc458",
            "input_data": {"script": "console.log('hello')"}
        }
    }

    with patch('asyncio.create_subprocess_shell') as mock_sub_shell:
        await agent._handle_orchestrator_message(message)
        mock_sub_shell.assert_not_called() # Script tasks are simulated for now

    assert agent.worker_agent_model.status == AgentStatus.BUSY
    assert agent.worker_agent_model.current_task_id == "task125"
    mock_dgraph_client.upsert_agent.assert_called_once_with(agent.worker_agent_model)

    mock_redis_client.xadd.assert_called_once()
    args, kwargs = mock_redis_client.xadd.call_args
    assert args[0] == "worker_results"
    payload = json.loads(args[1]["message"])
    assert payload["task_id"] == "task125"
    assert payload["success"] is True
    output_data = json.loads(payload["output_data"])
    assert output_data["status"] == "completed"
    assert "Script task test_script_task executed." in output_data["result"]

@pytest.mark.asyncio
async def test_handle_orchestrator_message_unknown_task_type(worker_agent, mock_dgraph_client, mock_redis_client):
    agent, MockDgraphClientClass, MockGeminiACPClientClass, MockRedisClass = worker_agent
    message = {
        "method": "execute_task",
        "params": {
            "task_id": "task126",
            "task_name": "test_unknown_task",
            "task_type": "UNKNOWN_TASK_TYPE",
            "process_id": "proc459",
            "input_data": {}
        }
    }

    with patch('asyncio.create_subprocess_shell') as mock_sub_shell:
        await agent._handle_orchestrator_message(message)
        mock_sub_shell.assert_not_called()

    assert agent.worker_agent_model.status == AgentStatus.BUSY
    assert agent.worker_agent_model.current_task_id == "task126"
    mock_dgraph_client.upsert_agent.assert_called_once_with(agent.worker_agent_model)

    mock_redis_client.xadd.assert_called_once()
    args, kwargs = mock_redis_client.xadd.call_args
    assert args[0] == "worker_results"
    payload = json.loads(args[1]["message"])
    assert payload["task_id"] == "task126"
    assert payload["success"] is True
    output_data = json.loads(payload["output_data"])
    assert output_data["status"] == "completed"
    assert "Generic task test_unknown_task completed." in output_data["result"]

@pytest.mark.asyncio
async def test_handle_orchestrator_message_command_execution_failure(worker_agent, mock_dgraph_client, mock_redis_client):
    agent, MockDgraphClientClass, MockGeminiACPClientClass, MockRedisClass = worker_agent
    message = {
        "method": "execute_task",
        "params": {
            "task_id": "task127",
            "task_name": "test_failed_command",
            "task_type": TaskType.SERVICE_TASK.value,
            "process_id": "proc460",
            "input_data": {"command": "exit 1"}
        }
    }

    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"Error: Command failed\n")
    mock_process.returncode = 1
    with patch('asyncio.create_subprocess_shell', return_value=mock_process) as mock_sub_shell:
        await agent._handle_orchestrator_message(message)
        mock_sub_shell.assert_called_once()

    assert agent.worker_agent_model.status == AgentStatus.BUSY
    assert agent.worker_agent_model.current_task_id == "task127"
    mock_dgraph_client.upsert_agent.assert_called_once_with(agent.worker_agent_model)

    mock_redis_client.xadd.assert_called_once()
    args, kwargs = mock_redis_client.xadd.call_args
    assert args[0] == "worker_results"
    payload = json.loads(args[1]["message"])
    assert payload["task_id"] == "task127"
    assert payload["success"] is False
    output_data = json.loads(payload["output_data"])
    assert output_data["status"] == "failed"
    assert "Command failed with exit code 1." in output_data["error"]
    assert "Error: Command failed" in output_data["error"]


