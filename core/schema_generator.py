from datetime import datetime

"""
Dgraph schema generator from Pydantic models.
"""
import inspect
import sys
from pathlib import Path
from typing import Any, Dict, List, Type

# Add project root to the Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from typing import Any, Dict, List, Type

from pydantic import BaseModel

from orchestrator.bpmn import models


def get_pydantic_models() -> List[Type[BaseModel]]:
    """Get all Pydantic models from the models module."""
    return [obj for _, obj in inspect.getmembers(models) if inspect.isclass(obj) and issubclass(obj, BaseModel)]


def pydantic_to_dgraph_type(field_type: Any) -> str:
    """Convert a Pydantic field type to a Dgraph type."""
    if field_type == str:
        return "string"
    if field_type == int:
        return "int"
    if field_type == float:
        return "float"
    if field_type == bool:
        return "bool"
    if field_type == datetime:
        return "datetime"
    return "string"  # Default to string for complex types


def generate_schema(pydantic_models: List[Type[BaseModel]]) -> str:
    """Generate a Dgraph schema from a list of Pydantic models."""
    schema_parts: List[str] = []
    for model in pydantic_models:
        type_name = model.__name__
        fields: List[str] = []
        for field_name, field_info in model.model_fields.items():
            dgraph_type = pydantic_to_dgraph_type(field_info.annotation)
            fields.append(f"    {field_name}: {dgraph_type} .")
        schema_parts.append(f"type {type_name} {{\n" + "\n".join(fields) + "\n}}")
    return "\n\n".join(schema_parts)


def main():
    """Generate the Dgraph schema and save it to a file."""
    pydantic_models = get_pydantic_models()
    schema = generate_schema(pydantic_models)
    with open("orchestrator/core/schema.dql", "w", encoding="utf-8") as f:
        f.write(schema)
    print("Dgraph schema generated successfully.")


if __name__ == "__main__":
    main()
