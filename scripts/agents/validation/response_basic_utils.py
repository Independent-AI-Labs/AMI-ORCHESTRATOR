"""Basic response validation utilities - message parsing and checks."""

import json
import re
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from scripts.agents.config import get_config
from scripts.agents.validation.core import HookResult


def _load_response_validation_patterns() -> dict[str, Any]:
    """Load response validation patterns from YAML config.

    Returns:
        Dictionary containing prohibited patterns and other validation rules
    """
    config = get_config()
    patterns_dir = config.root / "scripts/config/patterns"
    patterns_file = patterns_dir / "prohibited_communication_patterns.yaml"

    if not patterns_file.exists():
        # Return empty dict if config doesn't exist
        return {"prohibited_patterns": []}

    with patterns_file.open() as f:
        result: dict[str, Any] = yaml.safe_load(f)
        return result


def check_prohibited_patterns(last_message: str) -> HookResult | None:
    """Check if the message contains prohibited patterns.

    Args:
        last_message: The last assistant message

    Returns:
        HookResult if prohibited pattern found, None otherwise
    """
    # Load patterns from config
    patterns_config = _load_response_validation_patterns()
    prohibited_patterns = patterns_config.get("prohibited_patterns", [])

    # Apply communication rules
    for pattern_config in prohibited_patterns:
        pattern = pattern_config.get("pattern", "")
        description = pattern_config.get("description", "")

        if re.search(pattern, last_message, re.IGNORECASE):
            return HookResult.block(
                f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                f"Hook: Stop\n"
                f"Validator: ResponseScanner\n\n"
                f'CRITICAL COMMUNICATION RULES VIOLATION: "{description}" detected.\n\n'
                '- NEVER say "The issue is clear", "You are right", "I see the problem", '
                "or similar definitive statements without FIRST reading and verifying the actual source code/data.\n"
                "- ALWAYS scrutinize everything. NEVER assume. ALWAYS check before making claims.\n"
                "- If you don't know something or haven't verified it, say so explicitly.\n\n"
                "Verify the source code/data before making claims."
            )
    return None


def check_api_limit_messages(last_message: str) -> tuple[bool, HookResult | None]:
    """Check if message contains API limit messages that should be allowed.

    Args:
        last_message: The last assistant message

    Returns:
        Tuple of (is_api_limit_message, result_if_api_limit)
    """
    # Load API limit patterns from config
    patterns_config = _load_response_validation_patterns()
    api_limit_patterns = patterns_config.get("api_limit_patterns", [])

    # Extract patterns from config
    limit_patterns = [pattern_config.get("pattern", "") for pattern_config in api_limit_patterns]

    # Check for API limit messages - allow without completion marker
    for pattern in limit_patterns:
        if re.search(pattern, last_message, re.IGNORECASE):
            return True, HookResult.allow()
    return False, None


def get_last_assistant_message(transcript_path: Path) -> str:
    """Get last assistant message from transcript.

    Args:
        transcript_path: Path to transcript file

    Returns:
        Last assistant message text
    """
    last_text = ""
    for line in transcript_path.read_text().splitlines():
        try:
            msg = json.loads(line)
            if msg.get("type") == "assistant":
                # Extract text content
                for content in msg.get("message", {}).get("content", []):
                    if content.get("type") == "text":
                        last_text = content.get("text", "")
        except Exception as e:
            # Skip invalid lines

            logger.warning("transcript_parse_error", line=line[:100], error=str(e))
            continue
    return last_text


def is_greeting_exchange(last_message: str) -> bool:
    """Check if the transcript contains only a greeting exchange.

    Args:
        last_message: Last assistant message text

    Returns:
        True if this appears to be a greeting exchange, False otherwise
    """
    # Load greeting patterns from config
    patterns_config = _load_response_validation_patterns()
    greeting_patterns = patterns_config.get("greeting_patterns", [])

    # Extract patterns from config
    greeting_regexes = [pattern_config.get("pattern", "") for pattern_config in greeting_patterns]

    last_lower = last_message.lower().strip()
    return any(re.search(pattern, last_lower) for pattern in greeting_regexes)
