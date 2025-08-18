#!/usr/bin/env python
"""Replicate root CLAUDE.md to all submodules."""

import shutil
from pathlib import Path


def replicate_claude_md():
    """Copy root CLAUDE.md to all submodule directories."""
    root_dir = Path(__file__).parent.parent
    root_claude_md = root_dir / "CLAUDE.md"

    if not root_claude_md.exists():
        print(f"ERROR: Root CLAUDE.md not found at {root_claude_md}")
        return False

    # Define submodules
    submodules = [root_dir / "base", root_dir / "browser", root_dir / "files", root_dir / "compliance", root_dir / "domains"]

    success_count = 0
    for submodule in submodules:
        if not submodule.exists():
            print(f"WARNING: Submodule directory not found: {submodule}")
            continue

        target_claude_md = submodule / "CLAUDE.md"

        try:
            # Copy the file
            shutil.copy2(root_claude_md, target_claude_md)
            print(f"[OK] Replicated CLAUDE.md to {submodule.name}/")
            success_count += 1
        except Exception as e:
            print(f"[FAIL] Failed to replicate to {submodule.name}/: {e}")

    print(f"\nReplicated CLAUDE.md to {success_count}/{len(submodules)} submodules")
    return success_count == len([s for s in submodules if s.exists()])


if __name__ == "__main__":
    import sys

    success = replicate_claude_md()
    sys.exit(0 if success else 1)
