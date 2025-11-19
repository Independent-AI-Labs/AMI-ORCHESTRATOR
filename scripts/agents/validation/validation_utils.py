"""Basic validation utilities and helper functions."""

import re
from functools import lru_cache
from typing import Any

import yaml

from scripts.agents.config import get_config

# Code fence parsing
MIN_CODE_FENCE_LINES = 2  # Minimum lines for valid code fence (opening + closing)


@lru_cache(maxsize=1)
def load_python_patterns() -> list[dict[str, Any]]:
    """Load Python fast pattern validation rules from YAML.

    Returns:
        List of pattern dictionaries from python_fast.yaml

    Raises:
        FileNotFoundError: If python_fast.yaml doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    config = get_config()
    patterns_dir = config.root / "scripts/config/patterns"
    patterns_file = patterns_dir / "python_fast.yaml"

    if not patterns_file.exists():
        # Fail-open if patterns file missing (don't block development)
        return []

    with patterns_file.open() as f:
        data = yaml.safe_load(f)

    result: list[dict[str, Any]] = data.get("patterns", [])
    return result


@lru_cache(maxsize=1)
def load_bash_patterns() -> list[dict[str, str]]:
    """Load Bash command validation patterns from YAML.

    Returns:
        List of pattern dictionaries from bash_commands.yaml

    Raises:
        FileNotFoundError: If bash_commands.yaml doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    config = get_config()
    patterns_dir = config.root / "scripts/config/patterns"
    patterns_file = patterns_dir / "bash_commands.yaml"

    if not patterns_file.exists():
        # Fail-open if patterns file missing (don't block development)
        return []

    with patterns_file.open() as f:
        data = yaml.safe_load(f)

    result: list[dict[str, str]] = data.get("deny_patterns", [])
    return result


@lru_cache(maxsize=1)
def load_exemptions() -> set[str]:
    """Load file exemptions from YAML.

    Returns:
        Set of file paths exempt from pattern checks

    Raises:
        FileNotFoundError: If exemptions.yaml doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    config = get_config()
    patterns_dir = config.root / "scripts/config/patterns"
    exemptions_file = patterns_dir / "exemptions.yaml"

    if not exemptions_file.exists():
        # Fail-open if exemptions file missing (don't block development)
        return set()

    with exemptions_file.open() as f:
        data = yaml.safe_load(f)

    return set(data.get("pattern_check_exemptions", []))


def parse_code_fence_output(output: str) -> str:
    """Parse output, removing markdown code fences if present.

    Args:
        output: Raw output from LLM

    Returns:
        Cleaned output with code fences removed
    """
    cleaned = output.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if len(lines) > MIN_CODE_FENCE_LINES and lines[-1] == "```":
            cleaned = "\n".join(lines[1:-1]).strip()
        elif len(lines) > 1:
            cleaned = "\n".join(lines[1:]).strip()
    return cleaned


def count_pattern_occurrences(content: str, pattern_str: str, is_regex: bool = False) -> int:
    """Count occurrences of a pattern string in content.

    Args:
        content: Content to search
        pattern_str: Pattern string to count (literal or regex depending on is_regex)
        is_regex: If True, treat pattern_str as regex; otherwise literal string

    Returns:
        Count of occurrences
    """
    if is_regex:
        return len(re.findall(pattern_str, content))
    return content.count(pattern_str)
