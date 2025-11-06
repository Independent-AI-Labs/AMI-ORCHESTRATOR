#!/usr/bin/env bash
# Safe git commit wrapper - stages all changes before committing
# Usage: git_commit.sh [--fix] <module-path> <commit-message>
#        git_commit.sh [--fix] <module-path> -F <file>
#        git_commit.sh [--fix] <module-path> --amend
#        git_commit.sh [--fix] <module-path> --amend <commit-message>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Error: Module path required"
    echo "Usage: $0 [--fix] <module-path> <commit-message>"
    echo "       $0 [--fix] <module-path> -F <file>"
    echo "       $0 [--fix] <module-path> --amend"
    echo "       $0 [--fix] <module-path> --amend <commit-message>"
    echo ""
    echo "Options:"
    echo "  --fix    Run auto-fixes (ruff --fix --unsafe-fixes) before committing"
    echo ""
    echo "Examples:"
    echo "  $0 . \"fix: update root\""
    echo "  $0 --fix . \"fix: update root with auto-fixes\""
    echo "  $0 . -F /tmp/commit_msg.txt"
    echo "  $0 . --amend"
    echo "  $0 . --amend \"fix: corrected message\""
    echo "  $0 clients/irisai/demo \"fix: add migrations\""
    exit 1
fi

# Parse --fix flag
RUN_AUTOFIXES=false
if [ "$1" = "--fix" ]; then
    RUN_AUTOFIXES=true
    shift
fi

MODULE_PATH="$1"
shift

# Parse commit message argument
USE_AMEND=false
AMEND_MESSAGE=""
if [ $# -eq 0 ]; then
    echo "Error: Commit message or --amend flag required"
    exit 1
elif [ "$1" = "--amend" ]; then
    USE_AMEND=true
    USE_FILE=false
    shift
    # Check if there's a message after --amend
    if [ $# -gt 0 ]; then
        AMEND_MESSAGE="$1"
    fi
elif [ "$1" = "-F" ]; then
    if [ $# -lt 2 ]; then
        echo "Error: -F flag requires file path"
        exit 1
    fi
    COMMIT_FILE="$2"
    if [ ! -f "$COMMIT_FILE" ]; then
        echo "Error: Commit message file does not exist: $COMMIT_FILE"
        exit 1
    fi
    USE_FILE=true
else
    COMMIT_MSG="$1"
    USE_FILE=false
fi

# Resolve to absolute path
if [ ! -d "$MODULE_PATH" ]; then
    echo "Error: Module path does not exist: $MODULE_PATH"
    exit 1
fi

MODULE_ROOT="$(cd "$MODULE_PATH" && pwd)"

# Determine if this is orchestrator root or submodule
if [ -f "$MODULE_ROOT/.git" ]; then
    # Submodule - find orchestrator root
    CURRENT_DIR="$MODULE_ROOT"
    while [ -f "$CURRENT_DIR/.git" ]; do
        CURRENT_DIR="$(cd "$CURRENT_DIR/.." && pwd)"
        if [ "$CURRENT_DIR" = "/" ]; then
            echo "Error: Could not find orchestrator root"
            exit 1
        fi
    done
    ORCHESTRATOR_ROOT="$CURRENT_DIR"
else
    # Orchestrator root
    ORCHESTRATOR_ROOT="$MODULE_ROOT"
fi

# Verify it's a git repository
if [ ! -e "$MODULE_ROOT/.git" ]; then
    echo "Error: Not a git repository: $MODULE_ROOT"
    echo "(.git directory or file not found)"
    exit 1
fi

# Run autofixes if requested
if [ "$RUN_AUTOFIXES" = true ]; then
    echo "Running auto-fixes..."
    cd "$MODULE_ROOT"

    # Determine ruff config based on module type
    if [ "$ORCHESTRATOR_ROOT" = "$MODULE_ROOT" ]; then
        # Orchestrator root - use root ruff.toml if exists, otherwise base/ruff.toml
        if [ -f "${ORCHESTRATOR_ROOT}/ruff.toml" ]; then
            RUFF_CONFIG="${ORCHESTRATOR_ROOT}/ruff.toml"
        else
            RUFF_CONFIG="${ORCHESTRATOR_ROOT}/base/ruff.toml"
        fi
    else
        # Submodule - use base/ruff.toml
        RUFF_CONFIG="${ORCHESTRATOR_ROOT}/base/ruff.toml"
    fi

    # Run ruff with autofix
    RUFF_BIN="${ORCHESTRATOR_ROOT}/.venv/bin/ruff"
    if [ ! -f "$RUFF_BIN" ]; then
        # Try module .venv
        RUFF_BIN="${MODULE_ROOT}/.venv/bin/ruff"
    fi

    if [ ! -f "$RUFF_BIN" ]; then
        echo "Error: ruff not found in ${ORCHESTRATOR_ROOT}/.venv/bin or ${MODULE_ROOT}/.venv/bin"
        exit 1
    fi

    echo "Running ruff check --fix --unsafe-fixes..."
    "$RUFF_BIN" check --config "$RUFF_CONFIG" --fix --unsafe-fixes . || true

    echo "✓ Auto-fixes complete"
fi

echo "Staging all changes in ${MODULE_ROOT}..."
cd "$MODULE_ROOT"
git add -A

# Run shebang security check on staged files
echo "Running shebang security check..."
AUDIT_SCRIPT="${ORCHESTRATOR_ROOT:-$MODULE_ROOT}/scripts/audit_shebangs.py"
if [ -f "$AUDIT_SCRIPT" ]; then
    PYTHON_BIN="${ORCHESTRATOR_ROOT:-$MODULE_ROOT}/.venv/bin/python"
    if [ ! -f "$PYTHON_BIN" ]; then
        PYTHON_BIN="python3"
    fi

    if ! "$PYTHON_BIN" "$AUDIT_SCRIPT" --staged-only --directory "$MODULE_ROOT"; then
        echo ""
        echo "❌ Shebang security check failed!"
        echo "Fix issues and try again, or run with --fix flag:"
        echo "  $PYTHON_BIN $AUDIT_SCRIPT --staged-only --directory $MODULE_ROOT --fix"
        exit 1
    fi
    echo "✓ Shebang security check passed"
else
    echo "✗ BLOCKED: Shebang audit script not found at $AUDIT_SCRIPT"
    exit 1
fi

echo "Creating commit..."
if [ "$USE_AMEND" = true ]; then
    if [ -n "$AMEND_MESSAGE" ]; then
        git commit --amend -m "$AMEND_MESSAGE"
    else
        git commit --amend --no-edit
    fi
elif [ "$USE_FILE" = true ]; then
    git commit -F "$COMMIT_FILE"
else
    git commit -m "$COMMIT_MSG"
fi

echo "✓ Commit created successfully"
