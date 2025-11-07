#!/usr/bin/env bash
"""'exec "$(dirname "$0")/ami-run.sh" "$(dirname "$0")/audit_shebangs.py" "$@" #"""

from __future__ import annotations

"""Audit Python script shebangs across the AMI Orchestrator repository.

This script checks all Python files for incorrect shebangs and reports:
1. Scripts using direct python/python3 instead of ami-run
2. Scripts with polyglot shebangs that don't use ami-run
3. Scripts with no shebang (potential issues)

Usage:
    scripts/audit_shebangs.py                          # Check all Python files
    scripts/audit_shebangs.py --fix                    # Fix incorrect shebangs
    scripts/audit_shebangs.py --verbose                # Show all files checked
    scripts/audit_shebangs.py -d /path/to/dir          # Check specific directory
    scripts/audit_shebangs.py --staged-only            # Check only git staged files
"""

import argparse
import subprocess
import sys
from pathlib import Path

from loguru import logger

# Root directory
ROOT = Path(__file__).resolve().parents[1]

# Correct shebang patterns
CORRECT_AMI_RUN_SHEBANG = '#!/usr/bin/env bash\n"""\'exec "$(dirname "$0")/ami-run.sh" "$(dirname "$0")'
CORRECT_AMI_RUN_BASE = '#!/usr/bin/env bash\n"""\'exec "$(dirname "$0")/../scripts/ami-run.sh"'

# Incorrect patterns to detect
INCORRECT_PATTERNS = [
    (b"#!/usr/bin/env python", "Direct python shebang"),
    (b"#!/usr/bin/python", "Direct python shebang"),
    (b"#!/usr/bin/env python3", "Direct python3 shebang"),
    (b"#!/usr/bin/python3", "Direct python3 shebang"),
    (b'.venv/bin/python"', "Direct .venv python"),
]

# Security risk patterns
SECURITY_PATTERNS = [
    (b"sudo", "Contains sudo (security risk)"),
    (b"/usr/bin/python", "System python path (out-of-sandbox)"),
    (b"/usr/local/bin/python", "System python path (out-of-sandbox)"),
]

# Directories to skip
SKIP_DIRS = {
    ".venv",
    ".venv-linux",
    ".venv-windows",
    ".venv-macos",
    "node_modules",
    "__pycache__",
    ".git",
    ".cache",
    "venv",
    "env",
}


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped."""
    # Skip if in excluded directory
    for part in file_path.parts:
        if part in SKIP_DIRS:
            return True

    # Skip if not a Python file
    if file_path.suffix != ".py":
        return True

    # Skip __init__.py files (they're imported, not executed)
    return file_path.name == "__init__.py"


def get_shebang_lines(file_path: Path) -> tuple[str, str, str]:
    """Get first three lines of file (shebang + polyglot pattern).

    Returns:
        Tuple of (line1, line2, line3)
    """
    try:
        with file_path.open("rb") as f:
            line1 = f.readline().decode("utf-8", errors="ignore").rstrip()
            line2 = f.readline().decode("utf-8", errors="ignore").rstrip()
            line3 = f.readline().decode("utf-8", errors="ignore").rstrip()
        return line1, line2, line3
    except Exception as e:
        logger.warning(f"Failed to read {file_path}: {e}")
        return "", "", ""


def check_shebang(file_path: Path, verbose: bool = False) -> tuple[bool, str]:
    """Check if file has correct shebang.

    Returns:
        Tuple of (is_correct, issue_description)
    """
    line1, line2, line3 = get_shebang_lines(file_path)
    is_executable = file_path.stat().st_mode & 0o111

    # No shebang - only fail if executable
    if not line1.startswith("#!"):
        verbose_msg = "Not executable, no shebang needed" if verbose else ""
        return (False, "Executable file with no shebang") if is_executable else (True, verbose_msg)

    # Read content once for all pattern checks
    with file_path.open("rb") as f:
        content = f.read(200)

    # Check for security patterns first
    security_issue = next((f"SECURITY RISK: {desc}" for pat, desc in SECURITY_PATTERNS if pat in content), None)
    if security_issue:
        return False, security_issue

    # Check for incorrect patterns
    incorrect_issue = next((desc for pat, desc in INCORRECT_PATTERNS if pat in content), None)
    if incorrect_issue:
        return False, incorrect_issue

    # Check if using ami-run correctly
    has_ami_run = any("ami-run.sh" in line for line in (line1, line2, line3))
    if has_ami_run:
        return True, "Correct ami-run shebang"

    return False, f"Non-ami-run shebang: {line1[:50]}"


def get_correct_shebang(file_path: Path) -> tuple[str, str]:
    """Generate correct shebang for a file based on its location.

    Returns:
        Tuple of (line1, line2)
    """
    # Determine relative path to ami-run.sh
    try:
        rel_to_root = file_path.relative_to(ROOT)
        depth = len(rel_to_root.parts) - 1

        if depth == 1:
            # File is in root/foo.py
            ami_run_path = '"$(dirname "$0")/scripts/ami-run.sh"'
            script_ref = '"$0"'
        else:
            # File is deeper
            parent_dirs = "../" * (depth - 1)
            ami_run_path = f'"$(dirname "$0")/{parent_dirs}scripts/ami-run.sh"'
            script_ref = '"$0"'

        line1 = "#!/usr/bin/env bash"
        line2 = f"""''':'
exec {ami_run_path} {script_ref} "$@"
'''"""

        return line1, line2

    except ValueError:
        # File not under ROOT
        logger.warning(f"File {file_path} is not under {ROOT}")
        return "", ""


def _skip_old_shebang(lines: list[str]) -> int:
    """Find index after old shebang and polyglot lines.

    Returns:
        Index of first line after shebang/polyglot pattern
    """
    if not lines or not lines[0].startswith("#!"):
        return 0

    idx = 1
    # Skip multiline polyglot: ''':', exec line, '''
    if len(lines) > idx and lines[idx].strip() in ("''':'", '"""\''):
        idx += 1
        if len(lines) > idx and "exec" in lines[idx]:
            idx += 1
        if len(lines) > idx and lines[idx].strip() in ("'''", '"""'):
            idx += 1
    # Skip old single-line polyglot: """'exec...'"""
    elif len(lines) > idx and "exec" in lines[idx] and '"""' in lines[idx]:
        idx += 1

    return idx


def _extract_future_import(lines: list[str], start_idx: int) -> tuple[str, int]:
    """Extract __future__ import if present.

    Returns:
        Tuple of (future_import_line, new_start_idx)
    """
    if len(lines) <= start_idx:
        return "", start_idx

    if lines[start_idx].strip().startswith("from __future__ import"):
        future_import = lines[start_idx]
        start_idx += 1
        # Skip blank line after future import
        if len(lines) > start_idx and not lines[start_idx].strip():
            start_idx += 1
        return future_import, start_idx

    return "", start_idx


def fix_shebang(file_path: Path) -> bool:
    """Fix shebang in file.

    Returns:
        True if fixed, False otherwise
    """
    line1, line2 = get_correct_shebang(file_path)
    if not line1:
        return False

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)

        # Skip old shebang/polyglot
        start_idx = _skip_old_shebang(lines)

        # Preserve __future__ import if present
        future_import, start_idx = _extract_future_import(lines, start_idx)

        # Build new content
        header = f"{line1}\n{line2}\n{future_import}\n" if future_import else f"{line1}\n{line2}\n\n"
        new_content = header + "".join(lines[start_idx:])
        file_path.write_text(new_content, encoding="utf-8")

        logger.info(f"✓ Fixed: {file_path.relative_to(ROOT)}")
        return True

    except Exception as e:
        logger.error(f"Failed to fix {file_path}: {e}")
        return False


def get_staged_python_files(scan_dir: Path) -> list[Path]:
    """Get list of staged Python files using git diff.

    Returns:
        List of staged Python file paths
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=scan_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        staged_files = result.stdout.strip().split("\n")
        return [scan_dir / f for f in staged_files if f and f.endswith(".py") and (scan_dir / f).exists()]
    except subprocess.CalledProcessError:
        logger.warning("Failed to get staged files (not a git repo?)")
        return []


def audit_repository(
    fix: bool = False,
    verbose: bool = False,
    scan_dir: Path | None = None,
    staged_only: bool = False,
) -> int:
    """Audit all Python files in repository.

    Args:
        fix: Automatically fix incorrect shebangs
        verbose: Show all files checked
        scan_dir: Directory to scan (default: ROOT)
        staged_only: Only check git staged files

    Returns:
        Number of files with issues
    """
    target_dir = scan_dir or ROOT

    logger.info("=" * 60)
    logger.info("AMI Orchestrator Shebang Audit")
    logger.info("=" * 60)
    logger.info(f"Scanning: {target_dir}")
    if staged_only:
        logger.info("Mode: Git staged files only")
    logger.info("")

    issues: list[tuple[Path, str]] = []
    checked = 0
    skipped = 0

    # Get files to check
    if staged_only:
        python_files = get_staged_python_files(target_dir)
        if not python_files:
            logger.info("No staged Python files to check")
            return 0
    else:
        python_files = list(target_dir.rglob("*.py"))

    # Check each file
    for py_file in python_files:
        if should_skip_file(py_file):
            skipped += 1
            continue

        checked += 1
        is_correct, issue = check_shebang(py_file, verbose=verbose)

        if not is_correct:
            issues.append((py_file, issue))
        elif verbose and issue:
            logger.debug(f"✓ {py_file.relative_to(target_dir)}: {issue}")

    # Report findings
    logger.info("")
    logger.info("=" * 60)
    logger.info("Audit Results")
    logger.info("=" * 60)
    logger.info(f"Files checked: {checked}")
    logger.info(f"Files skipped: {skipped}")
    logger.info(f"Issues found: {len(issues)}")
    logger.info("")

    if not issues:
        logger.info("✓ No shebang issues found!")
        return 0

    # Display issues
    logger.warning("Files with incorrect shebangs:")
    logger.warning("")
    for file_path, issue in issues:
        try:
            rel_path = file_path.relative_to(target_dir)
        except ValueError:
            rel_path = file_path
        logger.warning(f"  {rel_path}")
        logger.warning(f"    Issue: {issue}")
        logger.warning("")

    # Fix if requested
    if fix:
        logger.info("=" * 60)
        logger.info("Fixing shebangs...")
        logger.info("=" * 60)
        fixed = 0
        for file_path, _ in issues:
            if fix_shebang(file_path):
                fixed += 1

        logger.info("")
        logger.info(f"✓ Fixed {fixed}/{len(issues)} files")

        if fixed < len(issues):
            logger.warning(f"⚠ {len(issues) - fixed} files could not be fixed")

    return len(issues)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Audit Python script shebangs across AMI Orchestrator")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix incorrect shebangs",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all files checked, including correct ones",
    )
    parser.add_argument(
        "--directory",
        "-d",
        type=Path,
        help="Directory to scan (default: repository root)",
    )
    parser.add_argument(
        "--staged-only",
        action="store_true",
        help="Only check git staged files (for pre-commit hooks)",
    )
    args = parser.parse_args()

    # Resolve directory
    scan_dir = args.directory.resolve() if args.directory else None

    try:
        issue_count = audit_repository(
            fix=args.fix,
            verbose=args.verbose,
            scan_dir=scan_dir,
            staged_only=args.staged_only,
        )

        if issue_count > 0 and not args.fix:
            logger.info("")
            logger.info("To fix these issues automatically, run:")
            if args.directory:
                logger.info(f"  scripts/audit_shebangs.py --directory {args.directory} --fix")
            else:
                logger.info("  scripts/audit_shebangs.py --fix")

        # Exit with error code if issues found (for hooks)
        return 0 if issue_count == 0 else 1

    except KeyboardInterrupt:
        logger.warning("\nAudit cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
