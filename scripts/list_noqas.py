#!/usr/bin/env python3
"""List all noqa comments in the repo by module."""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

IGNORED_PARTS = {"__pycache__", "node_modules", "venv"}
NOQA_PATTERN = re.compile(r"#\s*noqa:?\s*([A-Z0-9,\s]+)?")


def iter_python_files(repo_root: Path) -> Iterator[Path]:
    """Yield python files under ``repo_root`` while skipping ignored paths."""

    def should_skip(path: Path) -> bool:
        return any(part.startswith(".") or part in IGNORED_PARTS for part in path.parts)

    for py_file in repo_root.rglob("*.py"):
        if should_skip(py_file):
            continue
        yield py_file


def determine_module(repo_root: Path, file_path: Path) -> str | None:
    """Return the top-level module name for ``file_path`` or ``None`` if unknown."""

    try:
        relative = file_path.relative_to(repo_root)
    except ValueError:
        return None

    return relative.parts[0] if len(relative.parts) > 1 else "root"


def collect_noqa_data(
    repo_root: Path,
) -> tuple[
    defaultdict[str, int],
    defaultdict[str, defaultdict[str, int]],
    defaultdict[str, list[tuple[int, str, str]]],
]:
    """Scan the repository and return aggregated noqa data."""

    module_counts: defaultdict[str, int] = defaultdict(int)
    module_codes: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    file_details: defaultdict[str, list[tuple[int, str, str]]] = defaultdict(list)

    for py_file in iter_python_files(repo_root):
        module = determine_module(repo_root, py_file)
        if not module:
            continue

        try:
            content = py_file.read_text()
        except OSError as exc:
            print(f"Failed to read {py_file}: {exc}", file=sys.stderr)
            continue

        for line_num, line in enumerate(content.splitlines(), 1):
            match = NOQA_PATTERN.search(line)
            if not match:
                continue

            module_counts[module] += 1
            codes_str = match.group(1)
            if codes_str:
                codes = [c.strip() for c in codes_str.replace(",", " ").split() if c.strip()]
                for code in codes:
                    module_codes[module][code] += 1
            else:
                module_codes[module]["(blanket)"] += 1

            rel_path = str(py_file.relative_to(repo_root))
            file_details[module].append((line_num, rel_path, line.strip()))

    return module_counts, module_codes, file_details


def print_summary(
    module_counts: dict[str, int],
    module_codes: dict[str, dict[str, int]],
) -> None:
    """Print module-level summary statistics."""

    print("=" * 80)
    print("NOQA COMMENTS BY MODULE")
    print("=" * 80)
    print()

    total_noqas = 0
    for module, count in sorted(module_counts.items(), key=lambda item: item[1], reverse=True):
        total_noqas += count
        print(f"{module:20s} {count:5d} noqas")

        for code, code_count in sorted(module_codes[module].items(), key=lambda item: item[1], reverse=True):
            print(f"  {code:15s} {code_count:5d}")
        print()

    print("=" * 80)
    print(f"TOTAL: {total_noqas} noqas across {len(module_counts)} modules")
    print("=" * 80)
    print()


def maybe_print_details(
    module_counts: Iterable[str],
    file_details: dict[str, list[tuple[int, str, str]]],
) -> None:
    """Ask the user whether to print per-file details and display them when requested."""

    print("\nShow file details? (y/n): ", end="")
    choice = sys.stdin.read(1).lower()
    if choice != "y":
        return

    print("\n" + "=" * 80)
    print("FILE DETAILS")
    print("=" * 80)
    for module in sorted(module_counts):
        print(f"\n{module}:")
        print("-" * 80)
        for line_num, file_path, line in file_details[module]:
            print(f"{file_path}:{line_num}")
            print(f"  {line}")


def main() -> int:
    """Entry point for the CLI utility."""

    repo_root = Path(__file__).parent.parent
    module_counts, module_codes, file_details = collect_noqa_data(repo_root)

    module_counts_dict = dict(module_counts)
    module_codes_dict = {module: dict(codes) for module, codes in module_codes.items()}

    total_noqas = sum(module_counts_dict.values())

    if total_noqas > 0:
        print_summary(module_counts_dict, module_codes_dict)
        print("\nERROR: Lint suppressions (noqa comments) are not allowed!")
        print("Fix the underlying issues instead of suppressing warnings.")
        print("\nTo see file details, run: python3 scripts/list_noqas.py")
        return 1

    print("✓ No lint suppressions (noqa comments) found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
