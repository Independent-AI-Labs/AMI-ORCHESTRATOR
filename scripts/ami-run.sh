#!/usr/bin/env bash
# ami-run: Universal Python execution wrapper for AMI Orchestrator
# Use this instead of python3/python/uv run/pytest commands
#
# Finds nearest .venv up the directory hierarchy from PWD
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Load scripts/.env if it exists
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Find nearest .venv by walking up from PWD
find_venv() {
    local search_dir="$PWD"
    while [[ "$search_dir" != "/" ]]; do
        if [[ -d "$search_dir/.venv" ]]; then
            echo "$search_dir/.venv"
            return 0
        fi
        search_dir="$(dirname "$search_dir")"
    done

    # Fallback to root .venv
    if [[ -d "$ROOT_DIR/.venv" ]]; then
        echo "$ROOT_DIR/.venv"
        return 0
    fi

    return 1
}

VENV_DIR="$(find_venv)"
if [[ -z "$VENV_DIR" ]]; then
    echo "Error: No .venv found in hierarchy from $PWD to root" >&2
    exit 1
fi

VENV_PYTHON="$VENV_DIR/bin/python"
ROOT_VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
VENV_SOURCE="$ROOT_DIR/.venv-linux"

# Bootstrap .venv from .venv-linux if it doesn't exist
if [[ ! -d "$VENV_DIR" ]]; then
    if [[ ! -d "$VENV_SOURCE" ]]; then
        echo "Error: Source venv not found at $VENV_SOURCE" >&2
        exit 1
    fi
    echo "Bootstrapping .venv from .venv-linux..."
    cp -a "$VENV_SOURCE" "$VENV_DIR"
    echo "✓ Created .venv from .venv-linux"
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Error: Root venv python not found at $VENV_PYTHON" >&2
    exit 1
fi

# Add venv/bin to PATH so podman and other venv tools are available
export PATH="$VENV_DIR/bin:$PATH"

# Special command: install (alias for setup)
# Special command: setup
if [[ "$1" == "install" ]] || [[ "$1" == "setup" ]]; then
    shift
    if [[ $# -eq 0 ]]; then
        # Run root module_setup using root venv python
        exec "$ROOT_VENV_PYTHON" "$ROOT_DIR/module_setup.py"
    else
        # Run specific module setup using root venv python
        MODULE="$1"
        shift
        if [[ -f "$ROOT_DIR/$MODULE/module_setup.py" ]]; then
            exec "$ROOT_VENV_PYTHON" "$ROOT_DIR/$MODULE/module_setup.py" "$@"
        else
            echo "Error: module_setup.py not found in $MODULE" >&2
            exit 1
        fi
    fi
fi

# Regular execution: run python with all args using nearest .venv python
exec "$VENV_PYTHON" "$@"
