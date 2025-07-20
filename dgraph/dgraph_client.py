from typing import Any, Dict, List, Optional, Union
import json
from datetime import datetime
from enum import Enum
import uuid

import pydgraph

from orchestrator.models.bpmn_models import Process, Task, Event, Gateway, Agent, BPMNElementType, ProcessStatus, TaskType, TaskStatus, EventType, GatewayType, AgentType, SequenceFlow

import os

class DgraphClient:
    def __init__(self):
        host = os.getenv("DGRAPH_HOST", "localhost")
        port = os.getenv("DGRAPH_PORT", "9080")
        self.dgraph_url = f"{host}:{port}"
        self.client_stub = pydgraph.DgraphClientStub(self.dgraph_url)
        self.client = pydgraph.DgraphClient(self.client_stub)
        print(f"[DgraphClient] Initialized (connecting to Dgraph at {self.dgraph_url})")

    async def _to_dgraph_json(self, obj: Any) -> Dict[str, Any]:
        data = obj.__dict__.copy()
        # Remove internal Python attributes and None values
        data = {k: v for k, v in data.items() if not k.startswith('_') and v is not None}

        # Convert Enum values to their string representation
        for k, v in data.items():
            if isinstance(v, Enum):
                data[k] = v.value
            elif isinstance(v, datetime):
                data[k] = v.isoformat()
            elif isinstance(v, list):
                # Handle lists of objects, e.g., sequence_flows
                new_list = []
                for item in v:
                    if hasattr(item, '__dict__'):
                        new_list.append(self._to_dgraph_json_sync(item)) # Use sync version for nested calls
                    else:
                        new_list.append(item)
                data[k] = new_list

        # Add dgraph.type for schema type
        data["dgraph.type"] = obj.__class__.__name__
        # Use 'id' as uid for upsert if it exists
        if hasattr(obj, 'id'):
            data["uid"] = f"_:{obj.id}"
            data["id"] = obj.id # Store original ID as a predicate

        return data

    # Synchronous version for nested calls within _to_dgraph_json
    def _to_dgraph_json_sync(self, obj: Any) -> Dict[str, Any]:
        data = obj.__dict__.copy()
        data = {k: v for k, v in data.items() if not k.startswith('_') and v is not None}
        for k, v in data.items():
            if isinstance(v, Enum):
                data[k] = v.value
            elif isinstance(v, datetime):
                data[k] = v.isoformat()
            elif isinstance(v, list):
                new_list = []
                for item in v:
                    if hasattr(item, '__dict__'):
                        new_list.append(self._to_dgraph_json_sync(item))
                    else:
                        new_list.append(item)
                data[k] = new_list
        data["dgraph.type"] = obj.__class__.__name__
        if hasattr(obj, 'id'):
            data["uid"] = f"_:{obj.id}"
            data["id"] = obj.id
        return data

    async def _from_dgraph_json(self, data: Dict[str, Any], model_type: type):
        # Convert Dgraph JSON back to BPMN model object
        # Remove dgraph.type and uid before passing to constructor
        data_copy = data.copy()
        data_copy.pop("dgraph.type", None)
        data_copy.pop("uid", None)

        # Convert string representations back to Enum or datetime if necessary
        for k, v in data_copy.items():
            if k == "status" and hasattr(model_type, 'status') and isinstance(model_type.status, Enum):
                data_copy[k] = model_type.status.__class__(v)
            elif k == "task_type" and hasattr(model_type, 'task_type') and isinstance(model_type.task_type, Enum):
                data_copy[k] = model_type.task_type.__class__(v)
            elif k == "event_type" and hasattr(model_type, 'event_type') and isinstance(model_type.event_type, Enum):
                data_copy[k] = model_type.event_type.__class__(v)
            elif k == "gateway_type" and hasattr(model_type, 'gateway_type') and isinstance(model_type.gateway_type, Enum):
                data_copy[k] = model_type.gateway_type.__class__(v)
            elif k == "agent_type" and hasattr(model_type, 'agent_type') and "agent_type" in data_copy:
                data_copy[k] = AgentType(data_copy[k]) if isinstance(data_copy[k], str) else data_copy[k]
            elif k in ["start_time", "end_time"] and isinstance(v, str):
                try:
                    data_copy[k] = datetime.fromisoformat(v)
                except ValueError:
                    pass # Keep as string if not a valid isoformat
            elif k == "sequence_flows" and isinstance(v, list):
                new_flows = []
                for item in v:
                    if isinstance(item, dict) and "source_ref" in item and "target_ref" in item:
                        new_flows.append(SequenceFlow(id=item.get("id", str(uuid.uuid4())), source_ref=item["source_ref"], target_ref=item["target_ref"])) # Assuming SequenceFlow has id, source_ref, target_ref
                    else:
                        new_flows.append(item)
                data_copy[k] = new_flows

        return model_type(**data_copy)

    async def upsert_node(self, obj: Any) -> str:
        txn = self.client.txn()
        try:
            pb = await self._to_dgraph_json(obj)
            # print(f"[DgraphClient] Upserting JSON: {json.dumps(pb, indent=2)}")
            mutation = txn.create_mutation(set_obj=pb)
            request = txn.create_request(mutations=[mutation], commit_now=True)
            response = txn.do_request(request)
            # Extract UID if a new node was created, otherwise it's an update
            if response.uids:
                # If a new UID was assigned, it will be in response.uids
                # We assume the first UID in the map corresponds to our object
                # This might need more robust mapping if multiple objects are upserted
                for _, uid_val in response.uids.items():
                    return uid_val # Return the first UID found
            return obj.id # If no new UID, assume it was an update and return original ID
        finally:
            if txn:
                txn.discard()

    async def get_node(self, obj_id: str, model_type: type) -> Optional[Any]:
        query = f"{{ q(func: eq(id, \"{obj_id}\")) {{ expand(_all_) }} }}"
        res = await self.query(query)
        if res and res[0]:
            return await self._from_dgraph_json(res[0], model_type)
        return None

    async def upsert_process(self, process: Process) -> str:
        print(f"[DgraphClient] Upserting Process: {process.name} (ID: {process.id})")
        return await self.upsert_node(process)

    async def get_process(self, process_id: str) -> Optional[Process]:
        print(f"[DgraphClient] Getting Process with ID: {process_id}")
        return await self.get_node(process_id, Process)

    async def upsert_task(self, task: Task) -> str:
        print(f"[DgraphClient] Upserting Task: {task.name} (ID: {task.id})")
        return await self.upsert_node(task)

    async def get_task(self, task_id: str) -> Optional[Task]:
        print(f"[DgraphClient] Getting Task with ID: {task_id}")
        return await self.get_node(task_id, Task)

    async def upsert_event(self, event: Event) -> str:
        print(f"[DgraphClient] Upserting Event: {event.name} (ID: {event.id})")
        return await self.upsert_node(event)

    async def upsert_gateway(self, gateway: Gateway) -> str:
        print(f"[DgraphClient] Upserting Gateway: {gateway.name} (ID: {gateway.id})")
        return await self.upsert_node(gateway)

    async def upsert_agent(self, agent: Agent) -> str:
        print(f"[DgraphClient] Upserting Agent: {agent.name} (ID: {agent.id})")
        return await self.upsert_node(agent)

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        print(f"[DgraphClient] Getting Agent with ID: {agent_id}")
        return await self.get_node(agent_id, Agent)

    async def get_bpmn_element(self, element_id: str) -> Optional[BPMNElementType]:
        # Try to get element as Task, Event, or Gateway
        task = await self.get_node(element_id, Task)
        if task: return task
        event = await self.get_node(element_id, Event)
        if event: return event
        gateway = await self.get_node(element_id, Gateway)
        if gateway: return gateway
        return None

    async def query(self, query_str: str) -> List[Dict[str, Any]]:
        txn = self.client.txn(read_only=True)
        try:
            response = txn.query(query_str)
            return json.loads(response.json).get("q", [])
        finally:
            txn.discard()

    async def close(self):
        if self.client_stub:
            try:
                self.client_stub.close()
            except Exception as e:
                print(f"Error closing Dgraph client stub: {e}")
