#!/usr/bin/env python
"""Test runner for the AMI-ORCHESTRATOR root."""

import subprocess
import sys
from pathlib import Path


def main():
    """Run tests in all submodules."""
    root = Path(__file__).parent.parent

    # Test modules to check
    modules = ["base", "browser", "files"]
    failed = []

    for module in modules:
        module_path = root / module
        if not module_path.exists():
            continue

        run_tests_script = module_path / "scripts" / "run_tests.py"
        if not run_tests_script.exists():
            print(f"Warning: No run_tests.py in {module}")
            continue

        print(f"\nTesting {module}...")
        result = subprocess.run([sys.executable, str(run_tests_script)], cwd=str(module_path), capture_output=False, check=False)

        if result.returncode != 0:
            failed.append(module)

    if failed:
        print(f"\nTests failed in: {', '.join(failed)}")
        return 1

    print("\nAll tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
