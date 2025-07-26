"""
Applies the Dgraph schema to the database.
"""

from orchestrator.core.dgraph_client import DgraphClient


def apply_schema():
    """Applies the Dgraph schema."""
    with open("orchestrator/core/schema.dql", "r") as f:
        schema = f.read()

    client = DgraphClient()
    try:
        client.alter_schema(schema)
        print("Schema applied successfully.")
    finally:
        client.close()


if __name__ == "__main__":
    apply_schema()
