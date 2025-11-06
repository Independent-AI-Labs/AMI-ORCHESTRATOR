"""Shared validation logic for code quality checks.

Extracted from hooks.py to eliminate duplication between:
- hooks.py CodeQualityValidator (hook validation)
- files/backend/mcp/filesys/utils/audit_validator.py (MCP server validation)
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .agent_cli import AgentConfigPresets, AgentError, get_agent_cli
from .config import get_config

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

    # File content check (e.g., non-empty __init__.py)
    if check_type == "file_content":
        file_match = pattern_config.get("file_match", "")
        condition = pattern_config.get("condition")

        # Check if file matches pattern
        regex_pattern = file_match.replace("**", ".*").replace("*", "[^/]*")
        if not re.search(regex_pattern, file_path):
            return False, ""

        # Check condition
        if condition == "not_empty" and new_content.strip():
            error_msg = pattern_config.get("error_template", "Pattern violation detected")
            return True, error_msg

        return False, ""

    # Content pattern check (e.g., .parent.parent, suppressions)
    if check_type == "content_pattern":
        patterns = pattern_config.get("patterns", [pattern_config.get("pattern")])
        allow_removal = pattern_config.get("allow_removal", False)
        is_regex = pattern_config.get("is_regex", False)

        # Check for violations
        for pattern_str in patterns:
            if pattern_str is None:
                continue

            if allow_removal:
                # Only block ADDITIONS - compare old vs new count
                old_count = count_pattern_occurrences(old_content, pattern_str, is_regex)
                new_count = count_pattern_occurrences(new_content, pattern_str, is_regex)

                if new_count > old_count:
                    # Addition detected - check exemptions
                    if check_pattern_exemption(file_path, pattern_config):
                        # File is in exemption path, check if pattern is allowed
                        exemptions = pattern_config.get("exemptions", [])
                        for exemption in exemptions:
                            allowed_patterns = exemption.get("allowed_patterns", [])
                            allowed_regex = exemption.get("allowed_pattern_regex")

                            # Check if the specific pattern is allowed
                            if pattern_str in allowed_patterns:
                                continue  # This pattern is allowed

                            # Check regex exemption
                            if allowed_regex and re.search(allowed_regex, new_content):
                                continue  # Matches allowed regex

                        # No exemption matched, it's a violation
                        error_msg = pattern_config.get("error_template", "Pattern violation detected")
                        return True, error_msg
                    # Not in exemption path, it's a violation
                    error_msg = pattern_config.get("error_template", "Pattern violation detected")
                    return True, error_msg
            # Block if present in new content (regardless of old content)
            elif is_regex:
                if re.search(pattern_str, new_content):
                    error_msg = pattern_config.get("error_template", "Pattern violation detected")
                    return True, error_msg
            elif pattern_str in new_content:
                error_msg = pattern_config.get("error_template", "Pattern violation detected")
                return True, error_msg

        return False, ""

    # Unknown check type
    return False, ""


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


def validate_python_patterns(
    file_path: str | Path,
    old_content: str,
    new_content: str,
) -> tuple[bool, str]:
    """Fast pattern-based validation for Python files.

    Checks for common issues that don't require LLM analysis:
    - Non-empty __init__.py files
    - .parent.parent path manipulation
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


def validate_python_diff_llm(
    file_path: str | Path,
    old_content: str,
    new_content: str,
    session_id: str,
) -> tuple[bool, str]:
    """LLM-based diff audit for Python code changes.

    Args:
        file_path: Path to file
        old_content: Previous content
        new_content: New content
        session_id: Session ID for agent configuration

    Returns:
        Tuple of (is_valid, feedback_message)

    Raises:
        Exception: Non-AgentError exceptions are re-raised
    """
    # Build diff context
    diff_context = f"""FILE: {file_path}

## OLD CODE
```
{old_content}
```

## NEW CODE
```
{new_content}
```
"""

    # Get configuration and paths
    config = get_config()
    prompts_dir = config.root / config.get("prompts.dir")
    audit_diff_instruction = prompts_dir / config.get("prompts.audit_diff")

    if not audit_diff_instruction.exists():
        # Fail-open if prompt missing
        return True, f"Audit prompt missing: {audit_diff_instruction} (allowed)"

    # Run LLM-based diff audit
    cli = get_agent_cli()

    try:
        audit_diff_config = AgentConfigPresets.audit_diff(session_id)
        audit_diff_config.enable_streaming = True
        output, _ = cli.run_print(
            instruction_file=audit_diff_instruction,
            stdin=diff_context,
            agent_config=audit_diff_config,
        )

        # Check result - parse output for PASS/FAIL
        cleaned_output = parse_code_fence_output(output)

        # Check if PASS appears in the cleaned output
        if re.search(r"\bPASS\b", cleaned_output, re.IGNORECASE):
            return True, "Quality check passed"

        # Extract failure reason from output
        reason = output if output else "Code quality regression detected"
        return False, f"❌ CODE QUALITY CHECK FAILED\n\n{reason}\n\nZero-tolerance policy: NO regression allowed."

    except AgentError:
        # On agent errors (timeout, execution failure), allow the edit
        # This prevents infrastructure failures from blocking legitimate work
        return True, "Agent infrastructure error (allowed)"


def validate_python_full(
    file_path: str | Path,
    old_content: str,
    new_content: str,
    session_id: str,
) -> tuple[bool, str]:
    """Full Python validation: patterns + LLM diff audit.

    Args:
        file_path: Path to file
        old_content: Previous content
        new_content: New content
        session_id: Session ID for agent configuration

    Returns:
        Tuple of (is_valid, feedback_message)
    """
    # Pattern validation first (fast)
    is_valid, reason = validate_python_patterns(file_path, old_content, new_content)
    if not is_valid:
        return False, reason

    # LLM diff audit (slow but comprehensive)
    return validate_python_diff_llm(file_path, old_content, new_content, session_id)
