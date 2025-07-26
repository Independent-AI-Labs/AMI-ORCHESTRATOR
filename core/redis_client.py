"""
Redis client for the Orchestrator.
"""

import redis

from orchestrator.core.config import Config


class RedisClient:
    """A wrapper for the redis-py client to simplify interactions with Redis."""

    def __init__(self):
        """Initialize the Redis client."""
        self._redis_client = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0)

    def publish_message(self, stream, message):
        """Publish a message to a Redis stream."""
        return self._redis_client.xadd(stream, message)

    def read_messages(self, stream, count=1, block=0):
        """Read messages from a Redis stream."""
        return self._redis_client.xread({stream: 0}, count=count, block=block)

    def publish_to_dead_letter_queue(self, task, error):
        """Publish a failed task to the dead-letter queue."""
        return self._redis_client.xadd("dead_letter_queue", {"task": task, "error": error})

    def delete(self, key):
        """Delete a key from Redis."""
        return self._redis_client.delete(key)
