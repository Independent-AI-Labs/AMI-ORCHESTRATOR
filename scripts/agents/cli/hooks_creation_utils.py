"""Utilities for creating hook files.

This module contains hook file creation utilities extracted from utils.py
to reduce code size and improve maintainability.
"""

import json
import tempfile
from pathlib import Path


def create_bash_only_hooks_file() -> Path:
    """Create a temporary Claude Code settings file that only allows bash commands.

    Returns:
        Path to the temporary settings JSON file
    """

    # Create Claude Code compatible settings with bash-only hooks
    bash_only_config = {
        "hooks": {
            "PreToolUse": [
                {
                    "hooks": [
                        {
                            "name": "bash_command_validator",
                            "module": "scripts.agents.workflows.security",
                            "function": "validate_bash_command",
                            "allow_bypass": False,
                        }
                    ]
                }
            ],
            "Stop": [],  # Empty Stop hook list as expected by the tests
        }
    }

    # Write to temporary JSON file for Claude Code settings
    with tempfile.NamedTemporaryFile(mode="w", suffix="_bash_settings.json", delete=False) as f:
        json.dump(bash_only_config, f)
        return Path(f.name)


def create_full_hooks_file() -> Path:
    """Create a temporary Claude Code settings file with full hook validation.

    Returns:
        Path to the temporary settings JSON file
    """

    # Create Claude Code compatible settings with hooks configuration
    settings_config = {
        "hooks": {
            "PreToolUse": [
                {
                    "hooks": [
                        {
                            "name": "bash_command_validator",
                            "module": "scripts.agents.workflows.security",
                            "function": "validate_bash_command",
                            "allow_bypass": False,
                        },
                        {
                            "name": "security_validator",
                            "module": "scripts.agents.workflows.security",
                            "function": "validate_security",
                            "allow_bypass": False,
                        },
                        {
                            "name": "quality_validator",
                            "module": "scripts.agents.workflows.quality",
                            "function": "validate_quality",
                            "allow_bypass": False,
                        },
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "hooks": [
                        {
                            "name": "response_validator",
                            "module": "scripts.agents.workflows.response",
                            "function": "validate_response",
                            "allow_bypass": False,
                        }
                    ]
                }
            ],
            "Stop": [],  # Empty Stop hook list as expected by the tests
        }
    }

    # Write to temporary JSON file for Claude Code settings
    with tempfile.NamedTemporaryFile(mode="w", suffix="_settings.json", delete=False) as f:
        json.dump(settings_config, f)
        return Path(f.name)
