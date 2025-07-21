import logging
import uuid
import json
import os

from orchestrator.models.bpmn_models import Process, Task, Event, Gateway, ProcessStatus, TaskType, EventType, GatewayType, SequenceFlow
from orchestrator.dgraph.dgraph_client import DgraphClient
from orchestrator.models.process_definitions import ProcessDefinition

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class ProcessDefinitionsLoader:
    def __init__(self, dgraph_client: DgraphClient, active_processes: dict):
        self.dgraph_client = dgraph_client
        self.active_processes = active_processes

    async def start_bpmn_process(self, process_definition_id: str, version: str = "latest", initial_data: dict = None):
        # Load the BPMN process definition from an external source (e.g., file or database)
        # For now, we'll simulate loading by raising an error if not found.
        # In a real system, this would involve fetching the definition based on ID and version.
        bpmn_definition_data = self._load_definition_from_source(process_definition_id, version)
        if not bpmn_definition_data:
            raise ValueError(f"BPMN process definition '{process_definition_id}' (version: {version}) not found.")

        process_definition = self._load_bpmn_process_definition(bpmn_definition_data)

        process_id = str(uuid.uuid4())
        new_process = Process(id=process_id, name=process_definition.name, sequence_flows=process_definition.sequence_flows)

        for element_data in process_definition.elements:
            element_id = element_data["id"]
            element_name = element_data["name"]
            element_type = element_data["type"]

            if element_type == "Event":
                event_type = EventType(element_data["event_type"])
                element = Event(id=element_id, name=element_name, process_id=process_id, event_type=event_type)
                await self.dgraph_client.upsert_event(element)
            elif element_type == "Task":
                task_type = TaskType(element_data["task_type"])
                input_data_str = json.dumps(initial_data) if initial_data else "{}"
                element = Task(id=element_id, name=element_name, process_id=process_id, task_type=task_type, input_data=input_data_str)
                await self.dgraph_client.upsert_task(element)
            elif element_type == "Gateway":
                gateway_type = GatewayType(element_data["gateway_type"])
                element = Gateway(id=element_id, name=element_name, process_id=process_id, gateway_type=gateway_type)
                await self.dgraph_client.upsert_gateway(element)
            else:
                raise ValueError(f"Unknown BPMN element type: {element_type}")

        new_process.current_elements_ids.append(process_definition.get_start_event_id())

        await self.dgraph_client.upsert_process(new_process)
        self.active_processes[new_process.id] = new_process
        logging.info(f"[ORCHESTRATOR] Started new BPMN Process: {process_definition.name} (ID: {new_process.id}) with predefined flow.")
        return new_process

    def _load_definition_from_source(self, process_definition_id: str, version: str) -> dict:
        # In a real system, this would load from a database or a more sophisticated file system.
        # For now, we'll load from a JSON file in the bpmn_definitions directory.
        file_path = f"orchestrator/bpmn_definitions/{process_definition_id}.json"
        try:
            with open(file_path, 'r') as f:
                definition = json.load(f)
            if definition.get("version") == version or version == "latest":
                return definition
            else:
                return None # Version mismatch
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            logging.error(f"[ORCHESTRATOR] Error decoding JSON from {file_path}")
            return None
        return new_process

    def _load_bpmn_process_definition(self, definition: dict) -> ProcessDefinition:
        sequence_flows = []
        for flow_data in definition["sequence_flows"]:
            flow = SequenceFlow(id=flow_data["id"], source_ref=flow_data["source_ref"], target_ref=flow_data["target_ref"])
            sequence_flows.append(flow)

        return ProcessDefinition(
            id=definition["id"],
            name=definition["name"],
            version=definition["version"],
            elements=definition["elements"],
            sequence_flows=sequence_flows
        )
