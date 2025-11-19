"""Utilities for environment and privilege management.

This module contains environment and privilege-related utilities extracted from utils.py
to reduce code size and improve maintainability.
"""

import os
import pwd
from typing import Any

from loguru import logger


def drop_privileges(config: Any) -> None:
    """Drop privileges to the unprivileged user specified in config.

    Args:
        config: Configuration object containing unprivileged_user setting
    """
    unprivileged_user = config.get("unprivileged_user")
    if not unprivileged_user:
        return

    try:
        # Get user info
        user_info = pwd.getpwnam(unprivileged_user)
        uid = user_info.pw_uid
        gid = user_info.pw_gid

        # Set group first, then user (can't undo after dropping privileges)

        os.setgid(gid)
        os.setuid(uid)

        # Verify the change
        if os.getuid() != uid or os.getgid() != gid:
            raise RuntimeError("Failed to drop privileges")
    except Exception as e:
        # Log error but continue execution
        logger.error(f"Failed to drop privileges: {e}")


def get_unprivileged_env(config: Any) -> dict[str, str] | None:
    """Get environment to run subprocess with unprivileged user.

    Args:
        config: Configuration object containing unprivileged_user setting

    Returns:
        Environment dict with HOME and USER set to unprivileged user,
        or None if unprivileged user is not configured
    """
    unprivileged_user = config.get("unprivileged_user")
    if not unprivileged_user:
        return None

    try:
        user_info = pwd.getpwnam(unprivileged_user)
        env = {
            "HOME": user_info.pw_dir,
            "USER": unprivileged_user,
            "PATH": os.environ.get("PATH", ""),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        }

        # Include Claude CLI auto-update prevention environment variable
        if "DISABLE_AUTOUPDATER" in os.environ:
            env["DISABLE_AUTOUPDATER"] = os.environ["DISABLE_AUTOUPDATER"]

        return env
    except KeyError:
        # Unprivileged user doesn't exist
        return None
