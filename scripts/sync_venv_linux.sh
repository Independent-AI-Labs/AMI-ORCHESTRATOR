#!/usr/bin/env bash
# Sync .venv to .venv-linux
# This overwrites .venv-linux with the contents of .venv

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORCHESTRATOR_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ORCHESTRATOR_ROOT"

echo "Syncing .venv to .venv-linux..."
echo "==========================================="

if [ ! -d ".venv" ]; then
    echo "✗ ERROR: .venv does not exist"
    exit 1
fi

echo "Removing old .venv-linux..."
rm -rf .venv-linux

echo "Copying .venv to .venv-linux..."
cp -r .venv .venv-linux

echo ""
echo "==========================================="
echo "✓ Successfully synced .venv to .venv-linux"
