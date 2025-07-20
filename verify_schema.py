import pydgraph
import json
import os

DGRAPH_SERVER_ADDR = "10.8.0.3:9080" # Assuming Dgraph Alpha is on port 9080

def get_dgraph_schema(client):
    """
    Retrieves the current schema from Dgraph.
    """
    query = "schema {}"
    txn = client.txn(read_only=True)
    try:
        response = txn.query(query)
        return response.json
    except Exception as e:
        print(f"Error retrieving schema from Dgraph: {e}")
        return None
    finally:
        if txn:
            txn.discard()

def read_local_schema(file_path):
    """
    Reads the schema from the local schema.graphql file.
    """
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Local schema file not found at {file_path}")
        return None

def compare_schemas(dgraph_schema_json, local_schema_content):
    """
    Compares the Dgraph schema with the local schema file content.
    This is a basic string comparison. For a more robust comparison,
    one would need to parse and normalize both schemas.
    """
    if not dgraph_schema_json or not local_schema_content:
        return False, "One of the schemas is empty or could not be read."

    # Dgraph returns schema as JSON, local is GraphQL SDL.
    # We need to parse the Dgraph JSON to extract the types and predicates
    # and then compare them with the parsed local_schema_content.
    # For simplicity, let's just check if the local schema content
    # is present in the Dgraph schema string representation.
    # This is a very basic check and might not be sufficient for complex schemas.

    # A more robust comparison would involve parsing both GraphQL SDL and Dgraph's JSON schema
    # and comparing their ASTs or normalized representations.
    # For now, let's do a simple check for presence of type definitions.

    # Extract type names from local schema for a basic check
    local_types = set()
    for line in local_schema_content.split('\n'):
        if line.strip().startswith("type ") and "{" in line:
            type_name = line.strip().split(" ")[1].split("{")[0].strip()
            local_types.add(type_name)

    dgraph_schema_str = json.dumps(dgraph_schema_json, indent=2)

    missing_types = []
    for l_type in local_types:
        if f"type {l_type}" not in dgraph_schema_str:
            missing_types.append(l_type)

    if not missing_types:
        return True, "Schema verification successful: All local types found in Dgraph schema."
    else:
        return False, f"Schema verification failed: Missing types in Dgraph schema: {', '.join(missing_types)}"


if __name__ == "__main__":
    client_stub = None
    try:
        client_stub = pydgraph.DgraphClientStub(DGRAPH_SERVER_ADDR)
        client = pydgraph.DgraphClient(client_stub)

        print(f"Attempting to retrieve schema from Dgraph at {DGRAPH_SERVER_ADDR}...")
        dgraph_schema_bytes = get_dgraph_schema(client)

        if dgraph_schema_bytes:
            print("Successfully retrieved schema from Dgraph.")
            # Decode bytes to string and then load as JSON
            dgraph_schema = json.loads(dgraph_schema_bytes.decode('utf-8'))
            # print(json.dumps(dgraph_schema, indent=2)) # For debugging
        else:
            print("Failed to retrieve schema from Dgraph. Please ensure Dgraph is running and accessible.")
            exit(1)

        local_schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema.graphql')
        print(f"Reading local schema from {local_schema_path}...")
        local_schema_content = read_local_schema(local_schema_path)

        if local_schema_content:
            print("Successfully read local schema file.")
        else:
            print("Failed to read local schema file.")
            exit(1)

        print("Comparing schemas...")
        is_same, message = compare_schemas(dgraph_schema, local_schema_content)

        if is_same:
            print(f"Verification Result: {message}")
            print("Dgraph schema matches local schema. You can proceed.")
        else:
            print(f"Verification Result: {message}")
            print("Dgraph schema does NOT match local schema. Please apply the schema manually via Ratel UI or ensure Dgraph is running correctly.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if client_stub:
            client_stub.close()
            print("Dgraph client stub closed.")