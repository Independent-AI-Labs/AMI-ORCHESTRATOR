#!/usr/bin/env bash
# Safe git push wrapper - runs tests before pushing
# Usage: git_push.sh <module-path> [remote] [branch]

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Error: Module path required"
    echo "Usage: $0 <module-path> [remote] [branch]"
    echo ""
    echo "Examples:"
    echo "  $0 . origin main"
    echo "  $0 clients/irisai/demo"
    exit 1
fi

MODULE_PATH="$1"
shift  # Remove module path from arguments

# Resolve to absolute path
if [ ! -d "$MODULE_PATH" ]; then
    echo "Error: Module path does not exist: $MODULE_PATH"
    exit 1
fi

MODULE_ROOT="$(cd "$MODULE_PATH" && pwd)"

# Verify it's a git repository
if [ ! -e "$MODULE_ROOT/.git" ]; then
    echo "Error: Not a git repository: $MODULE_ROOT"
    echo "(.git directory or file not found)"
    exit 1
fi

cd "$MODULE_ROOT"

# Check if this is orchestrator root or a submodule
if [ -f "$MODULE_ROOT/.git" ]; then
    # Submodule
    MODULE_NAME="$(basename "$MODULE_ROOT")"
else
    # Orchestrator root
    MODULE_NAME="root"
fi

echo "Running tests for ${MODULE_NAME} before push..."
echo "=========================================="

# Run tests
if [ -f "$MODULE_ROOT/scripts/run_tests.py" ]; then
    if ! "$MODULE_ROOT/.venv/bin/python" "$MODULE_ROOT/scripts/run_tests.py"; then
        echo "✗ Tests failed - push aborted"
        exit 1
    fi
else
    echo "No test runner found at $MODULE_ROOT/scripts/run_tests.py"
    exit 1
fi

echo "=========================================="
echo "✓ All tests passed!"
echo ""
echo "Pushing to remote..."

# Push with arguments or defaults
if [ $# -eq 0 ]; then
    git push
else
    git push "$@"
fi

echo "✓ Push completed successfully"
