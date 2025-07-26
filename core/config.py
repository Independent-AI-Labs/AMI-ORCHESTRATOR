"""
Configuration management for the Orchestrator.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Orchestrator configuration."""

    DGRAPH_HOST = os.environ.get("DGRAPH_HOST", "localhost")
    DGRAPH_PORT = int(os.environ.get("DGRAPH_PORT", "9080"))
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
    PROMETHEUS_HOST = os.environ.get("PROMETHEUS_HOST", "localhost")
    PROMETHEUS_PORT = int(os.environ.get("PROMETHEUS_PORT", "8000"))
