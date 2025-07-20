from typing import List, Dict, Any
from orchestrator.models.bpmn_models import SequenceFlow

class ProcessDefinition:
    def __init__(
        self,
        id: str,
        name: str,
        elements: List[Dict[str, Any]],
        sequence_flows: List[SequenceFlow]
    ):
        self.id = id
        self.name = name
        self.elements = elements
        self.sequence_flows = sequence_flows

    def get_element_by_id(self, element_id: str) -> Dict[str, Any]:
        for element in self.elements:
            if element["id"] == element_id:
                return element
        raise ValueError(f"Element with ID {element_id} not found in process definition {self.id}")

    def get_start_event_id(self) -> str:
        for element in self.elements:
            if element["type"] == "Event" and element["event_type"] == "StartEvent":
                return element["id"]
        raise ValueError(f"No StartEvent found in process definition {self.id}")
