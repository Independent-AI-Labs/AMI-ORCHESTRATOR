#!/usr/bin/env python
"""Root test runner that performs no config writes.

Behavior:
- If no tests, exits 0 without modifying any files.
- Otherwise, invokes pytest in the current (uv) environment.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    tests_dir = ROOT / "tests"
    if not tests_dir.exists():
        print(f"No tests directory found at {tests_dir}. Nothing to test.")
        return 0
    test_files = list(tests_dir.rglob("test_*.py")) + list(tests_dir.rglob("*_test.py"))
    if not test_files:
        print("No test files found. Nothing to test.")
        return 0
    cmd = [sys.executable, "-m", "pytest", "-q"]
    return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
