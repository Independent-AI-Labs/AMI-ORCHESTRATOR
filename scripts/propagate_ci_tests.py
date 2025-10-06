#!/usr/bin/env python3
"""Propagate CI/CD validation tests to all submodules.

This script copies the CI test infrastructure from base/tests/integration/ci
to all other submodules, ensuring consistent CI/CD validation across the repo.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Source directory (base module)
SOURCE_DIR = REPO_ROOT / "base" / "tests" / "integration" / "ci"

# Target submodules (excluding base since it's the source)
TARGET_SUBMODULES = [
    "browser",
    "compliance",
    "domains",
    "files",
    "nodes",
    "streams",
    # Note: ux excluded - see CLAUDE.md
]


def copy_ci_tests(target_module: str) -> bool:
    """Copy CI tests to a target submodule.

    Args:
        target_module: Name of the target submodule

    Returns:
        True if tests were copied successfully, False otherwise
    """
    target_dir = REPO_ROOT / target_module / "tests" / "integration" / "ci"

    # Create target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Copy all files from source to target
        for source_file in SOURCE_DIR.glob("*"):
            if source_file.is_file():
                target_file = target_dir / source_file.name
                shutil.copy2(source_file, target_file)
                print(f"  ✓ Copied {source_file.name}")

        return True

    except Exception as e:
        print(f"  ✗ Error copying to {target_module}: {e}")
        return False


def reinstall_hooks(modules: list[str]) -> int:
    """Reinstall pre-commit hooks in specified modules.

    Returns:
        Number of modules where hooks were successfully reinstalled
    """
    reinstalled_count = 0
    print("Reinstalling pre-commit hooks in modules...")
    print()

    for module in modules:
        module_path = REPO_ROOT / module
        venv_precommit = module_path / ".venv" / "bin" / "pre-commit"

        if not venv_precommit.exists():
            print(f"  {module}: No .venv/bin/pre-commit found (skipping)")
            continue

        try:
            # Uninstall existing hooks
            subprocess.run(
                [str(venv_precommit), "uninstall"],
                cwd=str(module_path),
                capture_output=True,
                check=False,
            )

            # Reinstall hooks with new config
            result = subprocess.run(
                [str(venv_precommit), "install", "--install-hooks"],
                cwd=str(module_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                print(f"✓ {module}: Hooks reinstalled")
                reinstalled_count += 1
            else:
                print(f"✗ {module}: Failed to reinstall hooks - {result.stderr}")

        except Exception as e:
            print(f"✗ {module}: Error reinstalling hooks - {e}")

    return reinstalled_count


def main() -> int:
    """Propagate CI tests to all submodules."""
    print("Propagating CI/CD validation tests from base to all submodules...")
    print()

    if not SOURCE_DIR.exists():
        print(f"✗ Source directory not found: {SOURCE_DIR}")
        print("  Please ensure base/tests/integration/ci exists with test files.")
        return 1

    # List source files
    source_files = list(SOURCE_DIR.glob("*.py"))
    if not source_files:
        print(f"✗ No test files found in {SOURCE_DIR}")
        return 1

    print("Source: base/tests/integration/ci/")
    for source_file in source_files:
        print(f"  - {source_file.name}")
    print()

    # Copy to each target submodule
    success_count = 0
    fail_count = 0

    for submodule in TARGET_SUBMODULES:
        print(f"Copying to {submodule}/tests/integration/ci/")
        if copy_ci_tests(submodule):
            success_count += 1
        else:
            fail_count += 1
        print()

    # Reinstall hooks to pick up any config changes
    print("=" * 60)
    reinstalled_count = reinstall_hooks(TARGET_SUBMODULES)
    print()

    # Summary
    print("=" * 60)
    if fail_count == 0:
        print(f"✓ Successfully propagated CI tests to {success_count} submodule(s)")
        if reinstalled_count > 0:
            print(f"✓ Reinstalled hooks in {reinstalled_count} module(s)")
        print()
        print("Next steps:")
        print("  1. Review changes: git diff")
        print("  2. Run tests in each module: cd <module> && ../scripts/ami-run.sh scripts/run_tests.py")
        print("  3. Commit if satisfied")
        return 0
    print(f"✗ Failed to propagate to {fail_count} submodule(s)")
    print(f"✓ Successfully propagated to {success_count} submodule(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
