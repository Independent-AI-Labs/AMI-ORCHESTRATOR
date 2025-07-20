import pydgraph
import json
import os
import asyncio

DGRAPH_SERVER_ADDR = "10.8.0.3:9080"
SCHEMA_FILE_PATH = "C:/Users/vdonc/AMI-SDA/schema.graphql"

async def apply_dgraph_schema(client: pydgraph.DgraphClient, schema_content: str) -> bool:
    """
    Applies the Dgraph schema.
    """
    op = pydgraph.Operation(schema=schema_content)
    try:
        await client.alter(op)
        print("Dgraph schema applied successfully.")
        return True
    except Exception as e:
        print(f"Error applying Dgraph schema: {e}")
        return False

async def get_dgraph_schema(client: pydgraph.DgraphClient) -> bytes:
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
        return b''
    finally:
        if txn:
            txn.discard()

def read_local_schema(file_path: str) -> str:
    """
    Reads the schema from the local schema.graphql file.
    """
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Local schema file not found at {file_path}")
        return ""

async def verify_and_apply_schema():
    client_stub = None
    try:
        client_stub = pydgraph.DgraphClientStub(DGRAPH_SERVER_ADDR)
        client = pydgraph.DgraphClient(client_stub)

        print(f"Attempting to retrieve schema from Dgraph at {DGRAPH_SERVER_ADDR}...")
        dgraph_schema_bytes = await get_dgraph_schema(client)

        local_schema_content = read_local_schema(SCHEMA_FILE_PATH)
        if not local_schema_content:
            print("Local schema file could not be read. Aborting schema operations.")
            return

        if dgraph_schema_bytes:
            print("Successfully retrieved schema from Dgraph.")
            # Basic check: if the local schema content is not present in the Dgraph schema string
            # This is a very simplistic check and might need refinement for complex schemas.
            if local_schema_content.strip() in dgraph_schema_bytes.decode('utf-8').strip():
                print("Dgraph schema appears to match local schema. No application needed.")
            else:
                print("Dgraph schema does NOT fully match local schema. Attempting to apply...")
                if await apply_dgraph_schema(client, local_schema_content):
                    print("Schema application attempt successful.")
                else:
                    print("Schema application attempt failed. Please check Dgraph logs.")
        else:
            print("Failed to retrieve schema from Dgraph. Attempting to apply schema...")
            if await apply_dgraph_schema(client, local_schema_content):
                print("Schema application attempt successful.")
            else:
                print("Schema application attempt failed. Please check Dgraph logs.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if client_stub:
            client_stub.close()
            print("Dgraph client stub closed.")

if __name__ == "__main__":
    asyncio.run(verify_and_apply_schema())
