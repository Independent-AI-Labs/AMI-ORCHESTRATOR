import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from orchestrator.dgraph.dgraph_client import DgraphClient
from orchestrator.dgraph.dgraph_schema_manager import DgraphSchemaManager
from orchestrator.models.bpmn_models import Process, Task, Agent, ProcessStatus, TaskStatus, AgentStatus, TaskTypeasync def dgraph_client_fixture():
    client = DgraphClient()
    schema_manager = DgraphSchemaManager(dgraph_url=client.dgraph_url) # Use client's URL
    await schema_manager.apply_schema()
    yield client
    await client.close()
    await schema_manager.close()

@pytest.mark.asyncio
async def test_upsert_and_get_process(dgraph_client_fixture):
    process_id = "test_process_1"
    process = Process(id=process_id, name="Test Process", process_definition_id="def_1", version=1)
    
    # Upsert the process
    uid = await client.upsert_process(process)
    assert uid is not None
    
    # Get the process and verify
    retrieved_process = await client.get_process(process_id)
    assert retrieved_process is not None
    assert retrieved_process.id == process.id
    assert retrieved_process.name == process.name
    assert retrieved_process.process_definition_id == process.process_definition_id
    assert retrieved_process.version == process.version
    assert retrieved_process.status == process.status

@pytest.mark.asyncio
async def test_update_process_status(dgraph_client_fixture):
    process_id = "test_process_status_update"
    process = Process(id=process_id, name="Process for Status Update", process_definition_id="def_2", version=1, status=ProcessStatus.RUNNING)
    await client.upsert_process(process)

    # Update status
    updated = await client.update_process_status(process_id, ProcessStatus.COMPLETED)
    assert updated is True

    # Verify updated status
    retrieved_process = await client.get_process(process_id)
    assert retrieved_process.status == ProcessStatus.COMPLETED

@pytest.mark.asyncio
async def test_upsert_and_get_task(dgraph_client_fixture):
    task_id = "test_task_1"
    task = Task(id=task_id, name="Test Task", process_id="test_process_1", task_type=TaskType.SERVICE_TASK)
    
    # Upsert the task
    uid = await client.upsert_task(task)
    assert uid is not None
    
    # Get the task and verify
    retrieved_task = await client.get_task(task_id)
    assert retrieved_task is not None
    assert retrieved_task.id == task.id
    assert retrieved_task.name == task.name
    assert retrieved_task.process_id == task.process_id
    assert retrieved_task.task_type == task.task_type
    assert retrieved_task.status == task.status

@pytest.mark.asyncio
async def test_update_task_status(dgraph_client_fixture):
    task_id = "test_task_status_update"
    task = Task(id=task_id, name="Task for Status Update", process_id="test_process_1", task_type=TaskType.USER_TASK, status=TaskStatus.READY)
    await client.upsert_task(task)

    # Update status
    updated = await client.update_task_status(task_id, TaskStatus.IN_PROGRESS)
    assert updated is True

    # Verify updated status
    retrieved_task = await client.get_task(task_id)
    assert retrieved_task.status == TaskStatus.IN_PROGRESS

@pytest.mark.asyncio
async def test_upsert_and_get_agent(dgraph_client_fixture):
    agent_id = "test_agent_1"
    agent = Agent(id=agent_id, name="Test Agent")
    
    # Upsert the agent
    uid = await client.upsert_agent(agent)
    assert uid is not None
    
    # Get the agent and verify
    retrieved_agent = await client.get_agent(agent_id)
    assert retrieved_agent is not None
    assert retrieved_agent.id == agent.id
    assert retrieved_agent.name == agent.name
    assert retrieved_agent.agent_type == agent.agent_type
    assert retrieved_agent.status == agent.status

@pytest.mark.asyncio
async def test_update_agent_status(dgraph_client_fixture):
    agent_id = "test_agent_status_update"
    agent = Agent(id=agent_id, name="Agent for Status Update", status=AgentStatus.IDLE)
    await client.upsert_agent(agent)

    # Update status
    updated = await client.update_agent_status(agent_id, AgentStatus.BUSY)
    assert updated is True

    # Verify updated status
    retrieved_agent = await client.get_agent(agent_id)
    assert retrieved_agent.status == AgentStatus.BUSY

@pytest.mark.asyncio
async def test_get_process_instances(dgraph_client_fixture):
    definition_id = "test_definition_id"
    # Create multiple process instances for the same definition
    process1 = Process(id="proc_inst_1", name="Instance 1", process_definition_id=definition_id, version=1)
    process2 = Process(id="proc_inst_2", name="Instance 2", process_definition_id=definition_id, version=1)
    process3 = Process(id="proc_inst_3", name="Instance 3", process_definition_id=definition_id, version=2)

    await client.upsert_process(process1)
    await client.upsert_process(process2)
    await client.upsert_process(process3)

    # Get all instances for the definition
    instances_all = await client.get_process_instances(definition_id)
    assert len(instances_all) == 3
    assert any(p.id == "proc_inst_1" for p in instances_all)
    assert any(p.id == "proc_inst_2" for p in instances_all)
    assert any(p.id == "proc_inst_3" for p in instances_all)

    # Get instances for a specific version
    instances_v1 = await client.get_process_instances(definition_id, version=1)
    assert len(instances_v1) == 2
    assert any(p.id == "proc_inst_1" for p in instances_v1)
    assert any(p.id == "proc_inst_2" for p in instances_v1)
    assert not any(p.id == "proc_inst_3" for p in instances_v1)

    instances_v2 = await client.get_process_instances(definition_id, version=2)
    assert len(instances_v2) == 1
    assert any(p.id == "proc_inst_3" for p in instances_v2)

    # Test with non-existent definition
    instances_non_existent = await client.get_process_instances("non_existent_def")
    assert len(instances_non_existent) == 0

    # Test with non-existent version
    instances_non_existent_version = await client.get_process_instances(definition_id, version=99)
    assert len(instances_non_existent_version) == 0
