#!/usr/bin/env python3
"""Fail if banned words appear in the repository (excluding third-party dirs)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories that are treated as third-party or generated content.
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    ".venv-linux",
    "uv_cache",
    "cli-agents",  # explicitly excluded per user request
    ".next",  # Next.js build output
    "vendor",
    "site-packages",
    "dist-info",
    "egg-info",
    "third_party",
    "pkg",
    "coverage",
    "out",
    "domains",  # Submodule with separate governance
    "stubs",  # Type hint files
    "data",  # Runtime data directories (profiles, sessions, downloads)
}

# Individual files that should not be scanned (e.g., this tool itself).
IGNORED_FILES = {
    Path("scripts/check_banned_words.py"),
    Path("ux/cms/public/js/lib/highlight-engine/index.js"),  # Vendor lib
    Path("ux/scripts/check_banned_words.py"),
    Path("AGENTS.md"),
    Path("CLAUDE.md"),
    Path("claude-agent.sh"),
    Path("codex-agent.sh"),
}

# File extensions to ignore
IGNORED_SUFFIXES = {".tsbuildinfo", ".log", ".lock", ".min.js.map", ".min.js", ".min.css"}

DEFAULT_BANNED_WORDS = (
    "fallback",
    "backwards",
    "compatibility",
    "legacy",
    "shim",
    "shims",
    "stub",
    "stubs",
    "placeholder",
    "placeholders",
    "mock",
)

# Banned filename patterns (versioning, temporal markers)
BANNED_FILENAME_PATTERNS = (
    "_v1",
    "_v2",
    "_v3",
    "_v4",
    "_v5",
    "_old",
    "_new",
    "_fixed",
    "_temp",
    "_tmp",
    "_backup",
    "_copy",
    "_2",
    "_final",
    "_latest",
    ".old",
    ".new",
    ".backup",
    ".bak",
    ".orig",
)


def should_skip(path: Path) -> bool:
    """Return True if the relative path is inside an ignored directory or has ignored suffix."""

    return any(part in IGNORED_DIRS for part in path.parts) or path.suffix in IGNORED_SUFFIXES


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    except OSError:
        return None


def has_banned_filename_pattern(filename: str) -> str | None:
    """Check if filename contains banned patterns. Returns the pattern if found."""
    # Get filename without any extensions
    path = Path(filename)
    name_lower = path.name.lower()

    # Skip timestamp patterns (e.g., 20251004_120205)
    # These are 8+ digits followed by underscore and more digits
    if re.search(r"\d{8,}_\d+", name_lower):
        return None

    # Check for banned patterns
    for pattern in BANNED_FILENAME_PATTERNS:
        # For underscore/dot patterns, check if they're at word boundaries
        # (end of stem or before extension)
        if pattern.startswith(("_", ".")):
            # Check if pattern appears at the end of the stem or as extension
            stem = path.stem.lower()
            if stem.endswith(pattern.lstrip(".")):
                return pattern
            if name_lower.endswith(pattern):
                return pattern
        # For other patterns, check anywhere in name
        elif pattern in name_lower:
            return pattern

    return None


def should_skip_word_in_line(word: str, lower_line: str, file_path: Path | None = None) -> bool:
    """Return True if the word should be skipped in this line due to exceptions."""
    # Skip if word appears as a keyword argument (e.g., placeholder="...")
    if f"{word}=" in lower_line:
        return True

    # Skip stub-related exceptions
    if word in ("stub", "stubs") and ("asyncpg-stubs" in lower_line or "dgraphclientstub" in lower_line):
        return True

    # Skip placeholder exceptions
    if word in ("placeholder", "placeholders"):
        sql_terms = ("sql", "query", "parameter", "$1", "$2")
        dom_terms = ('.get("placeholder"', ".placeholder")
        template_marker = "{{" in lower_line and "}}" in lower_line
        sql_or_dom = any(term in lower_line for term in sql_terms) or any(term in lower_line for term in dom_terms)
        if sql_or_dom or template_marker:
            return True

    # Skip mock-related exceptions (pytest-mock package or tests/unit/)
    if word == "mock":
        pytest_mock = any(term in lower_line for term in ("pytest-mock", "pytest_mock", "plugins:"))
        in_unit_tests = file_path and "tests/unit/" in str(file_path).lower()
        if pytest_mock or in_unit_tests:
            return True

    return False


def scan_repo(banned_words: tuple[str, ...], module_path: Path | None = None) -> tuple[dict[str, list[tuple[Path, int, str]]], list[tuple[Path, str]]]:
    results: dict[str, list[tuple[Path, int, str]]] = {word: [] for word in banned_words}
    filename_violations: list[tuple[Path, str]] = []

    # Determine scan root
    scan_root = module_path if module_path else REPO_ROOT

    for file_path in scan_root.rglob("*"):
        if not file_path.is_file():
            continue

        relative = file_path.relative_to(REPO_ROOT)
        if should_skip(relative) or relative in IGNORED_FILES:
            continue
        name = relative.name.lower()
        if name.endswith("-agent.sh") or name.startswith("agents."):
            continue

        # Check for banned filename patterns
        banned_pattern = has_banned_filename_pattern(relative.name)
        if banned_pattern:
            filename_violations.append((relative, banned_pattern))

        content = read_text(file_path)
        if content is None:
            continue

        lines = content.splitlines()
        lower_lines = [line.lower() for line in lines]

        for index, lower_line in enumerate(lower_lines, start=1):
            for word in banned_words:
                if word in lower_line and not should_skip_word_in_line(word, lower_line, relative):
                    results[word].append((relative, index, lines[index - 1].strip()))

    return results, filename_violations


def parse_module_path(argv: list[str]) -> Path | None:
    """Parse optional module path from args."""
    if not argv:
        print("Scanning entire repository")
        return None

    module_arg = argv[0]
    potential_path = REPO_ROOT / module_arg
    if potential_path.exists() and potential_path.is_dir():
        print(f"Scanning module: {module_arg}")
        return potential_path

    print(f"Error: Path '{module_arg}' not found or not a directory")
    raise SystemExit(1)


def report_filename_violations(filename_violations: list[tuple[Path, str]]) -> None:
    """Report filename pattern violations."""
    print(f"BANNED FILENAME PATTERNS FOUND ({len(filename_violations)} file(s)):")
    for relative, pattern in filename_violations:
        print(f"  {relative} contains pattern '{pattern}'")
    print()
    print("Filenames must not contain versioning or temporal markers.")
    print("Update existing files instead of creating v2, _old, _new, etc.")
    print()


def report_word_violations(findings: dict[str, list[tuple[Path, int, str]]]) -> None:
    """Report banned word violations with summaries."""
    doc_dirs = {"docs", "documentation"}
    doc_exts = {".md", ".mdx", ".rst", ".txt", ".adoc"}

    for word, matches in findings.items():
        if not matches:
            continue

        print(f"BANNED WORD '{word}' FOUND {len(matches)} time(s):")
        for relative, line_number, line in matches:
            print(f"  {relative}:{line_number}: {line}")
        print()

        # Aggregate summary by top-level directory and doc/code classification
        summaries: dict[str, dict[str, int]] = {}
        for relative, *_ in matches:
            top_level = relative.parts[0] if relative.parts else "(repository root)"
            ext = relative.suffix.lower()
            classification = "docs" if (ext in doc_exts or any(part in doc_dirs for part in relative.parts)) else "code"
            module_summary = summaries.setdefault(top_level, {"docs": 0, "code": 0})
            module_summary[classification] += 1

        print("Summary by top-level directory:")
        for module in sorted(summaries):
            counts = summaries[module]
            doc_count = counts["docs"]
            code_count = counts["code"]
            total = doc_count + code_count
            print(f"  {module:20} total={total:4d}  docs={doc_count:4d}  code={code_count:4d}")
        print()


def main(argv: list[str]) -> int:
    module_path = parse_module_path(argv)
    words = DEFAULT_BANNED_WORDS
    findings, filename_violations = scan_repo(words, module_path)

    violations = bool(filename_violations) or any(findings.values())

    if filename_violations:
        report_filename_violations(filename_violations)

    if any(findings.values()):
        report_word_violations(findings)

    scan_target = module_path.name if module_path else "repository"

    if violations:
        total_violations = sum(len(matches) for matches in findings.values()) + len(filename_violations)
        print(f"TOTAL: {total_violations} violations found in {scan_target}")
        print("Banned words or filename patterns detected. Please remove or rename them before committing.")
        return 1

    print(f"✓ No banned words or filename patterns detected in {scan_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
