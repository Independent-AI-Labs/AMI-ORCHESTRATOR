#!/usr/bin/env python3
"""Fail if banned words appear in the repository (excluding third-party dirs)."""

from __future__ import annotations

import argparse
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


def should_skip_word_in_line(word: str, lower_line: str) -> bool:
    """Return True if the word should be skipped in this line due to exceptions."""
    # Skip if word appears as a keyword argument (e.g., placeholder="...")
    if f"{word}=" in lower_line:
        return True

    # Skip package names (e.g., asyncpg-stubs in requirements)
    if word in ("stub", "stubs") and "asyncpg-stubs" in lower_line:
        return True

    # Skip external library classes (e.g., pydgraph.DgraphClientStub)
    if word in ("stub", "stubs") and "dgraphclientstub" in lower_line:
        return True

    # Skip SQL parameter placeholders ($1, $2, etc.)
    if word in ("placeholder", "placeholders") and any(term in lower_line for term in ("sql", "query", "parameter", "$1", "$2")):
        return True

    # Skip template markers (e.g., {{MODULE_NAME}})
    return word in ("placeholder", "placeholders") and "{{" in lower_line and "}}" in lower_line


def scan_repo(banned_words: tuple[str, ...]) -> dict[str, list[tuple[Path, int, str]]]:
    results: dict[str, list[tuple[Path, int, str]]] = {word: [] for word in banned_words}

    for file_path in REPO_ROOT.rglob("*"):
        if not file_path.is_file():
            continue

        relative = file_path.relative_to(REPO_ROOT)
        if should_skip(relative) or relative in IGNORED_FILES:
            continue
        name = relative.name.lower()
        if name.endswith("-agent.sh") or name.startswith("agents."):
            continue

        content = read_text(file_path)
        if content is None:
            continue

        lines = content.splitlines()
        lower_lines = [line.lower() for line in lines]

        for index, lower_line in enumerate(lower_lines, start=1):
            for word in banned_words:
                if word in lower_line and not should_skip_word_in_line(word, lower_line):
                    results[word].append((relative, index, lines[index - 1].strip()))

    return results


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--words",
        nargs="*",
        default=list(DEFAULT_BANNED_WORDS),
        help="List of banned words to search for.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    words = tuple(word.lower() for word in args.words)

    findings = scan_repo(words)
    violations = False

    for word, matches in findings.items():
        if not matches:
            continue
        violations = True
        print(f"BANNED WORD '{word}' FOUND {len(matches)} time(s):")
        for relative, line_number, line in matches:
            print(f"  {relative}:{line_number}: {line}")
        print()

        # Aggregate summary by top-level directory and doc/code classification
        summaries: dict[str, dict[str, int]] = {}
        doc_dirs = {"docs", "documentation"}
        doc_exts = {".md", ".mdx", ".rst", ".txt", ".adoc"}
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

    if violations:
        print("Banned words detected. Please remove or rename them before committing.")
        return 1

    print("No banned words detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
