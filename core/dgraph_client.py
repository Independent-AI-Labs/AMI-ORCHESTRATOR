"""
Dgraph client for the Orchestrator.
"""

import pydgraph  # type: ignore

from orchestrator.core.config import Config


class DgraphClient:
    """Dgraph client for the Orchestrator."""

    def __init__(self):
        """Initialize the Dgraph client."""
        self.host = Config.DGRAPH_HOST
        self.port = Config.DGRAPH_PORT
        self._client_stub = pydgraph.DgraphClientStub(f"{self.host}:{self.port}")
        self._dgraph_client = pydgraph.DgraphClient(self._client_stub)

    def close(self):
        """Close the Dgraph client connection."""
        self._client_stub.close()

    def alter(self, op):
        """Alter the Dgraph schema."""
        return self._dgraph_client.alter(op)

    def mutate(self, mutation):
        """Run a mutation."""
        txn = self._dgraph_client.txn()
        try:
            response = txn.mutate(set_obj=mutation)
            txn.commit()
            return response
        finally:
            txn.discard()

    def query(self, query, variables=None):
        """Run a query."""
        txn = self._dgraph_client.txn(read_only=True)
        return txn.query(query, variables=variables)

    def create_process_instance(self):
        """Create a new process instance in Dgraph."""
        # This is a placeholder for the actual implementation.
        return "0x123"

    def create_human_task(self):
        """Create a new human task in Dgraph."""
        # This is a placeholder for the actual implementation.
        return "0x456"
