#!/usr/bin/env bash
# Propagate CLAUDE.md and AGENTS.md to all submodules
# FIRST copies AGENTS.md to CLAUDE.md everywhere (since Claude Code only auto-reads CLAUDE.md)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# STEP 1: Copy AGENTS.md to CLAUDE.md in root (so Claude Code auto-reads it)
if [ -f "AGENTS.md" ]; then
  echo "Copying AGENTS.md → CLAUDE.md in root..."
  cp -f AGENTS.md CLAUDE.md
else
  echo "Warning: AGENTS.md not found in root"
fi

# Get list of submodules
SUBMODULES=$(git config --file .gitmodules --get-regexp path | awk '{ print $2 }')

if [ -z "$SUBMODULES" ]; then
  echo "No submodules found"
  exit 0
fi

# STEP 2: For each submodule, copy AGENTS.md → CLAUDE.md, then propagate both
for submodule in $SUBMODULES; do
  if [ -d "$submodule" ]; then
    echo "Propagating to $submodule..."

    # First copy AGENTS.md to CLAUDE.md in the submodule
    if [ -f "$submodule/AGENTS.md" ]; then
      cp -f "$submodule/AGENTS.md" "$submodule/CLAUDE.md"
    fi

    # Then propagate root files to submodule
    cp -f CLAUDE.md "$submodule/"
    cp -f AGENTS.md "$submodule/"
  else
    echo "Warning: Submodule directory $submodule not found, skipping"
  fi
done

echo "Propagation complete"
