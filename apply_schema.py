"""
Applies the Dgraph schema to the database.
"""

from __future__ import annotations

from pathlib import Path

import pydgraph  # type: ignore

from orchestrator.core.dgraph_client import DgraphClient
from orchestrator.core.schema_generator import main as generate_schema


def apply_schema():
    """Applies the Dgraph schema."""
    generate_schema()
    schema_file = Path("orchestrator/core/schema.dql")
    schema = schema_file.read_text(encoding="utf-8")

    client = DgraphClient()
    try:
        op = pydgraph.Operation(schema_update=schema)
        client.alter(op)
        print("Schema applied successfully.")
    finally:
        client.close()


if __name__ == "__main__":
    apply_schema()
