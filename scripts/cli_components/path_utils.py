#!/usr/bin/env python3
"""Path utilities for git repository server management CLI."""

import os
from pathlib import Path


def get_base_path() -> Path:
    """Get git server base path from environment or default.

    Returns:
        Base path for git repositories (default: ~/git-repos)
    """
    env_path = os.getenv("GIT_SERVER_BASE_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / "git-repos"
