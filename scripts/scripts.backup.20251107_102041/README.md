# Scripts Directory

Automation scripts for the AMI Orchestrator project.

## Git Helper Scripts

### git_commit.sh
Safe git commit wrapper that stages all changes before committing.

```bash
scripts/git_commit.sh <module-path> <commit-message>
scripts/git_commit.sh <module-path> -F <file>
scripts/git_commit.sh <module-path> --amend
```

Examples:
```bash
scripts/git_commit.sh . "fix: update root"
scripts/git_commit.sh base "feat: add new feature"
scripts/git_commit.sh . -F /tmp/commit_msg.txt
```

### git_push.sh
Safe git push wrapper that runs tests before pushing.

```bash
scripts/git_push.sh <module-path> [remote] [branch]
```

Examples:
```bash
scripts/git_push.sh . origin main
scripts/git_push.sh base
```

### git_tag_all.sh
Tags all submodules and root repository with the same version tag, then pushes all tags to remote.

**Note:** This excludes external third-party submodules like `cli-agents/gemini-cli`.

```bash
bash scripts/git_tag_all.sh <version-tag> [message]
```

Examples:
```bash
bash scripts/git_tag_all.sh v1.0.0
bash scripts/git_tag_all.sh v2.1.3 "Release version 2.1.3 with bug fixes"
```

The script will:
1. Validate the tag follows semver format (vX.Y.Z)
2. Create annotated tags in all submodules
3. Tag the root repository
4. Push all tags to their respective remotes
5. Report summary of success/failures

### git_delete_tag_all.sh
Deletes a tag from all submodules and root repository (both local and remote).

**Warning:** This permanently deletes tags from remote repositories.

```bash
bash scripts/git_delete_tag_all.sh <version-tag>
```

Examples:
```bash
bash scripts/git_delete_tag_all.sh v1.0.0-test
bash scripts/git_delete_tag_all.sh v2.0.0-alpha
```

The script will:
1. Delete the tag locally from all submodules and root
2. Delete the tag from all remote repositories
3. Report summary of deletions

## Other Scripts

### check_pypi_versions.py
Check the latest available versions of all dependencies in a pyproject.toml file from PyPI.

**Features:**
- Parses all dependency sections (dependencies, optional-dependencies, dependency-groups, tool.uv.dev-dependencies)
- Queries PyPI API for the latest version of each package
- Shows comparison between current pinned version and latest available
- Supports filtering to show only outdated packages
- JSON output option for automation/scripting

**Usage:**
```bash
# Check dependencies in current directory's pyproject.toml
scripts/ami-run.sh scripts/check_pypi_versions.py

# Check specific pyproject.toml file
scripts/ami-run.sh scripts/check_pypi_versions.py path/to/pyproject.toml

# Show only outdated packages
scripts/ami-run.sh scripts/check_pypi_versions.py pyproject.toml --outdated-only

# Output as JSON for automation
scripts/ami-run.sh scripts/check_pypi_versions.py pyproject.toml --json
```

**Examples:**
```bash
# Check all modules
scripts/ami-run.sh scripts/check_pypi_versions.py base/pyproject.toml
scripts/ami-run.sh scripts/check_pypi_versions.py nodes/pyproject.toml --outdated-only

# Get outdated packages as JSON for processing
scripts/ami-run.sh scripts/check_pypi_versions.py pyproject.toml --outdated-only --json | jq '.[] | .name'
```

**Output:**
```
Package                  | Current         | Latest          | Status   | Section
-----------------------------------------------------------------------------------------------
pyyaml                   | 6.0.2           | 6.0.3           | OUTDATED | dependencies
ruff                     | 0.12.8          | 0.14.3          | OUTDATED | dependency-groups.dev
mypy                     | 1.17.1          | 1.18.2          | OUTDATED | dependency-groups.dev
loguru                   | 0.7.3           | 0.7.3           | UP-TO-DATE | dependency-groups.dev

Summary:
  Total dependencies: 24
  Up-to-date: 11
  Outdated: 13
  No pin: 0
  Unknown: 0
```

### ami-repo
Git repository server management CLI for creating and managing bare repositories with SSH access control.

**Configuration:**

Set the base directory for git repositories using the environment variable:
```bash
export GIT_SERVER_BASE_PATH=~/custom-git-repos  # Default: ~/git-repos
```

This environment variable is used by:
- All `ami-repo` commands (can also use `--base-path` flag)
- Git daemon service (both dev and systemd modes)
- Service management commands

**Repository Management:**
```bash
# Initialize git server
scripts/ami-repo init

# Create a new bare repository
scripts/ami-repo create <repo-name> [-d "description"]

# List all repositories
scripts/ami-repo list [-v]

# Get repository URL
scripts/ami-repo url <repo-name> [-p file|ssh]

# Clone a repository
scripts/ami-repo clone <repo-name> [destination]

# Show repository information
scripts/ami-repo info <repo-name>

# Delete a repository
scripts/ami-repo delete <repo-name> [-f]
```

**SSH Server Bootstrap:**
```bash
# Check/bootstrap system SSH server (port 22, requires sudo)
scripts/ami-repo bootstrap-ssh

# Bootstrap SSH server in venv (port 2222, no sudo required)
scripts/ami-repo bootstrap-ssh --install-type venv

# For venv mode, run the bootstrap script:
bash scripts/bootstrap_openssh.sh

# Start/stop/status venv SSH server
sshd-venv start
sshd-venv status
sshd-venv stop
sshd-venv restart
```

**SSH Key Management:**
```bash
# Generate new SSH key pair with secure permissions
scripts/ami-repo generate-key <name> [-t ed25519|rsa|ecdsa] [-c "comment"]

# Add SSH public key with git-only restrictions
scripts/ami-repo add-key <key-file> <name>

# List authorized SSH keys
scripts/ami-repo list-keys

# Remove an SSH key
scripts/ami-repo remove-key <name>

# Link git keys to ~/.ssh/authorized_keys
scripts/ami-repo setup-ssh
```

**Examples:**

Basic repository setup:
```bash
# Initialize and create a repository
scripts/ami-repo init
scripts/ami-repo create my-project -d "My awesome project"

# Get clone URL
scripts/ami-repo url my-project
# Output: file:///home/ami/git-repos/repos/my-project.git

# Clone to working directory
scripts/ami-repo clone my-project ~/workspace/my-project

# List all repositories with details
scripts/ami-repo list -v
```

Complete SSH access setup workflow:
```bash
# 1. Bootstrap SSH server (choose system or venv)
scripts/ami-repo bootstrap-ssh  # System mode (port 22)
# OR
scripts/ami-repo bootstrap-ssh --install-type venv  # Venv mode (port 2222)
bash scripts/bootstrap_openssh.sh  # Run if venv mode
sshd-venv start  # Start venv SSH server

# 2. Generate SSH key pair
scripts/ami-repo generate-key developer-key -t ed25519 -c "Developer laptop key"
# Private key: ~/git-repos/ssh-keys/developer-key_id_ed25519 (0600)
# Public key: ~/git-repos/ssh-keys/developer-key_id_ed25519.pub (0644)

# 3. Add key with git-only restrictions
scripts/ami-repo add-key ~/git-repos/ssh-keys/developer-key_id_ed25519.pub "developer-laptop"

# 4. List authorized keys
scripts/ami-repo list-keys

# 5. Link to SSH (if needed)
# System mode (port 22):
scripts/ami-repo setup-ssh
# Venv mode (port 2222):
ln -sf ~/git-repos/authorized_keys ~/.venv/openssh/etc/authorized_keys

# 6. Developer can now clone via SSH (no shell access, only git operations)
# System mode:
git clone ssh://ami@192.168.50.66/home/ami/git-repos/repos/my-project.git
# Venv mode:
git clone ssh://ami@192.168.50.66:2222/home/ami/git-repos/repos/my-project.git

# 7. Remove access when needed
scripts/ami-repo remove-key "developer-laptop"
```

Git server service management:
```bash
# Check service status (both dev and production modes)
scripts/ami-repo service status

# Development mode - temporary services via setup_service.py
scripts/ami-repo service start --mode dev     # Start SSH + git-daemon
scripts/ami-repo service stop --mode dev      # Stop services
scripts/ami-run.sh nodes/scripts/setup_service.py profile start git-server  # Alternative

# Production mode - persistent services via systemd
scripts/ami-repo service install-systemd      # One-time setup
scripts/ami-repo service start --mode systemd # Start services
scripts/ami-repo service stop --mode systemd  # Stop services

# Systemd services auto-start on boot and persist across sessions
systemctl --user status git-sshd git-daemon
systemctl --user enable git-sshd git-daemon   # Enable auto-start
```

**Service Modes:**

- **Development Mode** (`--mode dev`):
  - Managed by `setup_service.py` process manager
  - Services stop when terminal closes
  - Good for development and testing
  - Part of orchestrator process management

- **Production Mode** (`--mode systemd`):
  - Managed by systemd user services
  - Services persist across sessions
  - Auto-start on system boot (with lingering enabled)
  - Independent of terminal sessions
  - Automatic restart on failure

**Self-Contained Implementation:**
- ✅ SSH server: `.venv/openssh/sbin/sshd` (venv binary)
- ✅ Git daemon: `.venv/bin/git` (venv binary)
- ✅ No system dependencies required
- ✅ Fully portable via `.venv-linux/` backup
- ✅ Both binaries auto-bootstrapped during `module_setup.py`

**Security Features:**
- SSH keys are restricted to git operations only (no shell access)
- Keys cannot forward ports, X11, or agents
- Keys cannot allocate PTY (no interactive shell)
- All git operations are forced through git-shell in repos directory
- Each key is tracked with a name for easy management

### bootstrap_openssh.sh
Bootstraps OpenSSH server in the virtual environment for git-only access on non-privileged port 2222.

**Features:**
- Downloads OpenSSH binaries from Ubuntu packages (no compilation)
- Installs to `.venv/openssh/` directory
- Runs on port 2222 (no root required)
- Generates host keys automatically
- Creates `sshd-venv` control script
- Secure by default: no password auth, pubkey only, git-shell restricted
- **No system dependencies** - fully self-contained

**Usage:**
```bash
# Bootstrap OpenSSH in venv (auto-run during module_setup.py)
bash scripts/bootstrap_openssh.sh

# Control the SSH server
sshd-venv start    # Start SSH server on port 2222
sshd-venv status   # Check if running
sshd-venv stop     # Stop SSH server
sshd-venv restart  # Restart SSH server
```

**Environment Variables:**
- `SSH_PORT`: Port to listen on (default: 2222)

**Requirements:**
- None - downloads pre-built binaries from Ubuntu packages
- No compilation or build tools needed

### bootstrap_git.sh
Bootstraps Git in the virtual environment for self-contained git-daemon.

**Features:**
- Downloads Git binaries from Ubuntu packages (no compilation)
- Installs to `.venv/git/` directory
- Provides git-daemon for unauthenticated git:// access
- **No system dependencies** - fully self-contained
- Auto-creates symlink at `.venv/bin/git`

**Usage:**
```bash
# Bootstrap Git in venv (auto-run during module_setup.py)
bash scripts/bootstrap_git.sh

# Verify installation
.venv/bin/git --version
```

**Requirements:**
- None - downloads pre-built binaries from Ubuntu packages
- No compilation or build tools needed

### bootstrap_podman.sh
Bootstraps Podman and podman-compose in the virtual environment for rootless containers.

See main project documentation for Podman usage.

### ami-run.sh
Universal launcher for Python scripts using the correct virtual environment.

### ami-uv
Wrapper for uv package manager operations.

### ami-agent
Agent CLI wrapper for automation tasks.

### backup_to_gdrive.py
Automated backup utility for Google Drive.

### export_git_history.py
Export git history and statistics.

### toggle_root_protection.sh
Manage branch protection settings for the root repository.

### setup-shell.sh
Production shell environment setup script that configures comprehensive workflow aliases and PATH management.

**Quick Start:**
```bash
# Source the setup script (add to your .bashrc or .zshrc for persistence)
source scripts/setup-shell.sh
# OR
. scripts/setup-shell.sh
```

**Core Features:**

1. **Environment Configuration:**
   - Auto-detects AMI_ROOT and exports it
   - Prepends `.venv/bin` directories to PATH for all tools
   - Sets PYTHONPATH to include all modules
   - No system modifications required

2. **Wrapper Functions:**
   ```bash
   ami-run <script>        # Universal Python script runner
   ami-uv <command>        # UV package manager wrapper
   ami-agent <command>     # Agent CLI wrapper
   ami-repo <command>      # Git repository server management
   ```

3. **Service Management:**
   ```bash
   ami-service <cmd>       # Direct setup_service.py wrapper
   ami-start <process>     # Start process/profile
   ami-stop <process>      # Stop process/profile
   ami-restart <process>   # Restart process/profile
   ami-profile <cmd>       # Manage profiles
   ```

4. **Dynamic Discovery Functions:**
   ```bash
   # Auto-detect current module from PWD if not specified
   ami-test [module]       # Run tests for module (or auto-detect)
   ami-install [module]    # Run module_setup.py (or auto-detect)
   ami-setup [module]      # Alias for ami-install
   ```

5. **Code Quality:**
   ```bash
   ami-codecheck           # Run all pre-commit hooks
   ami-codecheck ruff      # Run specific hook(s)
   ami-codecheck ruff mypy # Run multiple hooks
   ```

6. **Git Shortcuts:**
   ```bash
   # Single module operations (auto-detect or specify)
   ami-status [module]     # Git status
   ami-diff [module]       # Git diff
   ami-log [module]        # Git log (last 10)

   # Multi-module operations
   ami-status-all          # Status for all modules + root
   ami-pull-all            # Pull for all modules + root
   ```

7. **Navigation Aliases:**
   ```bash
   # Jump to modules
   ami-root, ami-base, ami-browser, ami-compliance
   ami-domains, ami-files, ami-nodes, ami-streams, ami-ux

   # Jump to common directories
   ami-tests, ami-backend, ami-scripts, ami-docs
   ```

8. **Utilities:**
   ```bash
   ami-info                # Display environment info
   ami-check-storage       # Check storage backends
   ami-propagate-tests     # Propagate test runner
   ```

**Example Workflows:**

```bash
# Set up environment once per shell session
source scripts/setup-shell.sh

# Install/update a module
ami-install base

# Run tests in current directory's module
cd base/backend/dataops
ami-test  # Auto-detects base module

# Or specify module explicitly
ami-test base --filter test_dao

# Check git status for current module
cd base/backend
ami-status  # Auto-detects base module

# Or specify module
ami-status nodes

# Check all module statuses
ami-status-all

# Run code quality checks
ami-codecheck              # All hooks
ami-codecheck ruff mypy    # Specific hooks

# Start development environment
ami-start dev

# Jump between modules
ami-base
ami-nodes
ami-root
```

**Persistence:**

Add to your `~/.bashrc` or `~/.zshrc`:
```bash
# AMI Orchestrator environment
if [ -f ~/Projects/AMI-ORCHESTRATOR/scripts/setup-shell.sh ]; then
    . ~/Projects/AMI-ORCHESTRATOR/scripts/setup-shell.sh
fi
```

**Auto-Detection Logic:**

The script intelligently detects context:
- `_detect_current_module()`: Identifies which module PWD is in
- `_find_module_root()`: Finds module root by looking for `backend/` + `requirements.txt`
- `_find_nearest_module_setup()`: Locates nearest `module_setup.py` walking up from PWD

This allows you to run `ami-test`, `ami-status`, etc. from any subdirectory without specifying the module name.
