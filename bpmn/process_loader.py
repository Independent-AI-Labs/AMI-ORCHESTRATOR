"""
BPMN Process Loader for the Orchestrator.
"""

import json
from pathlib import Path

from orchestrator.core.dgraph_client import DgraphClient


class ProcessLoader:
    """Loads and stores BPMN process definitions."""

    def __init__(self, dgraph_client: DgraphClient):
        """Initialize the process loader."""
        self.dgraph_client = dgraph_client

    def load_process_from_file(self, file_path: str) -> dict:
        """Load a BPMN process definition from a JSON file."""
        process_definition = Path(file_path).read_text(encoding="utf-8")
        return json.loads(process_definition)

    def store_process_definition(self, process_definition: dict):
        """Store a BPMN process definition in Dgraph."""
        # This is a placeholder for the actual implementation.
        print(f"Storing process definition: {process_definition['name']}")
        # In a real implementation, we would use the dgraph_client to
        # mutate the graph and store the process definition.
