"""
Unit tests for the RedisClient class.
"""

import unittest
from unittest.mock import patch

from orchestrator.core.config import Config
from orchestrator.core.redis_client import RedisClient


class TestRedisClient(unittest.TestCase):
    """Unit tests for the RedisClient class."""

    @patch("redis.Redis")
    def test_init(self, mock_redis):
        """Test the __init__ method."""
        client = RedisClient()
        self.assertIsNotNone(client)
        mock_redis.assert_called_with(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0)

    @patch("redis.Redis")
    def test_publish_message(self, _):
        """Test the publish_message method."""
        client = RedisClient()
        stream = "my_stream"
        message = {"hello": "world"}
        client.publish_message(stream, message)
        # pylint: disable=protected-access
        client._redis_client.xadd.assert_called_once_with(stream, message)

    @patch("redis.Redis")
    def test_read_messages(self, _):
        """Test the read_messages method."""
        client = RedisClient()
        stream = "my_stream"
        client.read_messages(stream)
        # pylint: disable=protected-access
        client._redis_client.xread.assert_called_once_with({stream: 0}, count=1, block=0)

    @patch("redis.Redis")
    def test_publish_to_dead_letter_queue(self, _):
        """Test the publish_to_dead_letter_queue method."""
        client = RedisClient()
        task = "my_task"
        error = "my_error"
        client.publish_to_dead_letter_queue(task, error)
        # pylint: disable=protected-access
        client._redis_client.xadd.assert_called_once_with("dead_letter_queue", {"task": task, "error": error})

    @patch("redis.Redis")
    def test_delete(self, _):
        """Test the delete method."""
        client = RedisClient()
        key = "my_key"
        client.delete(key)
        # pylint: disable=protected-access
        client._redis_client.delete.assert_called_once_with(key)


if __name__ == "__main__":
    unittest.main()
