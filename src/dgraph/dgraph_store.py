import pydgraph

class DgraphStore:
    def __init__(self, dgraph_uri: str = "localhost:9080"):
        self.client_stub = pydgraph.DgraphClientStub(dgraph_uri)
        self.client = pydgraph.DgraphClient(self.client_stub)

    def close(self):
        self.client_stub.close()

    def set_schema(self, schema: str):
        return self.client.alter(pydgraph.Operation(schema=schema))
