"""
Integration tests for the DgraphClient class against a live Dgraph instance.
"""

import unittest

import pydgraph

from orchestrator.core.dgraph_client import DgraphClient


class TestDgraphClientIntegration(unittest.TestCase):
    """Integration tests for the DgraphClient class."""

    def setUp(self):
        """Set up the test case."""
        self.client = DgraphClient()
        op = pydgraph.Operation(drop_all=True)
        self.client.alter(op)

    def tearDown(self):
        """Tear down the test case."""
        op = pydgraph.Operation(drop_all=True)
        self.client.alter(op)
        self.client.close()

    def test_alter_schema_and_query(self):
        """Test altering the schema, mutating, and querying."""
        # 1. Alter Schema
        schema = "name: string @index(exact) ."
        op = pydgraph.Operation(schema=schema)
        self.client.alter(op)

        # 2. Mutate Data
        mutation = {"name": "Test Process"}
        response = self.client.mutate(mutation)
        uid = list(response.uids.values())[0]
        self.assertIsNotNone(uid)

        # 3. Query Data
        query = f"""query test_query($a: string) {{
            q(func: eq(name, $a)) {{
                uid
                name
            }}
        }}"""
        variables = {"$a": "Test Process"}
        response = self.client.query(query, variables=variables)
        self.assertIn("Test Process", str(response.json))


if __name__ == "__main__":
    unittest.main()
