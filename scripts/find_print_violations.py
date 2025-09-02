#!/usr/bin/env python
"""Find all print statements that should be using logger instead."""

import re
import sys
from pathlib import Path

# Root directory to search
ROOT = Path(__file__).parent.parent

# Directories to search
SEARCH_DIRS = [
    "base/backend",
    "browser/backend",
    "files/backend",
    "compliance/backend",
    "domains/backend",
    "base/scripts",
    "browser/scripts",
    "files/scripts",
    "compliance/scripts",
    "domains/scripts",
]

# Files to exclude (test files can use print)
EXCLUDE_PATTERNS = ["**/test_*.py", "**/*_test.py", "**/tests/**", "**/conftest.py", "**/__pycache__/**", "**/.venv/**", "**/venv/**"]


def should_skip(file_path: Path) -> bool:
    """Check if file should be skipped."""
    str_path = str(file_path)

    # Skip test files
    if "test_" in file_path.name or "_test.py" in file_path.name:
        return True

    # Skip test directories
    if "/tests/" in str_path.replace("\\", "/") or "\\tests\\" in str_path:
        return True

    # Skip cache and venv
    return "__pycache__" in str_path or ".venv" in str_path or "/venv/" in str_path.replace("\\", "/")


def find_print_statements(file_path: Path) -> list[tuple[int, str]]:
    """Find print statements in a file."""
    violations = []

    try:
        with Path(file_path).open(encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            # Look for print statements (but not in comments or strings)
            # Simple regex - may have false positives but better to catch more
            # Combine conditions with or operator
            if re.search(r"^\s*print\s*\(", line) or re.search(r'^\s*print\s+"', line) or re.search(r"^\s*print\s+'", line):
                violations.append((line_num, line.strip()))

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return violations


def main() -> int:
    """Find all print statement violations."""

    print("=" * 80)
    print("FINDING PRINT STATEMENT VIOLATIONS")
    print("All non-test code should use logger, not print()")
    print("=" * 80)

    all_violations = {}

    for search_dir in SEARCH_DIRS:
        dir_path = ROOT / search_dir
        if not dir_path.exists():
            continue

        # Find all Python files
        for py_file in dir_path.rglob("*.py"):
            if should_skip(py_file):
                continue

            violations = find_print_statements(py_file)
            if violations:
                all_violations[py_file] = violations

    if not all_violations:
        print("\nSUCCESS: No print statement violations found!")
        return 0

    # Report violations
    print(f"\nERROR: Found print statements in {len(all_violations)} files:\n")

    total_violations = 0
    for file_path, violations in sorted(all_violations.items()):
        relative_path = file_path.relative_to(ROOT)
        print(f"\n{relative_path}:")
        for line_num, line_content in violations:
            print(f"  Line {line_num}: {line_content}")
            total_violations += 1

    print("\n" + "=" * 80)
    print(f"TOTAL VIOLATIONS: {total_violations} print statements in {len(all_violations)} files")
    print("These should all be replaced with logger.info(), logger.warning(), etc.")
    print("=" * 80)

    return 1  # Exit with error code


if __name__ == "__main__":
    sys.exit(main())
