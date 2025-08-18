#!/usr/bin/env python
"""
Script to find all #noqa comments across all modules and generate a timestamped report.
"""

import re
from datetime import datetime
from pathlib import Path

# Constants to avoid magic numbers
MAX_LINE_LENGTH = 100
LINE_TRUNCATE_LENGTH = 97

# Type aliases for clarity
FileResult = tuple[Path, int, str]
ModuleResults = dict[str, list[tuple[Path, int, str]]]
FileGroups = dict[str, list[tuple[int, str]]]


def find_noqa_comments(directory: Path) -> list[FileResult]:
    """Find all lines containing #noqa comments in Python files.

    Args:
        directory: Directory to search

    Returns:
        List of (file_path, line_number, line_content) tuples
    """
    noqa_pattern = re.compile(r"#\s*noqa", re.IGNORECASE)
    results = []

    # Find all Python files
    for py_file in directory.rglob("*.py"):
        # Skip venv and other directories we don't care about
        if any(part in py_file.parts for part in [".venv", "__pycache__", ".git", "node_modules"]):
            continue

        try:
            with py_file.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if noqa_pattern.search(line):
                        results.append((py_file, line_num, line.rstrip()))
        except (OSError, UnicodeDecodeError) as e:
            print(f"Error reading {py_file}: {e}")

    return results


def group_results_by_module(results: list[FileResult], root_dir: Path) -> ModuleResults:
    """Group results by module."""
    modules: ModuleResults = {}
    for file_path, line_num, content in results:
        # Determine module
        rel_path = file_path.relative_to(root_dir)
        module = rel_path.parts[0] if len(rel_path.parts) > 0 else "root"

        if module not in modules:
            modules[module] = []
        modules[module].append((rel_path, line_num, content))

    return modules


def format_header(timestamp: str, title: str, subtitle: str = "") -> list[str]:
    """Format report header."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"{title} - {timestamp}")
    if subtitle:
        lines.append(subtitle)
    lines.append("=" * 80)
    lines.append("")
    return lines


def format_module_section(module: str, module_results: list[tuple[Path, int, str]], label: str = "Total") -> list[str]:
    """Format a module section of the report."""
    lines = []
    lines.append("")
    lines.append(f"MODULE: {module}")
    lines.append(f"{'=' * len(f'MODULE: {module}')}")
    lines.append(f"{label} noqa comments: {len(module_results)}")
    lines.append("")
    return lines


def group_by_file(module_results: list[tuple[Path, int, str]]) -> FileGroups:
    """Group module results by file."""
    files: FileGroups = {}
    for rel_path, line_num, content in module_results:
        file_str = str(rel_path)
        if file_str not in files:
            files[file_str] = []
        files[file_str].append((line_num, content))
    return files


def format_file_section(file_path: str, file_results: list[tuple[int, str]]) -> list[str]:
    """Format a file section with its noqa comments."""
    lines = []
    lines.append(f"  FILE: {file_path}")
    lines.append(f"  {'-' * (len(file_path) + 6)}")

    for line_num, content in sorted(file_results):
        # Extract the noqa code if present
        noqa_match = re.search(r"#\s*noqa(?::?\s*([A-Z0-9, ]+))?", content, re.IGNORECASE)
        noqa_code = noqa_match.group(1) if noqa_match and noqa_match.group(1) else "no code"

        # Truncate long lines
        display_content = content
        if len(content) > MAX_LINE_LENGTH:
            display_content = content[:LINE_TRUNCATE_LENGTH] + "..."

        lines.append(f"    Line {line_num:5d}: [{noqa_code:10s}] {display_content.strip()}")

    lines.append("")
    return lines


def extract_noqa_types(results: list[FileResult]) -> dict[str, int]:
    """Extract and count noqa types from results."""
    noqa_types: dict[str, int] = {}
    for _, _, content in results:
        noqa_match = re.search(r"#\s*noqa(?::?\s*([A-Z0-9, ]+))?", content, re.IGNORECASE)
        if noqa_match and noqa_match.group(1):
            # Split multiple codes
            codes = [c.strip() for c in noqa_match.group(1).split(",")]
            for code in codes:
                if code:
                    noqa_types[code] = noqa_types.get(code, 0) + 1
        else:
            noqa_types["(no code)"] = noqa_types.get("(no code)", 0) + 1
    return noqa_types


def format_summary_section(noqa_types: dict[str, int], title: str = "SUMMARY BY NOQA TYPE:") -> list[str]:
    """Format the summary section."""
    lines = []
    lines.append("-" * 80)
    lines.append(title)
    lines.append("-" * 80)

    for code in sorted(noqa_types.keys()):
        lines.append(f"  {code:15s}: {noqa_types[code]:3d} occurrences")

    return lines


def generate_report(results: list[FileResult], root_dir: Path) -> str:
    """Generate a formatted report of noqa comments.

    Args:
        results: List of (file_path, line_number, line_content) tuples
        root_dir: Root directory for relative paths

    Returns:
        Formatted report string
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = []

    # Header
    report.extend(format_header(timestamp, "NOQA COMMENTS REPORT"))

    if not results:
        report.append("No #noqa comments found!")
        return "\n".join(report)

    # Group by module
    modules = group_results_by_module(results, root_dir)

    # Report summary
    report.append(f"TOTAL NOQA COMMENTS FOUND: {len(results)}")
    report.append(f"MODULES AFFECTED: {', '.join(sorted(modules.keys()))}")
    report.append("")
    report.append("-" * 80)

    # Detailed listing by module
    for module in sorted(modules.keys()):
        report.extend(format_module_section(module, modules[module]))

        # Group by file within module
        files = group_by_file(modules[module])

        for file_path in sorted(files.keys()):
            report.extend(format_file_section(file_path, files[file_path]))

    # Summary by noqa type
    noqa_types = extract_noqa_types(results)
    report.extend(format_summary_section(noqa_types))

    report.append("")
    report.append("=" * 80)
    report.append(f"END OF REPORT - Generated at {timestamp}")
    report.append("=" * 80)

    return "\n".join(report)


def filter_critical_results(results: list[FileResult], root_dir: Path) -> list[FileResult]:
    """Filter out setup scripts and test files to show only critical noqa comments.

    Args:
        results: List of (file_path, line_number, line_content) tuples
        root_dir: Root directory for relative paths

    Returns:
        Filtered list of critical noqa comments
    """
    critical_results = []

    # Patterns to exclude
    exclude_patterns = [
        "test_",  # Test files
        "tests/",  # Test directories
        "conftest.py",  # Pytest config
        "setup.py",  # Setup scripts
        "setup_env.py",
        "bootstrap_paths.py",
        "run_tests.py",
        "start_mcp_server.py",
        "run_dataops.py",
        "run_ssh.py",
        "run_chrome.py",
        "run_filesys.py",
        "run_server.py",
        "path_finder.py",
        "mcp_runner_setup.py",
    ]

    for file_path, line_num, content in results:
        rel_path = file_path.relative_to(root_dir)
        path_str = str(rel_path).replace("\\", "/")

        # Check if this file should be excluded
        should_exclude = False
        for pattern in exclude_patterns:
            if pattern in path_str.lower():
                should_exclude = True
                break

        # Also exclude E402 (import order) as these are mostly unavoidable in our setup
        if "E402" in content:
            should_exclude = True

        if not should_exclude:
            critical_results.append((file_path, line_num, content))

    return critical_results


def extract_critical_noqa_types(results: list[FileResult]) -> dict[str, int]:
    """Extract and count critical noqa types (excluding E402)."""
    noqa_types: dict[str, int] = {}
    for _, _, content in results:
        noqa_match = re.search(r"#\s*noqa(?::?\s*([A-Z0-9, ]+))?", content, re.IGNORECASE)
        if noqa_match and noqa_match.group(1):
            codes = [c.strip() for c in noqa_match.group(1).split(",")]
            for code in codes:
                if code and code != "E402":  # Exclude E402 from summary
                    noqa_types[code] = noqa_types.get(code, 0) + 1
        else:
            noqa_types["(no code)"] = noqa_types.get("(no code)", 0) + 1
    return noqa_types


def generate_critical_report(results: list[FileResult], root_dir: Path) -> str:
    """Generate a report of critical noqa comments (excluding tests and setup).

    Args:
        results: List of (file_path, line_number, line_content) tuples
        root_dir: Root directory for relative paths

    Returns:
        Formatted critical report string
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = []

    # Header
    report.extend(format_header(timestamp, "CRITICAL NOQA COMMENTS REPORT", "(Excluding tests, setup scripts, and E402 import order issues)"))

    if not results:
        report.append("No critical #noqa comments found!")
        report.append("All noqa comments are in tests or setup scripts.")
        return "\n".join(report)

    # Group by module
    modules = group_results_by_module(results, root_dir)

    # Report summary
    report.append(f"CRITICAL NOQA COMMENTS FOUND: {len(results)}")
    report.append(f"MODULES AFFECTED: {', '.join(sorted(modules.keys()))}")
    report.append("")
    report.append("These require attention and should be fixed if possible:")
    report.append("-" * 80)

    # Detailed listing by module
    for module in sorted(modules.keys()):
        report.extend(format_module_section(module, modules[module], "Critical"))

        # Group by file within module
        files = group_by_file(modules[module])

        for file_path in sorted(files.keys()):
            report.extend(format_file_section(file_path, files[file_path]))

    # Summary by noqa type (critical only)
    noqa_types = extract_critical_noqa_types(results)
    report.extend(format_summary_section(noqa_types, "SUMMARY OF CRITICAL NOQA TYPES:"))

    report.append("")
    report.append("=" * 80)
    report.append(f"END OF CRITICAL REPORT - Generated at {timestamp}")
    report.append("=" * 80)

    return "\n".join(report)


def save_report(report: str, script_dir: Path, timestamp: str, prefix: str) -> None:
    """Save report to file with timestamp and latest version."""
    # Save to timestamped file
    report_file = script_dir / f"{prefix}_{timestamp}.txt"
    with report_file.open("w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to: {report_file}")

    # Also create a latest symlink/copy
    latest_file = script_dir / f"{prefix}_latest.txt"
    with latest_file.open("w", encoding="utf-8") as f:
        f.write(report)
    print(f"Latest report also saved to: {latest_file}")


def main():
    """Main function to run the noqa finder."""
    # Get the root directory (parent of scripts)
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent

    print(f"Searching for #noqa comments in: {root_dir}")
    print("This may take a moment...")
    print()

    # Find all noqa comments
    results = find_noqa_comments(root_dir)

    # Generate full report
    report = generate_report(results, root_dir)

    # Print to console
    print(report)

    # Save full report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_report(report, script_dir, timestamp, "noqa_report")

    # Generate critical report (excluding tests and setup)
    print()
    print("=" * 80)
    print("Generating CRITICAL report (excluding tests and setup scripts)...")
    print("=" * 80)

    critical_results = filter_critical_results(results, root_dir)
    critical_report = generate_critical_report(critical_results, root_dir)

    print(critical_report)

    # Save critical report
    save_report(critical_report, script_dir, timestamp, "critical_noqa_report")


if __name__ == "__main__":
    main()
