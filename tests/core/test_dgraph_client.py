"""
Unit tests for the DgraphClient class.
"""

import unittest
from unittest.mock import MagicMock, patch

import pydgraph

from orchestrator.core.dgraph_client import DgraphClient


class TestDgraphClient(unittest.TestCase):
    """Unit tests for the DgraphClient class."""

    @patch("pydgraph.DgraphClient")
    def setUp(self, mock_dgraph_client):
        """Set up the test case."""
        self.client = DgraphClient()
        self.client._dgraph_client = mock_dgraph_client

    def test_alter(self):
        """Test the alter method."""
        op = pydgraph.Operation(schema="name: string .")
        self.client.alter(op)
        self.client._dgraph_client.alter.assert_called_once_with(op)

    def test_mutate(self):
        """Test the mutate method."""
        mock_txn = MagicMock()
        self.client._dgraph_client.txn.return_value = mock_txn
        mutation = {"name": "test"}
        self.client.mutate(mutation)
        self.client._dgraph_client.txn.assert_called_once()
        mock_txn.mutate.assert_called_once_with(set_obj=mutation)
        mock_txn.commit.assert_called_once()

    def test_query(self):
        """Test the query method."""
        mock_txn = MagicMock()
        self.client._dgraph_client.txn.return_value = mock_txn
        query = "{ q(func: has(name)) { name } }"
        self.client.query(query)
        self.client._dgraph_client.txn.assert_called_once_with(read_only=True)
        mock_txn.query.assert_called_once_with(query, variables=None)


if __name__ == "__main__":
    unittest.main()
