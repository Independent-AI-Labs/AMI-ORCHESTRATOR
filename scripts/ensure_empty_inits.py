#!/usr/bin/env python3
"""
Ensure all __init__.py files are empty.

Usage:
  - Check only: python scripts/ensure_empty_inits.py --check
  - Fix (empty files): python scripts/ensure_empty_inits.py --fix

Notes:
  - Keeps file presence (does not delete files)
  - Treats whitespace and comments as non-empty; result is truly empty file
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def find_inits(root: Path) -> list[Path]:
    ignore_dirs = {".venv", ".git", ".mypy_cache", ".ruff_cache", "__pycache__"}
    results: list[Path] = []
    for p in root.rglob("__init__.py"):
        if any(part in ignore_dirs for part in p.parts):
            continue
        results.append(Path(p))
    return results


def is_empty(path: Path) -> bool:
    try:
        data = path.read_text(encoding="utf-8")
    except Exception:
        return False
    return data == ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure all __init__.py files are empty")
    parser.add_argument("--check", action="store_true", help="Only report non-empty files")
    parser.add_argument("--fix", action="store_true", help="Empty non-empty __init__.py files")
    args = parser.parse_args()

    if not args.check and not args.fix:
        # default to check mode if no flags provided
        args.check = True

    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    inits = find_inits(repo_root)
    non_empty: list[Path] = [p for p in inits if not is_empty(p)]

    if args.check:
        if non_empty:
            print("Non-empty __init__.py files:")
            for p in sorted(non_empty):
                print(f" - {p}")
            print(f"Total: {len(non_empty)}")
            return 1
        print("All __init__.py files are empty.")
        return 0

    # --fix
    changed = 0
    for p in non_empty:
        try:
            p.write_text("", encoding="utf-8")
            changed += 1
            print(f"emptied: {p}")
        except Exception as e:
            print(f"failed:  {p} ({e})")
    print(f"Emptied {changed} __init__.py files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
