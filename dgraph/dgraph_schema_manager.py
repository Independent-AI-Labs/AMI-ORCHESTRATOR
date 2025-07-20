import pydgraph
import os
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class DgraphSchemaManager:
    # Embedded Dgraph Schema as a string literal
    EMBEDDED_SCHEMA = """
id: string @index(exact) .
name: string @index(exact) .
status: string @index(exact) .
startTime: datetime @index(hour) .
endTime: datetime .
tasks: [uid] @reverse .
events: [uid] @reverse .
gateways: [uid] @reverse .
process: uid @reverse .
assignedAgent: uid @reverse .
inputData: string .
outputData: string .
type: string @index(exact) .
currentTask: uid @reverse .

type Process {
  id
  name
  status
  startTime
  endTime
  tasks
  events
  gateways
}

type Task {
  id
  name
  type
  status
  startTime
  endTime
  process
  assignedAgent
  inputData
  outputData
}

type Event {
  id
  name
  type
  status
  process
}

type Gateway {
  id
  name
  type
  status
  process
}

type Agent {
  id
  name
  type
  status
  currentTask
}
"""

    def __init__(self, dgraph_url: str = "10.8.0.3:9080"):
        self.dgraph_url = dgraph_url
        self.client_stub = None
        self.client = None

    async def _get_client(self):
        if not self.client_stub or not self.client:
            self.client_stub = pydgraph.DgraphClientStub(self.dgraph_url)
            self.client = pydgraph.DgraphClient(self.client_stub)
        return self.client

    async def apply_schema(self) -> bool:
        client = await self._get_client()
        op = pydgraph.Operation(schema=self.EMBEDDED_SCHEMA)
        try:
            logging.info("Attempting to apply Dgraph schema...")
            alter_future = client.async_alter(op)
            pydgraph.DgraphClient.handle_alter_future(alter_future)
            logging.info("Dgraph schema applied successfully.")
            return True
        except Exception as e:
            logging.error(f"Error applying Dgraph schema: {e}")
            return False

    async def get_current_schema(self) -> str:
        client = await self._get_client()
        query = "schema {}"
        txn = client.txn(read_only=True)
        try:
            response = txn.query(query)
            return response.json.decode('utf-8') # Decode bytes to string
        except Exception as e:
            logging.error(f"Error retrieving schema from Dgraph: {e}")
            return ""
        finally:
            if txn:
                txn.discard()

    async def close(self):
        if self.client_stub:
            try:
                self.client_stub.close()
                logging.info("Dgraph client stub closed.")
            except Exception as e:
                logging.error(f"Error closing Dgraph client stub: {e}")

async def main():
    schema_manager = DgraphSchemaManager()
    try:
        if await schema_manager.apply_schema():
            current_schema = await schema_manager.get_current_schema()
            logging.info("Current Dgraph Schema:\n" + current_schema)
        else:
            logging.error("Failed to apply schema.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        await schema_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
