#!/usr/bin/env bash
# Delete a tag from all submodules and root (both local and remote)
# Usage: git_delete_tag_all.sh <version-tag>
#
# Examples:
#   git_delete_tag_all.sh v1.0.0-test

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Error: Version tag required"
    echo "Usage: $0 <version-tag>"
    echo ""
    echo "Examples:"
    echo "  $0 v1.0.0-test"
    exit 1
fi

TAG="$1"

ORCHESTRATOR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ORCHESTRATOR_ROOT"

# Verify we're in the orchestrator root
if [ ! -d ".git" ] || [ -f ".git" ]; then
    echo "Error: Not in orchestrator root directory"
    exit 1
fi

echo "Deleting tag from all submodules and root: $TAG"
echo "=========================================="
echo ""

# Get list of submodules, excluding external ones
SUBMODULES=$(git config --file .gitmodules --get-regexp path | awk '{print $2}' | grep -v "cli-agents/gemini-cli")

DELETED_MODULES=()
FAILED_MODULES=()

# Delete tag from each submodule
for MODULE in $SUBMODULES; do
    echo "Processing submodule: $MODULE"

    if [ ! -d "$MODULE" ]; then
        echo "  ✗ Directory not found: $MODULE"
        FAILED_MODULES+=("$MODULE")
        continue
    fi

    cd "$MODULE"

    # Verify it's a git repository
    if [ ! -e ".git" ]; then
        echo "  ✗ Not a git repository: $MODULE"
        FAILED_MODULES+=("$MODULE")
        cd "$ORCHESTRATOR_ROOT"
        continue
    fi

    # Check if tag exists locally
    if git rev-parse "$TAG" >/dev/null 2>&1; then
        # Delete local tag
        if git tag -d "$TAG"; then
            echo "  ✓ Deleted local tag: $MODULE"
        else
            echo "  ✗ Failed to delete local tag: $MODULE"
            FAILED_MODULES+=("$MODULE:local")
        fi

        # Delete remote tag
        if git push origin ":refs/tags/$TAG" 2>/dev/null; then
            echo "  ✓ Deleted remote tag: $MODULE"
            DELETED_MODULES+=("$MODULE")
        else
            echo "  ⚠ Remote tag may not exist or failed to delete: $MODULE"
        fi
    else
        echo "  - Tag $TAG does not exist in $MODULE"
    fi

    cd "$ORCHESTRATOR_ROOT"
done

echo ""
echo "=========================================="
echo "Deleting tag from root repository"

cd "$ORCHESTRATOR_ROOT"
if git rev-parse "$TAG" >/dev/null 2>&1; then
    # Delete local tag
    if git tag -d "$TAG"; then
        echo "✓ Deleted local tag: root"
    else
        echo "✗ Failed to delete local tag: root"
        FAILED_MODULES+=("root:local")
    fi

    # Delete remote tag
    if git push origin ":refs/tags/$TAG" 2>/dev/null; then
        echo "✓ Deleted remote tag: root"
        DELETED_MODULES+=("root")
    else
        echo "⚠ Remote tag may not exist or failed to delete: root"
    fi
else
    echo "- Tag $TAG does not exist in root"
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Deleted from: ${#DELETED_MODULES[@]} module(s)"
for MODULE in "${DELETED_MODULES[@]}"; do
    echo "  ✓ $MODULE"
done

if [ ${#FAILED_MODULES[@]} -gt 0 ]; then
    echo ""
    echo "Failed: ${#FAILED_MODULES[@]} module(s)"
    for MODULE in "${FAILED_MODULES[@]}"; do
        echo "  ✗ $MODULE"
    done
    exit 1
fi

echo ""
echo "✓ Tag successfully deleted from all submodules and root: $TAG"
