#!/usr/bin/env python3
"""Remove pattern numbering from patterns_core.txt.

Reads the file and removes all pattern numbers and section counts.
Only order matters, not specific numbers.
"""

import re
import sys
from pathlib import Path

# Add orchestrator root to path
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))
from base.scripts.env.paths import find_orchestrator_root


def _parse_sections_and_patterns(lines: list[str]) -> tuple[dict[str, list[tuple[int, str]]], dict[str, int]]:
    """Parse severity sections and their patterns from file lines."""
    current_section: str | None = None
    section_patterns: dict[str, list[tuple[int, str]]] = {}
    section_header_lines: dict[str, int] = {}

    for i, line in enumerate(lines):
        # Match severity headers (with or without counts)
        severity_match = re.match(r"^###\s+(CRITICAL|HIGH|MEDIUM)\s+SEVERITY", line)
        if severity_match:
            current_section = severity_match.group(1)
            section_patterns[current_section] = []
            section_header_lines[current_section] = i
            continue

        # Match pattern headers (with or without numbers)
        if current_section:
            # Try numbered format first: #### 13. Pattern Name
            pattern_match = re.match(r"^####\s+(?:\d+\.\s+)?(.+)", line)
            if pattern_match:
                title = pattern_match.group(1)
                section_patterns[current_section].append((i, title))

    return section_patterns, section_header_lines


def _remove_numbering(
    lines: list[str],
    section_patterns: dict[str, list[tuple[int, str]]],
    section_header_lines: dict[str, int],
) -> list[str]:
    """Remove pattern numbers and section counts."""
    new_lines = lines.copy()

    for section, patterns in section_patterns.items():
        # Remove count from section header
        header_line = section_header_lines[section]
        new_lines[header_line] = f"### {section} SEVERITY\n"

        # Remove numbers from pattern headers
        for line_num, title in patterns:
            new_lines[line_num] = f"#### {title}\n"

    return new_lines


def remove_pattern_numbering(file_path: Path) -> None:
    """Remove pattern numbering from patterns_core.txt."""
    # Validate path
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"Not a file: {file_path}")

    # Read file
    try:
        content = file_path.read_text()
    except OSError as e:
        raise RuntimeError(f"Failed to read file: {e}") from e

    lines = content.splitlines(keepends=True)

    # Parse sections and patterns
    section_patterns, section_header_lines = _parse_sections_and_patterns(lines)

    # Remove numbering
    new_lines = _remove_numbering(lines, section_patterns, section_header_lines)

    # Write back
    try:
        file_path.write_text("".join(new_lines))
    except OSError as e:
        raise RuntimeError(f"Failed to write file: {e}") from e

    # Print report
    print("Pattern numbering removed:")
    for section, patterns in section_patterns.items():
        if patterns:
            print(f"  {section} SEVERITY: {len(patterns)} patterns")


if __name__ == "__main__":
    try:
        repo_root = find_orchestrator_root()
        if not repo_root:
            raise RuntimeError("Unable to locate orchestrator root")
        patterns_file = repo_root / "scripts/config/prompts/patterns_core.txt"
        remove_pattern_numbering(patterns_file)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
