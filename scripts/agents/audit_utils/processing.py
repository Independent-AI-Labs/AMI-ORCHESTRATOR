"""Audit utility functions extracted from audit.py."""

from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

# Import at the top to avoid circular imports
from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.config import get_config


def parse_audit_output(
    output: str, file_path: Path
) -> tuple[str, list[dict[str, Any]]]:  # Any: violation dicts have mixed types (line: int, message: str, severity: str, pattern_id: str)
    """Parse audit output from LLM into status and violations.

    Args:
        output: Raw output from audit agent
        file_path: File path being audited (for logging)

    Returns:
        Tuple of (status, violations list)
    """
    # Import at function start to avoid circular import

    output_stripped = output.strip()

    # Check for PASS (exact match)
    if output_stripped == "PASS":
        return "PASS", []

    # Check for FAIL anywhere in output (extract from LLM preamble if needed)
    if "FAIL:" in output_stripped:
        # Extract FAIL line (may be buried in preamble)
        fail_line = None
        for line in output_stripped.split("\n"):
            if line.startswith("FAIL:"):
                fail_line = line
                break

        if fail_line:
            violations = [{"line": 0, "pattern_id": "llm_audit", "severity": "CRITICAL", "message": fail_line}]
        else:
            # FAIL: found but not at line start, use full output
            violations = [{"line": 0, "pattern_id": "llm_audit", "severity": "CRITICAL", "message": output_stripped}]
        return "FAIL", violations

    # Check for ERROR
    if "ERROR:" in output_stripped:
        violations = [{"line": 0, "pattern_id": "audit_error", "severity": "ERROR", "message": output_stripped}]
        return "ERROR", violations

    # Non-compliant output format - treat as ERROR
    first_line = output_stripped.split("\n")[0] if output_stripped else ""
    violations = [
        {
            "line": 0,
            "pattern_id": "audit_format_violation",
            "severity": "ERROR",
            "message": f"Audit agent violated output format. Expected 'PASS' or 'FAIL: <reasons>', got: {first_line[:200]}",
        }
    ]

    logger.error("audit_output_format_violation", file=str(file_path), first_line=first_line[:100])
    return "ERROR", violations


def save_report(result: Any, root_dir: Path, output_dir: Path) -> None:  # Any: UnifiedExecutionResult type
    """Save audit report with mirrored directory structure.

    Args:
        result: Audit result
        root_dir: Root directory being audited
        output_dir: Output directory (e.g., docs/audit/DD.MM.YYYY)

    Example:
        automation/config.py -> docs/audit/18.10.2025/automation/config.py.md
    """
    # Create relative path for mirrored structure
    try:
        rel_path = result.item_path.relative_to(root_dir)
    except ValueError:
        rel_path = Path(result.item_path.name)

    # Mirror directory structure
    report_path = output_dir / rel_path.with_suffix(rel_path.suffix + ".md")

    # Create parent directories
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # Format violations
    violations_text = ""
    if result.violations:
        violations_text = "\n".join([f"- Line {v['line']}: {v['message']} (severity: {v['severity']})" for v in result.violations])
    elif result.executor_metadata and "violations" in result.executor_metadata:
        # Handle case where violations are in executor_metadata
        violations = result.executor_metadata["violations"]
        violations_text = "\n".join([f"- Line {v['line']}: {v['message']} (severity: {v['severity']})" for v in violations])

    # Write report
    with report_path.open("w") as f:
        f.write("# AUDIT REPORT\n\n")
        f.write(f"**File**: `{rel_path}`\n")
        f.write(f"**Status**: {result.status}\n")
        f.write(f"**Audit Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Execution Time**: {result.audit_execution_time:.2f}s\n\n")
        f.write("---\n\n")

        if result.status == "PASS":
            f.write("✅ No violations detected.\n")
        else:
            f.write(f"## Violations ({len(result.violations)})\n\n")
            f.write(violations_text)
            f.write("\n")


def consolidate_patterns(
    result: Any,
    root_dir: Path,
    output_dir: Path,
    consolidated_file: Path,
) -> None:
    """Consolidate patterns from failed audit into CONSOLIDATED.md.

    Only called for FAIL/ERROR files to extract patterns.

    Args:
        result: Failed audit result
        root_dir: Root directory being audited
        output_dir: Output directory
        consolidated_file: Path to CONSOLIDATED.md
    """

    # Get audit report path
    try:
        rel_path = result.item_path.relative_to(root_dir)
    except ValueError:
        rel_path = Path(result.item_path.name)

    report_path = output_dir / rel_path.with_suffix(rel_path.suffix + ".md")

    # Read audit report
    if not report_path.exists():
        return

    audit_content = report_path.read_text()

    # Read current consolidated (if exists)
    consolidated_content = consolidated_file.read_text() if consolidated_file.exists() else "# CONSOLIDATED AUDIT PATTERNS\n\nNo patterns consolidated yet.\n"

    # Run consolidation via agent CLI
    cli = get_agent_cli()
    config = get_config()
    prompts_dir = config.root / config.get("prompts.dir")
    consolidate_instruction = prompts_dir / config.get("prompts.consolidate")

    # Build context
    context = f"""
## CURRENT CONSOLIDATED REPORT

File path: `{consolidated_file}`

```markdown
{consolidated_content}
```

---

## NEW AUDIT REPORT

File path: `{report_path}`

```markdown
{audit_content}
```

---

**REMEMBER**: Use Read/Write/Edit tools to update `{consolidated_file}`. Output ONLY 'UPDATED' or 'NO_CHANGES' when done.
"""

    # run_print() raises AgentExecutionError on non-zero exit
    # If we reach this line, execution was successful
    consolidate_config = AgentConfigPresets.consolidate(session_id=result.item_path.name)
    consolidate_config.enable_streaming = True
    output, _ = cli.run_print(
        instruction_file=consolidate_instruction,
        stdin=context,
        agent_config=consolidate_config,
    )

    logger.info("consolidation_result", result=output.strip())
