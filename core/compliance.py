"""
Compliance tools for the Orchestrator.
"""

from orchestrator.core.dgraph_client import DgraphClient


class Compliance:
    """Provides compliance-related functionality."""

    def __init__(self, dgraph_client: DgraphClient):
        """Initialize the compliance tool."""
        self.dgraph_client = dgraph_client

    def get_audit_log(self, query: str) -> list:
        """Get the audit log from Dgraph."""
        return self.dgraph_client.query(query)

    def export_audit_log_to_csv(self, query: str, file_path: str):
        """Export the audit log to a CSV file."""
        audit_log = self.get_audit_log(query)
        # This is a placeholder for the actual implementation.
        print(f"Exporting audit log to {file_path}")
        with open(file_path, "w", encoding="utf-8") as f:
            for entry in audit_log:
                f.write(str(entry) + "\n")
