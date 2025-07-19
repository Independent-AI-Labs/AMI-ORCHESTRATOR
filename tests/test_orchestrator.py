import unittest
from unittest.mock import MagicMock
from src.orchestration.orchestrator import Orchestrator
from src.dgraph.dgraph_store import DgraphStore

class TestOrchestrator(unittest.TestCase):
    def test_init(self):
        # Arrange
        mock_dgraph_store = MagicMock(spec=DgraphStore)
        mock_task_queue = MagicMock()

        # Act
        orchestrator = Orchestrator(mock_dgraph_store, mock_task_queue)

        # Assert
        self.assertEqual(orchestrator.dgraph_store, mock_dgraph_store)
        self.assertEqual(orchestrator.task_queue, mock_task_queue)

    def test_delegate(self):
        # Arrange
        mock_dgraph_store = MagicMock(spec=DgraphStore)
        mock_task_queue = MagicMock()
        orchestrator = Orchestrator(mock_dgraph_store, mock_task_queue)
        task = "test_task"
        agent = "test_agent"

        # Act
        orchestrator.delegate(task, agent)

        # Assert
        mock_task_queue.send_task.assert_called_once_with('agent.execute', args=[task, agent])

if __name__ == '__main__':
    unittest.main()
