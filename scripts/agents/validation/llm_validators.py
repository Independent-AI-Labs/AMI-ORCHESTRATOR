"""LLM-based validation functions for code quality checks."""

import contextlib
import re
import tempfile
from pathlib import Path

from loguru import logger

from base.backend.utils.uuid_utils import uuid7
from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.cli.exceptions import AgentError, AgentExecutionError, AgentTimeoutError
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.config import get_config
from scripts.agents.validation.moderator_runner import run_moderator_with_retry
from scripts.agents.validation.pattern_validators import validate_python_patterns
from scripts.agents.validation.validation_utils import parse_code_fence_output


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

        execution_id = uuid7()[:8]
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


def validate_python_diff_llm(
    file_path: str | Path,
    old_content: str,
    new_content: str,
    session_id: str,
) -> tuple[bool, str]:
    """LLM-based diff audit for Python code changes (DEPRECATED - uses patterns_core.txt).

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
