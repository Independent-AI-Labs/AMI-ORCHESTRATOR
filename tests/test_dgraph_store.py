import unittest
from unittest.mock import MagicMock, patch
from src.dgraph.dgraph_store import DgraphStore

class TestDgraphStore(unittest.TestCase):
    @patch('pydgraph.DgraphClient')
    @patch('pydgraph.DgraphClientStub')
    def test_set_schema(self, mock_client_stub, mock_client):
        # Arrange
        mock_client_instance = mock_client.return_value
        dgraph_store = DgraphStore()

        # Act
        with open('src/dgraph/schema.dql', 'r') as f:
            schema = f.read()
        dgraph_store.set_schema(schema)

        # Assert
        mock_client_instance.alter.assert_called_once()

if __name__ == '__main__':
    unittest.main()
