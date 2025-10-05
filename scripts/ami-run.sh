#!/usr/bin/env bash
# Wrapper for root venv python - use this instead of python3/python commands
# Bootstraps .venv from .venv-linux if needed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$ROOT_DIR/.venv"
VENV_SOURCE="$ROOT_DIR/.venv-linux"
VENV_PYTHON="$VENV_DIR/bin/python"

# Bootstrap .venv from .venv-linux if it doesn't exist
if [[ ! -d "$VENV_DIR" ]]; then
    if [[ ! -d "$VENV_SOURCE" ]]; then
        echo "Error: Source venv not found at $VENV_SOURCE" >&2
        exit 1
    fi
    echo "Bootstrapping .venv from .venv-linux..." >&2
    cp -a "$VENV_SOURCE" "$VENV_DIR"
    echo "✓ Created .venv from .venv-linux" >&2
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Error: Root venv python not found at $VENV_PYTHON" >&2
    exit 1
fi

exec "$VENV_PYTHON" "$@"
