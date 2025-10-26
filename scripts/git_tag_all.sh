#!/usr/bin/env bash
# Tag all submodules and root with the same version tag
# Usage: git_tag_all.sh <version-tag> [message]
#
# Examples:
#   git_tag_all.sh v1.0.0
#   git_tag_all.sh v1.0.0 "Release version 1.0.0"

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Error: Version tag required"
    echo "Usage: $0 <version-tag> [message]"
    echo ""
    echo "Examples:"
    echo "  $0 v1.0.0"
    echo "  $0 v1.0.0 \"Release version 1.0.0\""
    exit 1
fi

TAG="$1"
MESSAGE="${2:-Release ${TAG}}"

# Validate tag format (should start with v and follow semver-like pattern)
if ! echo "$TAG" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+'; then
    echo "Error: Tag must follow semver format (e.g., v1.0.0, v2.1.3)"
    echo "Received: $TAG"
    exit 1
fi

ORCHESTRATOR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ORCHESTRATOR_ROOT"

# Verify we're in the orchestrator root
if [ ! -d ".git" ] || [ -f ".git" ]; then
    echo "Error: Not in orchestrator root directory"
    exit 1
fi

echo "Tagging all submodules and root with: $TAG"
echo "Message: $MESSAGE"
echo "=========================================="
echo ""

# Get list of submodules, excluding external ones
SUBMODULES=$(git config --file .gitmodules --get-regexp path | awk '{print $2}' | grep -v "cli-agents/gemini-cli")

TAGGED_MODULES=()
FAILED_MODULES=()

# Tag each submodule
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

    # Check if tag already exists
    if git rev-parse "$TAG" >/dev/null 2>&1; then
        echo "  ⚠ Tag $TAG already exists in $MODULE (skipping)"
        cd "$ORCHESTRATOR_ROOT"
        continue
    fi

    # Create annotated tag
    if git tag -a "$TAG" -m "$MESSAGE"; then
        echo "  ✓ Tagged: $MODULE"
        TAGGED_MODULES+=("$MODULE")
    else
        echo "  ✗ Failed to tag: $MODULE"
        FAILED_MODULES+=("$MODULE")
    fi

    cd "$ORCHESTRATOR_ROOT"
done

echo ""
echo "=========================================="
echo "Tagging root repository"

# Tag root repository
cd "$ORCHESTRATOR_ROOT"
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "⚠ Tag $TAG already exists in root (skipping)"
else
    if git tag -a "$TAG" -m "$MESSAGE"; then
        echo "✓ Tagged: root"
        TAGGED_MODULES+=("root")
    else
        echo "✗ Failed to tag root"
        FAILED_MODULES+=("root")
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "Pushing tags to remote repositories"
echo ""

# Push tags for each tagged module
for MODULE in "${TAGGED_MODULES[@]}"; do
    if [ "$MODULE" = "root" ]; then
        echo "Pushing tags for: root"
        cd "$ORCHESTRATOR_ROOT"
    else
        echo "Pushing tags for: $MODULE"
        cd "$ORCHESTRATOR_ROOT/$MODULE"
    fi

    if git push origin "$TAG"; then
        echo "  ✓ Pushed tag to origin"
    else
        echo "  ✗ Failed to push tag for $MODULE"
        FAILED_MODULES+=("$MODULE:push")
    fi

    cd "$ORCHESTRATOR_ROOT"
done

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Tagged and pushed: ${#TAGGED_MODULES[@]} module(s)"
for MODULE in "${TAGGED_MODULES[@]}"; do
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
echo "✓ All submodules and root successfully tagged and pushed: $TAG"
