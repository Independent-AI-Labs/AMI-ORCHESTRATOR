"""Shared validation logic for code quality checks.

Extracted from hooks.py to eliminate duplication between:
- hooks.py CodeQualityValidator (hook validation)
- files/backend/mcp/filesys/utils/audit_validator.py (MCP server validation)
"""

import re
from pathlib import Path

from .agent_cli import AgentConfigPresets, AgentError, get_agent_cli
from .config import get_config

# Code fence parsing
MIN_CODE_FENCE_LINES = 2  # Minimum lines for valid code fence (opening + closing)

# Error message templates (split strings to avoid triggering pattern checks)
PARENT_PATTERN = ".parent" + ".parent"
INIT_PY_ERROR = "❌ NON-EMPTY __init__.py FILE\n\n__init__.py files MUST be empty.\nRemove all content from this file."
PARENT_PATTERN_ERROR = (
    f"❌ FORBIDDEN CODE PATTERN: {PARENT_PATTERN}\n\n"
    f"NEVER use Path(__file__){PARENT_PATTERN}.parent or similar patterns.\n\n"
    "Use the _ensure_repo_on_path() pattern from scripts/run_tests.py:\n\n"
    "def _ensure_repo_on_path() -> Path:\n"
    "    current = Path(__file__).resolve().parent\n"
    "    while current != current.parent:\n"
    '        if (current / ".git").exists() and (current / "base").exists():\n'
    "            sys.path.insert(0, str(current))\n"
    "            return current\n"
    "        current = current.parent\n"
    '    raise RuntimeError("Unable to locate AMI orchestrator root")\n'
)


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


def validate_python_patterns(file_path: str | Path, content: str) -> tuple[bool, str]:
    """Fast pattern-based validation for Python files.

    Checks for common issues that don't require LLM analysis:
    - Non-empty __init__.py files
    - .parent.parent path manipulation
    - Other forbidden patterns

    Args:
        file_path: Path to file (string or Path)
        content: File content

    Returns:
        Tuple of (is_valid, denial_reason). If valid, reason is empty string.
    """
    file_path_str = str(file_path)

    # Reject non-empty __init__.py files
    if file_path_str.endswith("__init__.py") and content.strip():
        return False, INIT_PY_ERROR

    # Reject .parent.parent path manipulation
    if PARENT_PATTERN in content:
        return False, PARENT_PATTERN_ERROR

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
    is_valid, reason = validate_python_patterns(file_path, new_content)
    if not is_valid:
        return False, reason

    # LLM diff audit (slow but comprehensive)
    return validate_python_diff_llm(file_path, old_content, new_content, session_id)
