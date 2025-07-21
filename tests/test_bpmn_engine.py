import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from orchestrator.bpmn_engine import BPMNEngine
from orchestrator.models.bpmn_models import Process, Task, Event, Gateway, ProcessStatus, TaskStatus, EventType, GatewayType, SequenceFlow, AgentStatus, TaskType, Agent, AgentType

@pytest.fixture
def mock_dgraph_client():
    return AsyncMock()

@pytest.fixture
def bpmn_engine(mock_dgraph_client):
    active_processes = {}
    worker_clients = {}
    redis_client = MagicMock()
    dead_letter_queue_stream = "dlq"
    return BPMNEngine(mock_dgraph_client, active_processes, worker_clients, redis_client, dead_letter_queue_stream)

@pytest.mark.asyncio
async def test_process_start_event(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc1", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["start_event_1"], sequence_flows=[
        SequenceFlow(id="flow1", source_ref="start_event_1", target_ref="task1")
    ])
    start_event = Event(id="start_event_1", name="Start Event", event_type=EventType.START_EVENT, status=TaskStatus.READY, process_id="proc1")

    mock_dgraph_client.get_bpmn_element.return_value = start_event
    mock_dgraph_client.upsert_event.return_value = None
    mock_dgraph_client.upsert_process.return_value = None

    bpmn_engine.active_processes[process.id] = process

    await bpmn_engine._process_event(process, start_event)

    assert start_event.status == TaskStatus.COMPLETED
    mock_dgraph_client.upsert_event.assert_called_once_with(start_event)
    assert "start_event_1" not in process.current_elements_ids
    assert "task1" in process.current_elements_ids
    mock_dgraph_client.upsert_process.assert_called_once_with(process)

@pytest.mark.asyncio
async def test_process_end_event(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc2", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["end_event_1"], sequence_flows=[])
    end_event = Event(id="end_event_1", name="End Event", event_type=EventType.END_EVENT, status=TaskStatus.READY, process_id="proc2")

    mock_dgraph_client.get_bpmn_element.return_value = end_event
    mock_dgraph_client.upsert_event.return_value = None
    mock_dgraph_client.upsert_process.return_value = None

    bpmn_engine.active_processes[process.id] = process

    await bpmn_engine._process_event(process, end_event)

    assert end_event.status == TaskStatus.COMPLETED
    mock_dgraph_client.upsert_event.assert_called_once_with(end_event)
    assert "end_event_1" not in process.current_elements_ids
    assert process.status == ProcessStatus.COMPLETED
    assert process.end_time is not None
    mock_dgraph_client.upsert_process.assert_called_once_with(process)
    assert process.id not in bpmn_engine.active_processes

@pytest.mark.asyncio
async def test_process_task_ready_no_worker(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc3", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["task1"])
    task = Task(id="task1", name="Test Task", status=TaskStatus.READY, task_type=TaskType.SERVICE_TASK, process_id="proc3")

    mock_dgraph_client.get_bpmn_element.return_value = task
    mock_dgraph_client.get_agent.return_value = None # No idle worker

    await bpmn_engine._process_task(process, task)

    assert task.status == TaskStatus.READY # Should remain ready
    mock_dgraph_client.upsert_task.assert_not_called()
    mock_dgraph_client.upsert_agent.assert_not_called()

@pytest.mark.asyncio
async def test_process_task_ready_with_worker(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc4", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["task1"])
    task = Task(id="task1", name="Test Task", status=TaskStatus.READY, task_type=TaskType.SERVICE_TASK, process_id="proc4")
    worker_agent = Agent(id="worker1", name="Worker 1", agent_type=AgentType.WORKER, status=AgentStatus.IDLE)
    mock_worker_client = AsyncMock()

    bpmn_engine.worker_clients["worker1"] = mock_worker_client
    mock_dgraph_client.get_bpmn_element.return_value = task
    mock_dgraph_client.get_agent.return_value = worker_agent
    mock_dgraph_client.upsert_task.return_value = None
    mock_dgraph_client.upsert_agent.return_value = None

    await bpmn_engine._process_task(process, task)

    assert task.status == TaskStatus.IN_PROGRESS
    assert task.assigned_agent_id == "worker1"
    mock_dgraph_client.upsert_task.assert_called_once_with(task)
    assert worker_agent.status == AgentStatus.BUSY
    assert worker_agent.current_task_id == "task1"
    mock_dgraph_client.upsert_agent.assert_called_once_with(worker_agent)
    mock_worker_client.send_message.assert_called_once()
    args, kwargs = mock_worker_client.send_message.call_args
    assert args[0] == "execute_task"
    assert args[1]["task_id"] == "task1"
    assert args[1]["process_id"] == "proc4"

@pytest.mark.asyncio
async def test_handle_worker_task_completion_success(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc5", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["task1"], sequence_flows=[
        SequenceFlow(id="flow2", source_ref="task1", target_ref="end_event_1")
    ])
    task = Task(id="task1", name="Test Task", status=TaskStatus.IN_PROGRESS, assigned_agent_id="worker1", process_id="proc5", task_type=TaskType.SERVICE_TASK)
    worker_agent = Agent(id="worker1", name="Worker 1", agent_type=AgentType.WORKER, status=AgentStatus.BUSY, current_task_id="task1")

    mock_dgraph_client.get_task.return_value = task
    mock_dgraph_client.get_agent.return_value = worker_agent
    mock_dgraph_client.upsert_task.return_value = None
    mock_dgraph_client.upsert_agent.return_value = None
    mock_dgraph_client.get_process.return_value = process
    mock_dgraph_client.upsert_process.return_value = None

    await bpmn_engine.handle_worker_task_completion("task1", True, "Task completed successfully.")

    assert task.status == TaskStatus.COMPLETED
    assert task.output_data == "Task completed successfully."
    assert task.end_time is not None
    mock_dgraph_client.upsert_task.assert_called_once_with(task)
    assert worker_agent.status == AgentStatus.IDLE
    assert worker_agent.current_task_id is None
    mock_dgraph_client.upsert_agent.assert_called_once_with(worker_agent)
    assert "task1" not in process.current_elements_ids
    assert "end_event_1" in process.current_elements_ids
    mock_dgraph_client.upsert_process.assert_called_once_with(process)

@pytest.mark.asyncio
async def test_handle_worker_task_completion_failure_retry(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc6", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["task1"])
    task = Task(id="task1", name="Test Task", status=TaskStatus.IN_PROGRESS, assigned_agent_id="worker1", process_id="proc6", retry_count=0, max_retries=2, task_type=TaskType.SERVICE_TASK)
    worker_agent = Agent(id="worker1", name="Worker 1", agent_type=AgentType.WORKER, status=AgentStatus.BUSY, current_task_id="task1")

    mock_dgraph_client.get_task.return_value = task
    mock_dgraph_client.get_agent.return_value = worker_agent
    mock_dgraph_client.upsert_task.return_value = None
    mock_dgraph_client.upsert_agent.return_value = None
    mock_dgraph_client.get_process.return_value = process
    mock_dgraph_client.upsert_process.return_value = None

    await bpmn_engine.handle_worker_task_completion("task1", False, "Task failed.")

    assert task.status == TaskStatus.READY
    assert task.retry_count == 1
    mock_dgraph_client.upsert_task.assert_called_once_with(task)
    assert worker_agent.status == AgentStatus.IDLE
    assert worker_agent.current_task_id is None
    mock_dgraph_client.upsert_agent.assert_called_once_with(worker_agent)
    assert "task1" in process.current_elements_ids # Task should still be active for retry
    mock_dgraph_client.upsert_process.assert_not_called() # Process status should not change yet

@pytest.mark.asyncio
async def test_handle_worker_task_completion_failure_permanent(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc7", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["task1"])
    task = Task(id="task1", name="Test Task", status=TaskStatus.IN_PROGRESS, assigned_agent_id="worker1", process_id="proc7", retry_count=1, max_retries=1, task_type=TaskType.SERVICE_TASK)
    worker_agent = Agent(id="worker1", name="Worker 1", agent_type=AgentType.WORKER, status=AgentStatus.BUSY, current_task_id="task1")

    mock_dgraph_client.get_task.return_value = task
    mock_dgraph_client.get_agent.return_value = worker_agent
    mock_dgraph_client.upsert_task.return_value = None
    mock_dgraph_client.upsert_agent.return_value = None
    mock_dgraph_client.get_process.return_value = process
    mock_dgraph_client.upsert_process.return_value = None

    await bpmn_engine.handle_worker_task_completion("task1", False, "Task failed permanently.")

    assert task.status == TaskStatus.FAILED
    assert task.end_time is not None
    assert "Failed after 1 retries" in task.output_data
    mock_dgraph_client.upsert_task.assert_called_once_with(task)
    assert worker_agent.status == AgentStatus.IDLE
    assert worker_agent.current_task_id is None
    mock_dgraph_client.upsert_agent.assert_called_once_with(worker_agent)
    assert process.status == ProcessStatus.FAILED
    assert process.end_time is not None
    mock_dgraph_client.upsert_process.assert_called_once_with(process)
    assert process.id not in bpmn_engine.active_processes

@pytest.mark.asyncio
async def test_process_exclusive_gateway_condition_true(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc8", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["gateway1"], sequence_flows=[
        SequenceFlow(id="flowA", source_ref="task_prev", target_ref="gateway1"),
        SequenceFlow(id="flowB", source_ref="gateway1", target_ref="task_valid", condition_expression="data_valid == True"),
        SequenceFlow(id="flowC", source_ref="gateway1", target_ref="task_invalid", condition_expression="data_valid == False")
    ])
    gateway = Gateway(id="gateway1", name="Exclusive Gateway", gateway_type=GatewayType.EXCLUSIVE_GATEWAY, status=TaskStatus.READY, process_id="proc8")
    preceding_task = Task(id="task_prev", name="Previous Task", output_data=json.dumps({"data_valid": True}), process_id="proc8", task_type=TaskType.SERVICE_TASK)

    mock_dgraph_client.get_bpmn_element.return_value = gateway
    mock_dgraph_client.get_task.return_value = preceding_task
    mock_dgraph_client.upsert_gateway.return_value = None
    mock_dgraph_client.upsert_process.return_value = None

    await bpmn_engine._process_gateway(process, gateway)

    assert gateway.status == TaskStatus.COMPLETED
    mock_dgraph_client.upsert_gateway.assert_called_once_with(gateway)
    assert "gateway1" not in process.current_elements_ids
    assert "task_valid" in process.current_elements_ids
    assert "task_invalid" not in process.current_elements_ids
    mock_dgraph_client.upsert_process.assert_called_once_with(process)

@pytest.mark.asyncio
async def test_process_exclusive_gateway_condition_false(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc9", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["gateway1"], sequence_flows=[
        SequenceFlow(id="flowA", source_ref="task_prev", target_ref="gateway1"),
        SequenceFlow(id="flowB", source_ref="gateway1", target_ref="task_valid", condition_expression="data_valid == True"),
        SequenceFlow(id="flowC", source_ref="gateway1", target_ref="task_invalid", condition_expression="data_valid == False")
    ])
    gateway = Gateway(id="gateway1", name="Exclusive Gateway", gateway_type=GatewayType.EXCLUSIVE_GATEWAY, status=TaskStatus.READY, process_id="proc9")
    preceding_task = Task(id="task_prev", name="Previous Task", output_data=json.dumps({"data_valid": False}), process_id="proc9", task_type=TaskType.SERVICE_TASK)

    mock_dgraph_client.get_bpmn_element.return_value = gateway
    mock_dgraph_client.get_task.return_value = preceding_task
    mock_dgraph_client.upsert_gateway.return_value = None
    mock_dgraph_client.upsert_process.return_value = None

    await bpmn_engine._process_gateway(process, gateway)

    assert gateway.status == TaskStatus.COMPLETED
    mock_dgraph_client.upsert_gateway.assert_called_once_with(gateway)
    assert "gateway1" not in process.current_elements_ids
    assert "task_valid" not in process.current_elements_ids
    assert "task_invalid" in process.current_elements_ids
    mock_dgraph_client.upsert_process.assert_called_once_with(process)

@pytest.mark.asyncio
async def test_process_parallel_gateway(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc10", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["gateway1"], sequence_flows=[
        SequenceFlow(id="flowA", source_ref="gateway1", target_ref="taskA"),
        SequenceFlow(id="flowB", source_ref="gateway1", target_ref="taskB")
    ])
    gateway = Gateway(id="gateway1", name="Parallel Gateway", gateway_type=GatewayType.PARALLEL_GATEWAY, status=TaskStatus.READY, process_id="proc10")

    mock_dgraph_client.get_bpmn_element.return_value = gateway
    mock_dgraph_client.upsert_gateway.return_value = None
    mock_dgraph_client.upsert_process.return_value = None

    await bpmn_engine._process_gateway(process, gateway)

    assert gateway.status == TaskStatus.COMPLETED
    mock_dgraph_client.upsert_gateway.assert_called_once_with(gateway)
    assert "gateway1" not in process.current_elements_ids
    assert "taskA" in process.current_elements_ids
    assert "taskB" in process.current_elements_ids
    mock_dgraph_client.upsert_process.assert_called_once_with(process)

@pytest.mark.asyncio
async def test_process_error_event(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc12", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["error_event_1"], sequence_flows=[])
    error_event = Event(id="error_event_1", name="Error Event", event_type=EventType.ERROR_EVENT, status=TaskStatus.READY, process_id="proc12")

    mock_dgraph_client.get_bpmn_element.return_value = error_event
    mock_dgraph_client.upsert_event.return_value = None
    mock_dgraph_client.upsert_process.return_value = None

    bpmn_engine.active_processes[process.id] = process

    await bpmn_engine._process_event(process, error_event)

    assert error_event.status == TaskStatus.COMPLETED
    mock_dgraph_client.upsert_event.assert_called_once_with(error_event)
    assert process.status == ProcessStatus.FAILED
    assert process.end_time is not None
    mock_dgraph_client.upsert_process.assert_called_once_with(process)
    assert process.id not in bpmn_engine.active_processes

@pytest.mark.asyncio
async def test_process_timer_event_not_completed(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc13", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["timer_event_1"], sequence_flows=[
        SequenceFlow(id="flowE", source_ref="timer_event_1", target_ref="taskC")
    ])
    timer_event = Event(id="timer_event_1", name="Timer Event", event_type=EventType.TIMER_EVENT, status=TaskStatus.READY, process_id="proc13", input_data=json.dumps({"duration": 5}))

    mock_dgraph_client.get_bpmn_element.return_value = timer_event
    mock_dgraph_client.upsert_event.return_value = None
    mock_dgraph_client.upsert_process.return_value = None

    bpmn_engine.active_processes[process.id] = process

    await bpmn_engine._process_event(process, timer_event)

    assert timer_event.status == TaskStatus.READY # Should still be READY
    mock_dgraph_client.upsert_event.assert_called_once_with(timer_event) # Should have updated start_time
    assert timer_event.start_time is not None
    assert "taskC" not in process.current_elements_ids # Should not have advanced

@pytest.mark.asyncio
async def test_process_timer_event_completed(bpmn_engine, mock_dgraph_client):
    process = Process(id="proc14", name="Test Process", process_definition_id="test_def", version=1, status=ProcessStatus.RUNNING, current_elements_ids=["timer_event_1"], sequence_flows=[
        SequenceFlow(id="flowF", source_ref="timer_event_1", target_ref="taskD")
    ])
    # Simulate that the timer started 10 seconds ago
    start_time = datetime.now() - timedelta(seconds=10)
    timer_event = Event(id="timer_event_1", name="Timer Event", event_type=EventType.TIMER_EVENT, status=TaskStatus.READY, process_id="proc14", input_data=json.dumps({"duration": 5}), start_time=start_time)

    mock_dgraph_client.get_bpmn_element.return_value = timer_event
    mock_dgraph_client.upsert_event.return_value = None
    mock_dgraph_client.upsert_process.return_value = None

    bpmn_engine.active_processes[process.id] = process

    await bpmn_engine._process_event(process, timer_event)

    assert timer_event.status == TaskStatus.COMPLETED
    mock_dgraph_client.upsert_event.assert_called_once_with(timer_event)
    assert "timer_event_1" not in process.current_elements_ids
    assert "taskD" in process.current_elements_ids
    mock_dgraph_client.upsert_process.assert_called_once_with(process)
