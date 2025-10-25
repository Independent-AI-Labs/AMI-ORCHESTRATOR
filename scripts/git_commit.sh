#!/usr/bin/env bash
# Safe git commit wrapper - stages all changes before committing
# Usage: git_commit.sh <module-path> <commit-message>
#        git_commit.sh <module-path> -F <file>
#        git_commit.sh <module-path> --amend

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Error: Module path required"
    echo "Usage: $0 <module-path> <commit-message>"
    echo "       $0 <module-path> -F <file>"
    echo "       $0 <module-path> --amend"
    echo ""
    echo "Examples:"
    echo "  $0 . \"fix: update root\""
    echo "  $0 . -F /tmp/commit_msg.txt"
    echo "  $0 . --amend"
    echo "  $0 clients/irisai/demo \"fix: add migrations\""
    exit 1
fi

MODULE_PATH="$1"
shift

# Parse commit message argument
USE_AMEND=false
if [ $# -eq 0 ]; then
    echo "Error: Commit message or --amend flag required"
    exit 1
elif [ "$1" = "--amend" ]; then
    USE_AMEND=true
    USE_FILE=false
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

# Verify it's a git repository
if [ ! -e "$MODULE_ROOT/.git" ]; then
    echo "Error: Not a git repository: $MODULE_ROOT"
    echo "(.git directory or file not found)"
    exit 1
fi

echo "Staging all changes in ${MODULE_ROOT}..."
cd "$MODULE_ROOT"
git add -A

echo "Creating commit..."
if [ "$USE_AMEND" = true ]; then
    git commit --amend --no-edit
elif [ "$USE_FILE" = true ]; then
    git commit -F "$COMMIT_FILE"
else
    git commit -m "$COMMIT_MSG"
fi

echo "✓ Commit created successfully"
