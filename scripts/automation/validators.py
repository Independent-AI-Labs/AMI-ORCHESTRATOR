"""Shared validation logic for code quality checks.

Extracted from hooks.py to eliminate duplication between:
- hooks.py CodeQualityValidator (hook validation)
- files/backend/mcp/filesys/utils/audit_validator.py (MCP server validation)
"""

import contextlib
import re
import tempfile
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from .agent_cli import (
    AgentConfigPresets,
    AgentError,
    AgentExecutionError,
    AgentTimeoutError,
    get_agent_cli,
)
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
            escaped_with_placeholder = file_match.replace("**", "__GLOB_DOUBLE_STAR__")
            regex_pattern = re.escape(escaped_with_placeholder)
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
    """Check content pattern violations (e.g., .parent.parent, suppressions).

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


def validate_diff_llm(
    file_path: str | Path,
    old_content: str,
    new_content: str,
    session_id: str,
    patterns_file: str,
) -> tuple[bool, str]:
    """LLM-based diff audit for code changes with specified pattern file.

    Args:
        file_path: Path to file
        old_content: Previous content
        new_content: New content
        session_id: Session ID for agent configuration
        patterns_file: Name of patterns file (e.g., "patterns_core.txt", "patterns_python.txt")

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
    audit_diff_template = prompts_dir / config.get("prompts.audit_diff")
    patterns_path = prompts_dir / patterns_file

    if not audit_diff_template.exists():
        # Fail-open if prompt missing
        return True, f"Audit prompt missing: {audit_diff_template} (allowed)"

    if not patterns_path.exists():
        # Fail-open if patterns missing
        return True, f"Patterns file missing: {patterns_path} (allowed)"

    # Load patterns and inject into template
    patterns_content = patterns_path.read_text()
    audit_template = audit_diff_template.read_text()
    audit_prompt = audit_template.replace("{PATTERNS}", patterns_content)

    # Write temporary prompt file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.write(audit_prompt)
        tmp_prompt_path = Path(tmp.name)

    try:
        # Run LLM-based diff audit with retry on hang
        audit_diff_config = AgentConfigPresets.audit_diff(session_id)
        audit_diff_config.enable_streaming = True
        cli = get_agent_cli()

        # Create audit log for hang detection
        execution_id = str(uuid.uuid4())[:8]
        config = get_config()
        audit_dir = config.root / "logs" / "agent-cli"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_log_path = audit_dir / f"code-quality-{patterns_file.replace('.txt', '')}-{execution_id}.log"

        output, _ = run_moderator_with_retry(
            cli=cli,
            instruction_file=tmp_prompt_path,
            stdin=diff_context,
            agent_config=audit_diff_config,
            audit_log_path=audit_log_path,
            moderator_name=f"code_quality_{patterns_file.replace('.txt', '')}",
            session_id=session_id,
            execution_id=execution_id,
            max_attempts=2,
            first_output_timeout=3.5,
        )

        # Check result - parse output for ALLOW/BLOCK
        cleaned_output = parse_code_fence_output(output)

        # Parse the decision from the output
        return _parse_audit_decision(cleaned_output, output)

    except (AgentTimeoutError, AgentExecutionError) as e:
        # FAIL-CLOSED: On timeout or execution errors, BLOCK the edit
        # This ensures quality checks are not bypassed by moderator hangs
        logger.error(
            "code_quality_moderator_error_fail_closed",
            session_id=session_id,
            execution_id=execution_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        return False, f"CODE QUALITY CHECK FAILED\n\nModerator error: {type(e).__name__}\n\nFail-closed for safety - retry operation."
    except AgentError as e:
        # Other agent errors - also fail-closed
        logger.error(
            "code_quality_moderator_error_fail_closed",
            session_id=session_id,
            execution_id=execution_id if "execution_id" in locals() else "unknown",
            error_type=type(e).__name__,
            error=str(e),
        )
        return False, f"CODE QUALITY CHECK FAILED\n\nModerator error: {type(e).__name__}\n\nFail-closed for safety - retry operation."
    finally:
        # Clean up temporary prompt file
        with contextlib.suppress(Exception):
            tmp_prompt_path.unlink()


def _parse_audit_decision(cleaned_output: str, original_output: str) -> tuple[bool, str]:
    """Parse the decision from audit output.

    Args:
        cleaned_output: Cleaned output from LLM
        original_output: Original output in case no decision marker is found

    Returns:
        Tuple of (is_valid, feedback_message)
    """
    # Strip preamble before decision marker
    # Find first occurrence of ALLOW or BLOCK: and take text from there
    allow_match = re.search(r"\bALLOW\b", cleaned_output, re.IGNORECASE)
    block_match = re.search(r"\bBLOCK:\s*", cleaned_output, re.IGNORECASE)

    if allow_match and (not block_match or allow_match.start() < block_match.start()):
        # ALLOW appears before BLOCK (or no BLOCK)
        return True, "Quality check passed"

    if block_match:
        # Extract reason after BLOCK:
        reason_start = block_match.end()
        reason = cleaned_output[reason_start:].strip()
        if not reason:
            reason = "Code quality regression detected"
        return False, f"CODE QUALITY CHECK FAILED\n\n{reason}\n\nZero-tolerance policy: NO regression allowed."

    # No decision marker found
    reason = original_output if original_output else "Code quality regression detected"
    return False, f"CODE QUALITY CHECK FAILED\n\n{reason}\n\nZero-tolerance policy: NO regression allowed."


def validate_python_diff_llm(
    file_path: str | Path,
    old_content: str,
    new_content: str,
    session_id: str,
) -> tuple[bool, str]:
    """LLM-based diff audit for Python code changes (LEGACY - uses patterns_core.txt).

    NOTE: This function is deprecated. Use validate_diff_llm with patterns_python.txt instead.

    Args:
        file_path: Path to file
        old_content: Previous content
        new_content: New content
        session_id: Session ID for agent configuration

    Returns:
        Tuple of (is_valid, feedback_message)
    """
    return validate_diff_llm(file_path, old_content, new_content, session_id, "patterns_core.txt")


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
        new_content: str
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


def _check_first_output_in_audit_log(audit_log_path: Path) -> bool:
    """Check if audit log contains first output marker.

    Args:
        audit_log_path: Path to audit log file

    Returns:
        True if first output marker found, False otherwise
    """
    if not audit_log_path or not audit_log_path.exists():
        return False

    try:
        content = audit_log_path.read_text()
        # Check for first output marker from agent CLI
        return "=== FIRST OUTPUT:" in content
    except Exception:
        return False


def _check_decision_in_output(output: str) -> bool:
    """Check if output contains a decision (ALLOW or BLOCK).

    Args:
        output: Moderator output string

    Returns:
        True if decision found, False otherwise
    """
    if not output:
        return False

    # Check for decision markers
    # Pattern matches: ALLOW or BLOCK or BLOCK: (with optional colon and reason)
    cleaned = parse_code_fence_output(output)
    return bool(re.search(r"\b(ALLOW|BLOCK)\b", cleaned, re.IGNORECASE))


def run_moderator_with_retry(
    cli: Any,
    instruction_file: Path,
    stdin: str,
    agent_config: Any,
    audit_log_path: Path | None,
    moderator_name: str,
    session_id: str,
    execution_id: str,
    max_attempts: int = 2,
    first_output_timeout: float = 3.5,
) -> tuple[str, dict[str, Any] | None]:
    """Run moderator with automatic restart if hangs during startup or analysis.

    Monitors for TWO types of hangs:
    1. **Startup hang**: No first output within first_output_timeout (default 3.5s)
       - Claude never starts streaming
       - Process appears stuck before any output

    2. **Analysis hang**: First output produced but no <decision> tag
       - Claude starts streaming (system init message)
       - But hangs during thinking/analysis phase
       - Never produces final decision output

    If either hang detected, automatically restarts (up to max_attempts total).

    Args:
        cli: Agent CLI instance
        instruction_file: Path to moderator prompt file
        stdin: Input context for moderator
        agent_config: Agent configuration
        audit_log_path: Audit log path (required for hang monitoring)
        moderator_name: Name of moderator for logging
        session_id: Session ID
        execution_id: Execution ID
        max_attempts: Maximum attempts (default 2: original + 1 restart)
        first_output_timeout: Seconds to wait for first output (default 3.5s)

    Returns:
        Tuple of (output, metadata)

    Raises:
        AgentTimeoutError: All attempts hung without first output
        AgentError: Other execution errors
    """
    if not audit_log_path:
        # No audit log - cannot monitor for first output, run directly
        result: tuple[str, dict[str, Any] | None] = cli.run_print(
            instruction_file=instruction_file,
            stdin=stdin,
            agent_config=agent_config,
            audit_log_path=audit_log_path,
        )
        return result

    # Use shorter timeout to detect hangs quickly
    original_timeout = agent_config.timeout
    hang_detection_timeout = max(int(first_output_timeout * 2), 15)  # At least 2x first_output_timeout, minimum 15s

    for attempt in range(1, max_attempts + 1):
        attempt_execution_id = f"{execution_id}-attempt{attempt}"

        # Clear audit log for this attempt
        if audit_log_path.exists():
            audit_log_path.unlink()

        logger.info(
            f"{moderator_name}_attempt_starting",
            session_id=session_id,
            execution_id=attempt_execution_id,
            attempt=attempt,
            max_attempts=max_attempts,
            timeout=hang_detection_timeout,
        )

        # Set shorter timeout for hang detection
        agent_config.timeout = hang_detection_timeout

        try:
            start_time = time.time()

            # Start moderator execution
            output, metadata = cli.run_print(
                instruction_file=instruction_file,
                stdin=stdin,
                agent_config=agent_config,
                audit_log_path=audit_log_path,
            )

            # Success - verify first output was produced
            has_first_output = _check_first_output_in_audit_log(audit_log_path)
            has_decision = _check_decision_in_output(output)
            elapsed = time.time() - start_time

            if has_first_output and has_decision:
                # Complete success
                logger.info(
                    f"{moderator_name}_attempt_success",
                    session_id=session_id,
                    execution_id=attempt_execution_id,
                    attempt=attempt,
                    elapsed=round(elapsed, 2),
                )
                agent_config.timeout = original_timeout
                return output, metadata

            if has_first_output and not has_decision:
                # Analysis hang: first output present but no decision
                if attempt < max_attempts:
                    # Kill hung process before retry
                    cli.kill_current_process()

                    logger.warning(
                        f"{moderator_name}_analysis_hang_restarting",
                        session_id=session_id,
                        execution_id=attempt_execution_id,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        reason="First output present but no decision - moderator hung during analysis",
                        output_preview=output[:500] if output else "",
                        elapsed=elapsed,
                    )
                    continue  # Retry

                # Last attempt - return output even without decision (parsing will fail-closed)
                logger.error(
                    f"{moderator_name}_analysis_hang_exhausted",
                    session_id=session_id,
                    execution_id=attempt_execution_id,
                    attempt=attempt,
                )
                agent_config.timeout = original_timeout
                return output, metadata

            # No first output but completed (shouldn't happen)
            logger.warning(
                f"{moderator_name}_no_first_output_but_completed",
                session_id=session_id,
                execution_id=attempt_execution_id,
                attempt=attempt,
            )
            agent_config.timeout = original_timeout
            return output, metadata

        except (AgentTimeoutError, AgentExecutionError) as e:
            # On timeout, always retry
            if attempt < max_attempts:
                # Kill hung process before retry
                cli.kill_current_process()

                # Check if first output was produced for logging
                has_first_output = _check_first_output_in_audit_log(audit_log_path)
                hang_type = "startup hang" if not has_first_output else "analysis hang"

                logger.warning(
                    f"{moderator_name}_timeout_restarting",
                    session_id=session_id,
                    execution_id=attempt_execution_id,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error_type=type(e).__name__,
                    hang_type=hang_type,
                    has_first_output=has_first_output,
                    elapsed=time.time() - start_time,
                )

                # Restore timeout before retry
                agent_config.timeout = original_timeout
                continue  # Retry

            # Last attempt - re-raise
            agent_config.timeout = original_timeout
            raise

        except Exception:
            # Other errors - re-raise immediately
            agent_config.timeout = original_timeout
            raise

    # All attempts exhausted without success
    raise AgentTimeoutError(
        timeout=int(hang_detection_timeout * max_attempts),
        cmd=["claude", "--print"],
        duration=float(hang_detection_timeout * max_attempts),
    )
