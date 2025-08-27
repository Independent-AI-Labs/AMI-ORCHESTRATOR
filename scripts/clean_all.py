#!/usr/bin/env python
"""Clean all cache and venv directories across the entire project."""

import shutil
import sys
from pathlib import Path


def clean_project():
    """Remove all cache and venv directories."""
    root = Path(__file__).parent.parent
    print(f"Cleaning project at: {root}")

    # Patterns to clean
    patterns = [
        ".venv",
        "__pycache__",
        ".pytest_cache",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".coverage",
        "htmlcov",
        "*.egg-info",
        "dist",
        "build",
        ".mypy_cache",
        ".ruff_cache",
    ]

    total_removed = 0

    # Find and remove all matching directories and files
    for pattern in patterns:
        if pattern.startswith("*."):
            # File pattern
            for file in root.rglob(pattern):
                try:
                    file.unlink()
                    print(f"Removed file: {file}")
                    total_removed += 1
                except Exception as e:
                    print(f"Error removing {file}: {e}")
        else:
            # Directory pattern
            for dir_path in root.rglob(pattern):
                if dir_path.is_dir():
                    try:
                        shutil.rmtree(dir_path)
                        print(f"Removed directory: {dir_path}")
                        total_removed += 1
                    except Exception as e:
                        print(f"Error removing {dir_path}: {e}")

    print(f"\nCleaning complete! Removed {total_removed} items.")
    print("\nYou will need to recreate virtual environments:")
    print("  - Run setup.py in each module directory")
    print("  - Or use: uv venv .venv && uv pip install -r requirements.txt")

    return 0


if __name__ == "__main__":
    sys.exit(clean_project())
