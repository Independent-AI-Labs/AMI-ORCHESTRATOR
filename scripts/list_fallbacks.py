#!/usr/bin/env python3
"""Report every occurrence of the word 'fallback' outside cli-agents."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterable
from pathlib import Path

DEFAULT_KEYWORD = "fallback"
REPO_ROOT = Path(__file__).resolve().parent.parent
IGNORED_DIRS = {
    "cli-agents",
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "uv_cache",
    "vendor",
    "site-packages",
    "dist-info",
    "egg-info",
    "third_party",
    ".next",  # Next.js build output
    "pkg",
    "coverage",
    "out",
}
IGNORED_PATH_PREFIXES = {Path("domains"), Path("ux/cms/public/js/lib")}
SCRIPT_PATH = Path(__file__).resolve().relative_to(REPO_ROOT)
IGNORED_FILES = {
    Path("scripts/check_banned_words.py"),
    Path("scripts/list_fallbacks.py"),
    Path("AGENTS.md"),
    Path("codex-agent.sh"),
    Path("claude-agent.sh"),
    SCRIPT_PATH,
}
IGNORED_SUFFIXES = {".tsbuildinfo", ".log", ".lock", ".min.js.map", ".min.js", ".min.css"}


def should_skip(relative_path: Path) -> bool:
    """Return True when the path should be skipped based on ignored directories."""

    if any(part in IGNORED_DIRS for part in relative_path.parts):
        return True

    return any(relative_path.is_relative_to(prefix) for prefix in IGNORED_PATH_PREFIXES)


def iter_files(root_paths: Iterable[Path]) -> Iterable[Path]:
    """Yield files under the provided roots while pruning ignored directories."""

    for root in root_paths:
        abs_root = (REPO_ROOT / root).resolve()
        if not abs_root.exists():
            continue

        for dirpath, dirnames, filenames in os.walk(abs_root, topdown=True):
            rel_dir = Path(dirpath).relative_to(REPO_ROOT)
            if should_skip(rel_dir):
                dirnames[:] = []
                continue

            # Prune ignored directories before descending further
            dirnames[:] = [d for d in dirnames if not should_skip(rel_dir / d)]

            for filename in filenames:
                candidate = rel_dir / filename
                if should_skip(candidate):
                    continue
                if candidate.suffix in IGNORED_SUFFIXES:
                    continue
                yield REPO_ROOT / candidate


def scan_for_keyword(keyword: str, roots: Iterable[Path]) -> list[tuple[Path, int, str]]:
    """Scan the repository for the keyword and return matches as tuples."""

    matches: list[tuple[Path, int, str]] = []

    for path in iter_files(roots):
        relative = path.relative_to(REPO_ROOT)
        if relative in IGNORED_FILES:
            continue
        if relative.name.endswith("-agent.sh"):
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lowered = keyword.lower()
        for line_number, line in enumerate(content.splitlines(), start=1):
            if lowered in line.lower():
                matches.append((relative, line_number, line.strip()))

    return matches


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keyword",
        default=DEFAULT_KEYWORD,
        help="Keyword to search for (default: '%(default)s')",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[Path()],
        help="Optional paths (relative to repo root) to scan. Defaults to entire repo.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    keyword = args.keyword.lower()
    roots = [Path(p) for p in args.paths]
    matches = scan_for_keyword(keyword, roots)

    if not matches:
        print(f"No occurrences of '{keyword}' found outside ignored directories.")
        return 0

    for relative, line_number, line in matches:
        print(f"{relative}:{line_number}: {line}")

    print(f"\nTotal matches: {len(matches)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
