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


def _ensure_repo_on_path() -> Path:
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists() and (current / "base").exists():
            sys.path.insert(0, str(current))
            return current
        current = current.parent
    raise RuntimeError("Unable to locate AMI orchestrator root")


def main() -> int:
    orchestrator_root = _ensure_repo_on_path()

    from base.backend.utils.runner_bootstrap import ensure_module_venv

    ensure_module_venv(Path(__file__))

    tests_dir = orchestrator_root / "tests"
    if not tests_dir.exists():
        print(f"No tests directory found at {tests_dir}. Nothing to test.")
        return 0
    test_files = list(tests_dir.rglob("test_*.py")) + list(tests_dir.rglob("*_test.py"))
    if not test_files:
        print("No test files found. Nothing to test.")
        return 0
    cmd = [sys.executable, "-m", "pytest"] + sys.argv[1:]
    return subprocess.run(cmd, cwd=str(orchestrator_root), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
