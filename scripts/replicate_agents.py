#!/usr/bin/env python3
"""Replicate root AGENTS.md into each submodule."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_FILE = ROOT / "AGENTS.md"


def parse_gitmodules() -> list[Path]:
    paths: list[Path] = []
    gitmodules = ROOT / ".gitmodules"
    if not gitmodules.exists():
        return paths

    current_path: str | None = None
    for raw in gitmodules.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("[submodule"):
            if current_path:
                paths.append(ROOT / current_path)
            current_path = None
            continue
        if line.startswith("path ="):
            current_path = line.split("=", 1)[1].strip()
    if current_path:
        paths.append(ROOT / current_path)
    return paths


def replicate(targets: list[Path], check_only: bool) -> bool:
    if not AGENTS_FILE.exists():
        raise FileNotFoundError(f"Missing AGENTS.md at {AGENTS_FILE}")
    source_text = AGENTS_FILE.read_text(encoding="utf-8")

    changed = False
    for module_path in targets:
        if not module_path.exists():
            continue
        dest = module_path / "AGENTS.md"
        if dest.exists() and dest.read_text(encoding="utf-8") == source_text:
            continue
        if check_only:
            print(f"needs update: {dest}")
            changed = True
            continue
        dest.write_text(source_text, encoding="utf-8")
        print(f"replicated: {dest}")
        changed = True
    return changed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Replicate AGENTS.md to submodules")
    parser.add_argument("--check", action="store_true", help="Report targets needing updates without writing")
    args = parser.parse_args(argv)

    submodules = parse_gitmodules()
    if not submodules:
        print("No submodules found in .gitmodules", file=sys.stderr)
        return 0

    changed = replicate(submodules, check_only=args.check)
    if args.check and changed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
