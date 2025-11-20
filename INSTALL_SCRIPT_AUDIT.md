# AMI Orchestrator Install Script Audit

## Overview
The install script (`@install`) bootstraps the AMI Orchestrator development environment by setting up a complete development stack with Python, Node.js, and project dependencies.

## Bootstrap Flow

### 1. Initial Setup
- Sources the following setup scripts:
  - `./scripts/setup/common.sh` - Common utility functions and logging
  - `./scripts/setup/node.sh` - Node.js environment setup
  - `./scripts/setup/test.sh` - Testing functions
  - `./scripts/setup/submodule.sh` - Submodule handling
- Creates and uses a `.boot-linux` isolated environment for bootstrapping

### 2. Bootstrap Environment Creation
- Creates `.boot-linux` directory if it doesn't exist using `scripts/setup/bootstrap.sh`
- The `.boot-linux` environment contains:
  - Python 3.12 (bootstrapped via portable uv)
  - uv package manager
  - Git (bootstrapped)
  - Node.js environment (via nodeenv)
- All tools in `.boot-linux` are used as the base for the rest of the installation

### 3. Directory Handling
- Checks for existing `.boot-linux` directory and recreates if needed
- Handles existing directories as follows:
  - `.venv` - Created fresh during regular flow if not present, removed during recreate flow
  - `.boot-linux` - Removed and recreated during recreate flow (`--recreate` flag)
  - `cli-agents` - Required for Node.js agents installation
  - `base/` - Expected as the core module

### 4. Git Submodule Handling
- Initializes and updates git submodules recursively
- Falls back to HTTPS URLs if SSH authentication fails
- Parses .gitmodules to convert SSH URLs to HTTPS when needed

### 5. Python Environment Setup
- Uses uv to create and manage virtual environments
- Creates `.venv` directory for project dependencies
- Installs Python 3.12 as the base Python version
- Syncs dependencies from `pyproject.toml`

### 6. Node.js Environment Setup
- **Current version**: Node.js 24.11.1 (set in `scripts/setup/node.sh:73`)
- Uses nodeenv to create isolated Node.js environment in `.boot-linux/node-env`
- Installs nodeenv via bootstrapped Python
- Creates symlinks in `.boot-linux/bin/` for `node`, `npm`, `npx`

### 7. Node.js Agents Installation
- Builds Qwen CLI from source in `./cli-agents/qwen-code`
- Installs Node.js CLI agents to `.venv/node_modules`:
  - `@anthropic-ai/claude-code@2.0.10`
  - `@google/gemini-cli@0.11.3`
  - `@qwen-code/qwen-code`

### 8. Testing
- Runs tests using `base/scripts/run_tests.py`
- Tests are mandatory for installation success
- Uses pytest with parallel execution if pytest-xdist is available

### 9. Submodule Setup
- Recursively sets up all submodule directories that have either:
  - `module_setup.py` files
  - `module-setup` shell scripts
- Executes setup scripts from within each submodule directory

### 10. Shell Aliases
- Registers `ami-run` and `ami-uv` aliases in `.bashrc` and/or `.zshrc`
- Adds sourcing of `scripts/setup-shell.sh` to shell configuration files

## Command-line Options
- `--recreate`: Deletes both `.venv` and `.boot-linux` directories, then proceeds with fresh installation
- `--help`: Displays usage information

## Error Handling
- Exits on error, undefined variables, and pipe failures (`set -euo pipefail`)
- Provides fallback mechanisms for git submodule initialization (SSH to HTTPS)
- Warns rather than fails for some operations (alias registration, OpenSSH bootstrap)

## Dependencies
- Requires portable uv for Python toolchain management
- Uses curl to download portable uv binary
- Uses nodeenv for Node.js environment management
- Expects `cli-agents` directory with agent sources

## Security Considerations
- Isolates bootstrapping tools in `.boot-linux` environment
- Uses HTTPS fallback for git operations to avoid SSH key requirements
- Sets up environment in a way that prevents system Python dependencies