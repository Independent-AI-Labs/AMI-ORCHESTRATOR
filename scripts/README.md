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
