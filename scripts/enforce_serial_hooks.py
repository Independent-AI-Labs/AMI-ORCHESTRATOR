#!/usr/bin/env python3
"""Enforce require_serial: true on all pre-commit hooks in all submodules.

This script ensures that all pre-commit hooks run serially to prevent:
- File system race conditions
- Resource conflicts (browser processes, databases, etc.)
- Git push timing issues
- Test interference
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Submodules with .pre-commit-config.yaml
SUBMODULES = [
    "base",
    "browser",
    "compliance",
    "domains",
    "files",
    "nodes",
    "streams",
    "ux",
]


def add_require_serial(content: str) -> tuple[str, int]:
    """Add require_serial: true to all hooks missing it.

    Returns:
        Tuple of (modified_content, number_of_changes)
    """
    changes = 0

    # Pattern: Find hook blocks without require_serial
    # A hook block starts with "- id:" and ends before next "- id:" or "- repo:"
    lines = content.split("\n")
    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        result_lines.append(line)

        # Check if this line starts a hook definition
        if re.match(r"^\s*- id:", line):
            # Find the indentation level of this hook
            hook_indent = len(line) - len(line.lstrip())

            # Scan ahead to see if require_serial already exists in this hook block
            j = i + 1
            has_require_serial = False
            hook_end = len(lines)

            while j < len(lines):
                next_line = lines[j]

                # Check if we've reached the next hook or repo
                if re.match(r"^\s*- (id|repo):", next_line):
                    hook_end = j
                    break

                # Check if this hook already has require_serial
                if re.match(r"^\s*require_serial:", next_line):
                    has_require_serial = True
                    break

                j += 1

            # If no require_serial found, add it
            if not has_require_serial:
                # Find where to insert it (after stages line or before next hook)
                insert_pos = None

                for k in range(i + 1, hook_end):
                    check_line = lines[k]
                    # Insert after "stages:" line
                    if re.match(r"^\s*stages:", check_line):
                        insert_pos = k + 1
                        break

                if insert_pos is None:
                    # No stages line, insert at end of hook block
                    insert_pos = hook_end

                # Add require_serial with same indentation as other hook properties
                property_indent = " " * (hook_indent + 2)
                require_serial_line = f"{property_indent}require_serial: true"

                # Insert the line
                result_lines.append(require_serial_line)
                changes += 1

                # Continue from where we left off, but skip the inserted line
                i += 1
                continue

        i += 1

    return "\n".join(result_lines), changes


def process_file(file_path: Path) -> bool:
    """Process a single .pre-commit-config.yaml file.

    Returns:
        True if file was modified, False otherwise
    """
    try:
        content = file_path.read_text()
        modified_content, changes = add_require_serial(content)

        if changes > 0:
            file_path.write_text(modified_content)
            print(f"✓ {file_path.relative_to(REPO_ROOT)}: Added require_serial to {changes} hook(s)")
            return True
        print(f"  {file_path.relative_to(REPO_ROOT)}: All hooks already have require_serial")
        return False

    except Exception as e:
        print(f"✗ {file_path.relative_to(REPO_ROOT)}: Error - {e}")
        return False


def process_all_configs() -> int:
    """Process all config files and return count of modified files."""
    modified_count = 0

    # Process root config
    root_config = REPO_ROOT / ".pre-commit-config.yaml"
    if root_config.exists():
        if process_file(root_config):
            modified_count += 1
    else:
        print(f"✗ Root .pre-commit-config.yaml not found at {root_config}")

    # Process submodule configs (both platform-specific and generated)
    for submodule in SUBMODULES:
        for platform_config in [
            REPO_ROOT / submodule / ".pre-commit-config.unix.yaml",
            REPO_ROOT / submodule / ".pre-commit-config.win.yaml",
            REPO_ROOT / submodule / ".pre-commit-config.yaml",
        ]:
            if platform_config.exists() and process_file(platform_config):
                modified_count += 1

    # Process base config templates
    for base_config in [
        REPO_ROOT / "base" / "configs" / ".pre-commit-config.unix.yaml",
        REPO_ROOT / "base" / "configs" / ".pre-commit-config.win.yaml",
    ]:
        if base_config.exists() and process_file(base_config):
            modified_count += 1

    return modified_count


def reinstall_hooks() -> int:
    """Reinstall pre-commit hooks in all submodules to pick up new config.

    Returns:
        Number of modules where hooks were successfully reinstalled
    """
    reinstalled_count = 0
    print("Reinstalling pre-commit hooks to pick up new configuration...")
    print()

    # Reinstall hooks in each submodule
    for submodule in SUBMODULES:
        submodule_path = REPO_ROOT / submodule
        venv_precommit = submodule_path / ".venv" / "bin" / "pre-commit"

        if not venv_precommit.exists():
            print(f"  {submodule}: No .venv/bin/pre-commit found (skipping)")
            continue

        try:
            # Uninstall existing hooks
            subprocess.run(
                [str(venv_precommit), "uninstall"],
                cwd=str(submodule_path),
                capture_output=True,
                check=False,
            )

            # Reinstall hooks with new config
            result = subprocess.run(
                [str(venv_precommit), "install", "--install-hooks"],
                cwd=str(submodule_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                print(f"✓ {submodule}: Hooks reinstalled")
                reinstalled_count += 1
            else:
                print(f"✗ {submodule}: Failed to reinstall hooks - {result.stderr}")

        except Exception as e:
            print(f"✗ {submodule}: Error reinstalling hooks - {e}")

    return reinstalled_count


def main() -> int:
    """Enforce require_serial on all pre-commit config files."""
    print("Enforcing require_serial: true on all pre-commit hooks...")
    print()

    modified_count = process_all_configs()

    print()
    if modified_count > 0:
        print(f"✓ Modified {modified_count} file(s)")
        print()

        # Reinstall hooks to pick up new config
        reinstalled_count = reinstall_hooks()
        print()

        if reinstalled_count > 0:
            print(f"✓ Reinstalled hooks in {reinstalled_count} module(s)")
            print()

        print("Next steps:")
        print("  1. Review changes: git diff")
        print("  2. Test hooks: git add -A && git commit -m 'test'")
        print("  3. Commit changes if satisfied")
        return 0

    print("✓ All files already compliant")

    # Still reinstall hooks even if no config changes
    print()
    reinstalled_count = reinstall_hooks()
    if reinstalled_count > 0:
        print()
        print(f"✓ Reinstalled hooks in {reinstalled_count} module(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
