#!/usr/bin/env bash
# Propagate CLAUDE.md and AGENTS.md to all submodules

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Get list of submodules
SUBMODULES=$(git config --file .gitmodules --get-regexp path | awk '{ print $2 }')

if [ -z "$SUBMODULES" ]; then
  echo "No submodules found"
  exit 0
fi

# Copy files to each submodule
for submodule in $SUBMODULES; do
  if [ -d "$submodule" ]; then
    echo "Propagating to $submodule..."
    cp -f CLAUDE.md "$submodule/"
    cp -f AGENTS.md "$submodule/"
  else
    echo "Warning: Submodule directory $submodule not found, skipping"
  fi
done

echo "Propagation complete"
