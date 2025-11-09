#!/usr/bin/env bash
# Safe git push wrapper - runs tests before pushing
# Usage: git_push.sh [--only-ready] <module-path> [remote] [branch]

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Error: Module path required"
    echo "Usage: $0 [--only-ready] <module-path> [remote] [branch]"
    echo ""
    echo "Options:"
    echo "  --only-ready    Skip dirty check, push already committed work only"
    echo ""
    echo "Examples:"
    echo "  $0 . origin main"
    echo "  $0 --only-ready . origin main"
    echo "  $0 clients/irisai/demo"
    exit 1
fi

# Parse flags
ONLY_READY=false
if [ "$1" = "--only-ready" ]; then
    ONLY_READY=true
    shift
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

# Check for uncommitted or unstaged changes (unless --only-ready)
if [ "$ONLY_READY" = false ]; then
    if ! git diff-index --quiet --ignore-submodules HEAD --; then
        echo "✗ BLOCKED: Uncommitted or unstaged changes detected"
        echo ""
        echo "Working tree must be clean before push."
        echo "Either:"
        echo "  1. Commit all changes with scripts/git_commit.sh"
        echo "  2. Use --only-ready flag to push already committed work"
        echo ""
        git status --short
        exit 1
    fi
fi

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
# For submodules: explicitly test only tests/ directory in module
if [ "$MODULE_NAME" = "root" ]; then
    # Pass "tests/" as explicit pytest argument to only test root's tests/
    if ! "$ORCHESTRATOR_ROOT/scripts/ami-run.sh" "$ORCHESTRATOR_ROOT/base/scripts/run_tests.py" "$MODULE_ROOT" -- tests/; then
        echo "✗ Tests failed - push aborted"
        exit 1
    fi
else
    # Submodules: pass "tests/" to discover only from module's tests/ directory
    if ! "$ORCHESTRATOR_ROOT/scripts/ami-run.sh" "$ORCHESTRATOR_ROOT/base/scripts/run_tests.py" "$MODULE_ROOT" -- tests/; then
        echo "✗ Tests failed - push aborted"
        exit 1
    fi
fi

echo "=========================================="
echo "✓ All tests passed!"
echo ""
echo "Pushing to remote..."

# Push with arguments or defaults and capture result
if [ $# -eq 0 ]; then
    if git push; then
        echo ""
        echo "✓ Push completed successfully"
    else
        echo ""
        echo "✗ Push failed - see error above"
        exit 1
    fi
else
    if git push "$@"; then
        echo ""
        echo "✓ Push completed successfully"
    else
        echo ""
        echo "✗ Push failed - see error above"
        exit 1
    fi
fi
