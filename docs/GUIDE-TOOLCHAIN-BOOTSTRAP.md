# Toolchain Bootstrap Guide

## Overview

AMI-ORCHESTRATOR uses `uv` for fast, reliable Python dependency management across all modules. This guide explains the bootstrap process and toolchain setup.

## Quick Start

Most users should use the automated module setup:

```bash
# Automatic setup - bootstraps toolchain + creates venvs + installs dependencies
python module_setup.py
```

This internally handles:
1. Checking for `uv` installation
2. Installing Python 3.12 via `uv python install 3.12`
3. Creating per-module virtual environments
4. Syncing dependencies from `pyproject.toml`

## Manual Bootstrap (Advanced)

If you need to bootstrap `uv` separately:

```bash
# Automated bootstrap (uses package managers where available)
python base/scripts/meta/bootstrap_toolchain.py --auto --ensure-python 3.12
```

Implementation: `base/scripts/meta/bootstrap_toolchain.py:24-223`

### Platform-Specific Installation

**macOS**
```bash
brew install uv
```

**Windows**
```bash
# Via winget
winget install -e --id Astral-Software.UV

# Via Chocolatey
choco install uv
```

**Linux/macOS (direct installer)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

## Trust Model

The bootstrap script follows a trusted installation hierarchy:

1. **OS Package Managers** (preferred): Homebrew, winget, Chocolatey
   - Signed binaries from trusted catalogs

2. **Official Installers** (fallback): `https://astral.sh/uv/`
   - HTTPS-only download
   - Verifies against Astral's distribution

3. **Python Runtimes**: `uv python install 3.12`
   - Uses python-build-standalone from Gregory Szorc
   - Deterministic builds with known provenance

## Module Architecture

### Why Per-Module Venvs?

Each submodule (`base/`, `browser/`, `files/`, etc.) maintains its own:

- Isolated `.venv/` directory
- Independent `pyproject.toml` dependencies
- Module-specific lock file via `uv.lock`

**Benefits:**
- Modules are independently runnable without orchestrator
- Dependency conflicts isolated to module boundaries
- Parallel development without version clashes
- Clear ownership and update boundaries

### How Modules Bootstrap Themselves

Entry point: `module_setup.py` (exists in root + each module)

```python
# Simplified flow from module_setup.py:24-223
check_uv()                    # Verify uv available
ensure_uv_python("3.12")      # Install Python 3.12 if missing
ensure_venv(module_root)      # Create .venv with python 3.12
sync_dependencies()           # Run: uv sync --dev
install_precommit()           # Install git hooks
setup_child_submodules()      # Recursively setup children
```

## Offline / Air-Gapped Environments

For environments without internet access:

### 1. Mirror Artifacts

```bash
# Mirror uv binaries for all platforms
mkdir -p .local/mirrors/uv
# Download from https://github.com/astral-sh/uv/releases

# Mirror python-build-standalone
mkdir -p .local/mirrors/python
# Download from https://github.com/indygreg/python-build-standalone/releases
```

### 2. Configure Package Index

```bash
# Point to internal PyPI mirror
export UV_INDEX_URL=https://pypi.internal.corp/simple
export PIP_INDEX_URL=https://pypi.internal.corp/simple
```

### 3. Vendor Bootstrap Dependencies

For truly air-gapped setups, vendor the bootstrap script's dependencies (none - uses stdlib only).

## Verification

After bootstrap, verify toolchain:

```bash
# Check uv installation
uv --version
# Expected: uv 0.9.0 (or newer)

# Check Python 3.12
uv python find 3.12
# Expected: /path/to/uv/python/3.12.x/bin/python3.12

# Verify module setup
cd base/
source .venv/bin/activate
python --version
# Expected: Python 3.12.x
```

## Troubleshooting

### `uv` not found after installation

```bash
# Check common install locations
ls ~/.cargo/bin/uv       # Unix installer default
ls ~/.local/bin/uv       # Alternative location

# Add to PATH
export PATH="$HOME/.cargo/bin:$PATH"
```

### Python 3.12 not available

```bash
# Let uv install it
uv python install 3.12

# Verify installation
uv python list
```

### Module setup fails

```bash
# Check pyproject.toml exists
ls pyproject.toml

# Manually sync dependencies
uv sync --dev

# Check for lock conflicts
rm uv.lock
uv sync --dev
```

## References

- Bootstrap implementation: `base/scripts/meta/bootstrap_toolchain.py`
- Module setup: `module_setup.py` (root + each module)
- Environment utilities: `base/scripts/env/venv.py`, `base/scripts/env/paths.py`
- uv documentation: https://docs.astral.sh/uv/
