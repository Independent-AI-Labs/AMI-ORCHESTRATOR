import unittest
from unittest.mock import MagicMock
from src.agents.base import BaseAgent
from src.dgraph.dgraph_store import DgraphStore

class ConcreteAgent(BaseAgent):
    def execute(self, task):
        pass

class TestBaseAgent(unittest.TestCase):
    def test_init(self):
        # Arrange
        mock_dgraph_store = MagicMock(spec=DgraphStore)

        # Act
        agent = ConcreteAgent(mock_dgraph_store)

        # Assert
        self.assertEqual(agent.dgraph_store, mock_dgraph_store)

if __name__ == '__main__':
    unittest.main()
