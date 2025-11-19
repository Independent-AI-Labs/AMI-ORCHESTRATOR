"""Pattern-based validation functions for code quality checks."""

import re
from pathlib import Path
from typing import Any

from scripts.agents.validation.validation_utils import count_pattern_occurrences, load_python_patterns


def check_pattern_exemption(file_path: str, pattern_config: dict[str, Any]) -> bool:
    """Check if file is exempt from a specific pattern check.

    Args:
        file_path: Path to file being checked
        pattern_config: Pattern configuration dictionary

    Returns:
        True if file is exempt from this pattern
    """
    exemptions = pattern_config.get("exemptions", [])

    for exemption in exemptions:
        path_patterns = exemption.get("path_patterns", [])

        # Check if file matches any exemption path pattern
        for path_pattern in path_patterns:
            # Convert glob pattern to regex
            regex_pattern = path_pattern.replace("**", ".*").replace("*", "[^/]*")
            if re.search(regex_pattern, file_path):
                # File matches exemption path, now check pattern-specific rules
                exemption.get("allowed_patterns", [])
                exemption.get("allowed_pattern_regex")

                # If there are specific allowed patterns, the pattern must match one
                # This is handled by the caller (check_pattern_violation)
                return True

    return False


def _check_file_content_violation(
    file_path: str,
    new_content: str,
    pattern_config: dict[str, Any],
) -> tuple[bool, str]:
    """Check file content pattern violations (e.g., non-empty __init__.py).

    Args:
        file_path: Path to file being checked
        new_content: New content
        pattern_config: Pattern configuration dictionary

    Returns:
        Tuple of (is_violation, error_message). If no violation, error_message is empty.
    """
    file_match = pattern_config.get("file_match", "")
    condition = pattern_config.get("condition")

    # Check if file matches pattern
    # Convert glob pattern to regex properly
    # For **, we want to match zero or more directories followed by /

    # For **/__init__.py -> (.*?/)?__init\.py (optional directory path)
    # Replace ** patterns first before escaping
    if "**" in file_match:
        # Handle the case where ** appears at the start (meaning zero or more dirs)
        if file_match.startswith("**/"):
            pattern_suffix = file_match[3:]  # Get part after '**/'
            # Create regex that optionally matches any directory path followed by the suffix
            regex_pattern = f"^(.*?/)?{re.escape(pattern_suffix)}$"
        else:
            # More complex glob pattern, escape and convert
            escaped_with_intermediate = file_match.replace("**", "__GLOB_DOUBLE_STAR__")
            regex_pattern = re.escape(escaped_with_intermediate)
            regex_pattern = regex_pattern.replace("__GLOB_DOUBLE_STAR__", ".*")
            regex_pattern = regex_pattern.replace(r"\*", "[^/]*")
            regex_pattern = f"^{regex_pattern}$"
    else:
        # No ** patterns, just handle * normally
        regex_pattern = f"^{re.escape(file_match).replace(r'*', '[^/]*')}$"

    if not re.search(regex_pattern, file_path):
        return False, ""

    # Check condition
    if condition == "not_empty" and new_content.strip():
        error_msg = pattern_config.get("error_template", "Pattern violation detected")
        return True, error_msg

    return False, ""


def _check_additions_violation(
    pattern_str: str,
    old_content: str,
    new_content: str,
    is_regex: bool,
    file_path: str,
    pattern_config: dict[str, Any],
) -> tuple[bool, str]:
    """Check for addition violations when allow_removal is True.

    Args:
        pattern_str: Pattern to check
        old_content: Previous content
        new_content: New content
        is_regex: Whether pattern is a regex
        file_path: Path to file being checked
        pattern_config: Pattern configuration dictionary

    Returns:
        Tuple of (is_violation, error_message)
    """
    # Only block ADDITIONS - compare old vs new count
    old_count = count_pattern_occurrences(old_content, pattern_str, is_regex)
    new_count = count_pattern_occurrences(new_content, pattern_str, is_regex)

    if new_count <= old_count:
        return False, ""  # No addition detected

    # Addition detected - check exemptions
    if check_pattern_exemption(file_path, pattern_config):
        # File is in exemption path, check if pattern is allowed
        return _check_exemptions_for_pattern(pattern_str, new_content, pattern_config)

    # Not in exemption path, it's a violation
    error_msg = pattern_config.get("error_template", "Pattern violation detected")
    return True, error_msg


def _check_exemptions_for_pattern(
    pattern_str: str,
    new_content: str,
    pattern_config: dict[str, Any],
) -> tuple[bool, str]:
    """Check if a pattern is exempted based on the pattern config.

    Args:
        pattern_str: Pattern to check
        new_content: New content
        pattern_config: Pattern configuration dictionary

    Returns:
        Tuple of (is_violation, error_message)
    """
    exemptions = pattern_config.get("exemptions", [])
    for exemption in exemptions:
        allowed_patterns = exemption.get("allowed_patterns", [])
        allowed_regex = exemption.get("allowed_pattern_regex")

        # Check if the specific pattern is allowed
        if pattern_str in allowed_patterns:
            return False, ""  # This pattern is allowed

        # Check regex exemption
        if allowed_regex and re.search(allowed_regex, new_content):
            return False, ""  # Matches allowed regex

    # No exemption matched, it's a violation
    error_msg = pattern_config.get("error_template", "Pattern violation detected")
    return True, error_msg


def _check_presence_violation(
    pattern_str: str,
    new_content: str,
    is_regex: bool,
    pattern_config: dict[str, Any],
) -> tuple[bool, str]:
    """Check for presence violations when allow_removal is False.

    Args:
        pattern_str: Pattern to check
        new_content: New content
        is_regex: Whether pattern is a regex
        pattern_config: Pattern configuration dictionary

    Returns:
        Tuple of (is_violation, error_message)
    """
    if is_regex:
        if re.search(pattern_str, new_content):
            error_msg = pattern_config.get("error_template", "Pattern violation detected")
            return True, error_msg
    elif pattern_str in new_content:
        error_msg = pattern_config.get("error_template", "Pattern violation detected")
        return True, error_msg

    return False, ""  # No violation


def _check_content_pattern_violation(
    file_path: str,
    old_content: str,
    new_content: str,
    pattern_config: dict[str, Any],
) -> tuple[bool, str]:
    """Check content pattern violations (e.g., relative path traversal, suppressions).

    Args:
        file_path: Path to file being checked
        old_content: Previous content
        new_content: New content
        pattern_config: Pattern configuration dictionary

    Returns:
        Tuple of (is_violation, error_message). If no violation, error_message is empty.
    """
    patterns = pattern_config.get("patterns", [pattern_config.get("pattern")])
    allow_removal = pattern_config.get("allow_removal", False)
    is_regex = pattern_config.get("is_regex", False)

    # Check for violations
    for pattern_str in patterns:
        if pattern_str is None:
            continue

        if allow_removal:
            violation_detected, error_msg = _check_additions_violation(pattern_str, old_content, new_content, is_regex, file_path, pattern_config)
            if violation_detected:
                return True, error_msg
        else:
            # Block if present in new content (regardless of old content)
            violation_detected, error_msg = _check_presence_violation(pattern_str, new_content, is_regex, pattern_config)
            if violation_detected:
                return True, error_msg

    return False, ""


def check_pattern_violation(
    file_path: str,
    old_content: str,
    new_content: str,
    pattern_config: dict[str, Any],
) -> tuple[bool, str]:
    """Check if a pattern violation exists in the content change.

    Args:
        file_path: Path to file being checked
        old_content: Previous content
        new_content: New content
        pattern_config: Pattern configuration dictionary

    Returns:
        Tuple of (is_violation, error_message). If no violation, error_message is empty.
    """
    check_type = pattern_config.get("check_type")

    if check_type == "file_content":
        return _check_file_content_violation(file_path, new_content, pattern_config)
    if check_type == "content_pattern":
        return _check_content_pattern_violation(file_path, old_content, new_content, pattern_config)
    # Unknown check type
    return False, ""


def validate_python_patterns(
    file_path: str | Path,
    old_content: str,
    new_content: str,
) -> tuple[bool, str]:
    """Fast pattern-based validation for Python files.

    Checks for common issues that don't require LLM analysis:
    - Non-empty __init__.py files
    - Relative path traversal
    - Code quality suppressions without justification
    - Other forbidden patterns (loaded from YAML)

    Args:
        file_path: Path to file (string or Path)
        old_content: Previous content (for detecting additions vs removals)
        new_content: New content

    Returns:
        Tuple of (is_valid, denial_reason). If valid, reason is empty string.
    """
    file_path_str = str(file_path)

    # Load patterns from YAML
    patterns = load_python_patterns()

    # Check each pattern
    for pattern_config in patterns:
        is_violation, error_msg = check_pattern_violation(
            file_path_str,
            old_content,
            new_content,
            pattern_config,
        )

        if is_violation:
            return False, error_msg

    return True, ""
