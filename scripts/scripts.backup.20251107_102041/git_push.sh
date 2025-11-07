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

# Find orchestrator root
ORCHESTRATOR_ROOT="$MODULE_ROOT"
while [ ! -d "$ORCHESTRATOR_ROOT/base" ] && [ "$ORCHESTRATOR_ROOT" != "/" ]; do
    ORCHESTRATOR_ROOT="$(dirname "$ORCHESTRATOR_ROOT")"
done

if [ ! -d "$ORCHESTRATOR_ROOT/base" ]; then
    echo "✗ Cannot find orchestrator root (base/ directory)"
    exit 1
fi

# Run centralized test runner
# For root: explicitly test only tests/ directory to avoid submodule tests
# For submodules: discover all tests in module
if [ "$MODULE_NAME" = "root" ]; then
    # Pass "tests/" as explicit pytest argument to only test root's tests/
    if ! "$ORCHESTRATOR_ROOT/scripts/ami-run.sh" "$ORCHESTRATOR_ROOT/base/scripts/run_tests.py" "$MODULE_ROOT" -- tests/; then
        echo "✗ Tests failed - push aborted"
        exit 1
    fi
else
    # Submodules: discover all tests
    if ! "$ORCHESTRATOR_ROOT/scripts/ami-run.sh" "$ORCHESTRATOR_ROOT/base/scripts/run_tests.py" "$MODULE_ROOT"; then
        echo "✗ Tests failed - push aborted"
        exit 1
    fi
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
