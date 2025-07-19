import logging
import uuid
import json

from sda.core.bpmn_models import Process, Task, Event, Gateway, ProcessStatus, TaskType, EventType, GatewayType, SequenceFlow
from sda.services.dgraph_client import DgraphClient
from sda.core.process_definitions import ProcessDefinition

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class ProcessDefinitionsLoader:
    def __init__(self, dgraph_client: DgraphClient, active_processes: dict):
        self.dgraph_client = dgraph_client
        self.active_processes = active_processes

    async def start_bpmn_process(self, process_name: str, initial_data: dict = None):
        # For now, we'll use a hardcoded process definition for demonstration.
        # In a real system, this would be loaded from a file or database.
        bpmn_definition_data = {
            "id": "sample_process_1",
            "name": process_name,
            "elements": [
                {
                    "type": "Event",
                    "id": "start_event_1",
                    "name": "Process Started",
                    "event_type": "StartEvent"
                },
                {
                    "type": "Task",
                    "id": "task_process_data",
                    "name": "Process Data",
                    "task_type": "ServiceTask"
                },
                {
                    "type": "Gateway",
                    "id": "gateway_data_valid",
                    "name": "Is Data Valid?",
                    "gateway_type": "ExclusiveGateway"
                },
                {
                    "type": "Task",
                    "id": "task_handle_valid",
                    "name": "Handle Valid Data",
                    "task_type": "ServiceTask"
                },
                {
                    "type": "Task",
                    "id": "task_handle_invalid",
                    "name": "Handle Invalid Data",
                    "task_type": "ServiceTask"
                },
                {
                    "type": "Event",
                    "id": "end_event_1",
                    "name": "Process Ended",
                    "event_type": "EndEvent"
                }
            ],
            "sequence_flows": [
                { "id": "flow_1", "source_ref": "start_event_1", "target_ref": "task_process_data" },
                { "id": "flow_2", "source_ref": "task_process_data", "target_ref": "gateway_data_valid" },
                { "id": "flow_3_valid", "source_ref": "gateway_data_valid", "target_ref": "task_handle_valid" },
                { "id": "flow_4_invalid", "source_ref": "gateway_data_valid", "target_ref": "task_handle_invalid" },
                { "id": "flow_5_valid_to_end", "source_ref": "task_handle_valid", "target_ref": "end_event_1" },
                { "id": "flow_6_invalid_to_end", "source_ref": "task_handle_invalid", "target_ref": "end_event_1" }
            ]
        }

        process_definition = self._load_bpmn_process_definition(bpmn_definition_data)

        process_id = str(uuid.uuid4())
        new_process = Process(id=process_id, name=process_name, sequence_flows=process_definition.sequence_flows)

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
        logging.info(f"[ORCHESTRATOR] Started new BPMN Process: {process_name} (ID: {new_process.id}) with predefined flow.")
        return new_process

    def _load_bpmn_process_definition(self, definition: dict) -> ProcessDefinition:
        sequence_flows = []
        for flow_data in definition["sequence_flows"]:
            flow = SequenceFlow(id=flow_data["id"], source_ref=flow_data["source_ref"], target_ref=flow_data["target_ref"])
            sequence_flows.append(flow)

        return ProcessDefinition(
            id=definition["id"],
            name=definition["name"],
            elements=definition["elements"],
            sequence_flows=sequence_flows
        )
