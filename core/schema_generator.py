"""
Dgraph schema generator from Pydantic models.
"""

import inspect
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from orchestrator.bpmn import models

# Add project root to the Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))


def get_pydantic_models() -> list[type[BaseModel]]:
    """Get all Pydantic models from the models module."""
    return [obj for _, obj in inspect.getmembers(models) if inspect.isclass(obj) and issubclass(obj, BaseModel)]


def pydantic_to_dgraph_type(field_type: Any) -> str:
    """Convert a Pydantic field type to a Dgraph type."""
    if field_type is str:
        return "string"
    if field_type is int:
        return "int"
    if field_type is float:
        return "float"
    if field_type is bool:
        return "bool"
    if field_type is datetime:
        return "datetime"
    return "string"  # Default to string for complex types


def generate_schema(pydantic_models: list[type[BaseModel]]) -> str:
    """Generate a Dgraph schema from a list of Pydantic models."""
    schema_parts: list[str] = []
    for model in pydantic_models:
        type_name = model.__name__
        fields: list[str] = []
        for field_name, field_info in model.model_fields.items():
            dgraph_type = pydantic_to_dgraph_type(field_info.annotation)
            fields.append(f"    {field_name}: {dgraph_type} .")
        schema_parts.append(f"type {type_name} {{\n" + "\n".join(fields) + "\n}}")
    return "\n\n".join(schema_parts)


def main():
    """Generate the Dgraph schema and save it to a file."""
    pydantic_models = get_pydantic_models()
    schema = generate_schema(pydantic_models)
    Path("orchestrator/core/schema.dql").write_text(schema, encoding="utf-8")
    print("Dgraph schema generated successfully.")


if __name__ == "__main__":
    main()
