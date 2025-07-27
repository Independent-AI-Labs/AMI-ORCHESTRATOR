"""
Applies the Dgraph schema to the database.
"""

import pydgraph  # type: ignore

from orchestrator.core.dgraph_client import DgraphClient
from orchestrator.core.schema_generator import main as generate_schema


def apply_schema():
    """Applies the Dgraph schema."""
    generate_schema()
    with open("orchestrator/core/schema.dql", "r", encoding="utf-8") as f:
        schema = f.read()

    client = DgraphClient()
    try:
        op = pydgraph.Operation(schema_update=schema)
        client.alter(op)
        print("Schema applied successfully.")
    finally:
        client.close()


if __name__ == "__main__":
    apply_schema()
