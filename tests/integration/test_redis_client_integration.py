"""
Integration tests for the RedisClient class against a live Redis instance.
"""

import unittest

from orchestrator.core.config import Config
from orchestrator.core.redis_client import RedisClient


class TestRedisClientIntegration(unittest.TestCase):
    """Integration tests for the RedisClient class."""

    def setUp(self):
        """Set up the test case."""
        self.client = RedisClient()
        self.stream_name = "test_stream"
        # Clean up any previous test data
        self.client.delete(self.stream_name)

    def tearDown(self):
        """Tear down the test case."""
        self.client.delete(self.stream_name)

    def test_publish_and_read_message(self):
        """Test publishing and reading a message from a Redis stream."""
        # 1. Publish Message
        message = {"hello": "world"}
        self.client.publish_message(self.stream_name, message)

        # 2. Read Message
        response = self.client.read_messages(self.stream_name)
        self.assertIsNotNone(response)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0][1][0][1], {b"hello": b"world"})


if __name__ == "__main__":
    unittest.main()
