#!/usr/bin/env bash
# Clean all Python linter and test caches from root and all submodules
# This includes mypy, ruff, pytest, and Python bytecode caches

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🧹 Cleaning all caches in ${PROJECT_ROOT}..."

# Find and remove all cache directories
# -o = OR operator for find
find "$PROJECT_ROOT" \( \
    -type d -name ".mypy_cache" -o \
    -type d -name ".ruff_cache" -o \
    -type d -name ".pytest_cache" -o \
    -type d -name "__pycache__" \
\) -prune -exec rm -rf {} + 2>/dev/null || true

echo "✅ Cache cleanup complete!"
echo ""
echo "Removed cache types:"
echo "  - .mypy_cache (mypy type checker)"
echo "  - .ruff_cache (ruff linter)"
echo "  - .pytest_cache (pytest test runner)"
echo "  - __pycache__ (Python bytecode)"
