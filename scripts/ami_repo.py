#!/usr/bin/env python3
"""Git repository server management CLI.

Creates and manages bare git repositories for local/remote development.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn


def get_base_path() -> Path:
    """Get git server base path from environment or default.

    Returns:
        Base path for git repositories (default: ~/git-repos)
    """
    env_path = os.getenv("GIT_SERVER_BASE_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / "git-repos"


class GitRepoManager:
    """Manages git server and bare repositories."""

    def __init__(self, base_path: Path | None = None):
        """Initialize git repository manager.

        Args:
            base_path: Base directory for git repositories
                      (defaults to GIT_SERVER_BASE_PATH env var or ~/git-repos)
        """
        self.base_path = base_path or get_base_path()
        self.repos_path = self.base_path / "repos"
        self.keys_path = self.base_path / "authorized_keys"
        self.ssh_dir = Path.home() / ".ssh"

    def init_server(self) -> None:
        """Initialize git server directory structure."""
        # Check if already initialized (README.md exists)
        readme_path = self.base_path / "README.md"
        if readme_path.exists():
            print(f"Git server already initialized at {self.base_path}")
            print(f"Repositories directory: {self.repos_path}")
            return

        print(f"Initializing git server at {self.base_path}")

        # Create directory structure
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.repos_path.mkdir(parents=True, exist_ok=True)

        # Create README (marker for initialization)
        readme_content = """# Git Repository Server

This directory contains bare git repositories for local/remote development.

## Structure

- `repos/` - Bare git repositories

## Usage

```bash
# Create a new repository
ami-repo create <repo-name>

# List all repositories
ami-repo list

# Clone a repository
ami-repo clone <repo-name> [destination]

# Get repository URL
ami-repo url <repo-name>

# Delete a repository
ami-repo delete <repo-name>
```

## SSH Access

To access these repositories via SSH, configure your SSH server to allow access
to this directory and use URLs like:

```
ssh://user@host/path/to/git-repos/repos/repo-name.git
```

For local access, use file:// URLs:

```
file:///path/to/git-repos/repos/repo-name.git
```
"""
        readme_path.write_text(readme_content)

        print("✓ Git server initialized successfully")
        print(f"  Base directory: {self.base_path}")
        print(f"  Repositories: {self.repos_path}")
        print(f"  README: {readme_path}")

    def create_repo(self, name: str, description: str | None = None) -> None:
        """Create a new bare git repository.

        Args:
            name: Repository name (without .git extension)
            description: Optional repository description
        """
        if not self.repos_path.exists():
            print("Error: Git server not initialized. Run 'ami-repo init' first.", file=sys.stderr)
            sys.exit(1)

        # Ensure .git extension
        repo_name = name if name.endswith(".git") else f"{name}.git"
        repo_path = self.repos_path / repo_name

        if repo_path.exists():
            print(f"Error: Repository '{repo_name}' already exists at {repo_path}", file=sys.stderr)
            sys.exit(1)

        print(f"Creating bare repository: {repo_name}")

        # Initialize bare repository
        try:
            subprocess.run(
                ["git", "init", "--bare", str(repo_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to create repository: {e.stderr}", file=sys.stderr)
            sys.exit(1)

        # Set description if provided
        if description:
            desc_file = repo_path / "description"
            desc_file.write_text(description)

        # Enable git daemon (if needed)
        daemon_export = repo_path / "git-daemon-export-ok"
        daemon_export.touch()

        print("✓ Repository created successfully")
        print(f"  Path: {repo_path}")
        print(f"  File URL: file://{repo_path}")
        if description:
            print(f"  Description: {description}")

    def list_repos(self, verbose: bool = False) -> None:
        """List all repositories.

        Args:
            verbose: Show detailed information
        """
        if not self.repos_path.exists():
            print("Error: Git server not initialized. Run 'ami-repo init' first.", file=sys.stderr)
            sys.exit(1)

        repos = sorted([d for d in self.repos_path.iterdir() if d.is_dir() and d.name.endswith(".git")])

        if not repos:
            print("No repositories found")
            return

        print(f"Repositories in {self.repos_path}:\n")

        for repo in repos:
            name = repo.name
            if verbose:
                # Get description
                desc_file = repo / "description"
                description = "No description"
                if desc_file.exists():
                    desc_text = desc_file.read_text().strip()
                    if desc_text and desc_text != "Unnamed repository; edit this file 'description' to name the repository.":
                        description = desc_text

                # Get branch info
                try:
                    result = subprocess.run(
                        ["git", "--git-dir", str(repo), "branch"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    branches = [line.strip().replace("* ", "") for line in result.stdout.strip().split("\n") if line.strip()]
                    branch_info = f"{len(branches)} branch(es)" if branches else "No branches"
                except subprocess.CalledProcessError:
                    branch_info = "Unknown"

                print(f"  {name}")
                print(f"    Description: {description}")
                print(f"    Branches: {branch_info}")
                print(f"    Path: {repo}")
                print(f"    URL: file://{repo}")
                print()
            else:
                print(f"  {name}")

    def get_repo_url(self, name: str, protocol: str = "file") -> None:
        """Get repository URL.

        Args:
            name: Repository name
            protocol: URL protocol (file, ssh, http)
        """
        if not self.repos_path.exists():
            print("Error: Git server not initialized. Run 'ami-repo init' first.", file=sys.stderr)
            sys.exit(1)

        repo_name = name if name.endswith(".git") else f"{name}.git"
        repo_path = self.repos_path / repo_name

        if not repo_path.exists():
            print(f"Error: Repository '{repo_name}' not found", file=sys.stderr)
            sys.exit(1)

        if protocol == "file":
            print(f"file://{repo_path}")
        elif protocol == "ssh":
            # Get current user and host
            user = os.environ.get("USER", "user")
            host = os.environ.get("HOSTNAME", "localhost")
            print(f"ssh://{user}@{host}{repo_path}")
        else:
            print(f"Error: Unsupported protocol '{protocol}'. Use: file, ssh", file=sys.stderr)
            sys.exit(1)

    def clone_repo(self, name: str, destination: Path | None = None) -> None:
        """Clone a repository.

        Args:
            name: Repository name
            destination: Destination directory (defaults to repo name without .git)
        """
        if not self.repos_path.exists():
            print("Error: Git server not initialized. Run 'ami-repo init' first.", file=sys.stderr)
            sys.exit(1)

        repo_name = name if name.endswith(".git") else f"{name}.git"
        repo_path = self.repos_path / repo_name

        if not repo_path.exists():
            print(f"Error: Repository '{repo_name}' not found", file=sys.stderr)
            sys.exit(1)

        # Determine destination
        destination = Path.cwd() / name.replace(".git", "") if destination is None else Path(destination)

        if destination.exists():
            print(f"Error: Destination '{destination}' already exists", file=sys.stderr)
            sys.exit(1)

        print(f"Cloning {repo_name} to {destination}")

        try:
            subprocess.run(
                ["git", "clone", f"file://{repo_path}", str(destination)],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to clone repository: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"✓ Repository cloned successfully to {destination}")

    def delete_repo(self, name: str, force: bool = False) -> None:
        """Delete a repository.

        Args:
            name: Repository name
            force: Skip confirmation prompt
        """
        if not self.repos_path.exists():
            print("Error: Git server not initialized. Run 'ami-repo init' first.", file=sys.stderr)
            sys.exit(1)

        repo_name = name if name.endswith(".git") else f"{name}.git"
        repo_path = self.repos_path / repo_name

        if not repo_path.exists():
            print(f"Error: Repository '{repo_name}' not found", file=sys.stderr)
            sys.exit(1)

        if not force:
            response = input(f"Are you sure you want to delete '{repo_name}'? This cannot be undone. [y/N]: ")
            if response.lower() not in ["y", "yes"]:
                print("Deletion cancelled")
                return

        print(f"Deleting repository: {repo_name}")

        try:
            import shutil

            shutil.rmtree(repo_path)
        except OSError as e:
            print(f"Error: Failed to delete repository: {e}", file=sys.stderr)
            sys.exit(1)

        print("✓ Repository deleted successfully")

    def repo_info(self, name: str) -> None:
        """Show detailed repository information.

        Args:
            name: Repository name
        """
        if not self.repos_path.exists():
            print("Error: Git server not initialized. Run 'ami-repo init' first.", file=sys.stderr)
            sys.exit(1)

        repo_name = name if name.endswith(".git") else f"{name}.git"
        repo_path = self.repos_path / repo_name

        if not repo_path.exists():
            print(f"Error: Repository '{repo_name}' not found", file=sys.stderr)
            sys.exit(1)

        print(f"Repository: {repo_name}\n")
        print(f"Path: {repo_path}")
        print(f"File URL: file://{repo_path}")

        # Description
        desc_file = repo_path / "description"
        if desc_file.exists():
            desc_text = desc_file.read_text().strip()
            if desc_text and desc_text != "Unnamed repository; edit this file 'description' to name the repository.":
                print(f"Description: {desc_text}")

        # Branches
        try:
            result = subprocess.run(
                ["git", "--git-dir", str(repo_path), "branch", "-a"],
                capture_output=True,
                text=True,
                check=True,
            )
            branches = result.stdout.strip()
            if branches:
                print("\nBranches:")
                for line in branches.split("\n"):
                    print(f"  {line}")
        except subprocess.CalledProcessError:
            pass

        # Tags
        try:
            result = subprocess.run(
                ["git", "--git-dir", str(repo_path), "tag"],
                capture_output=True,
                text=True,
                check=True,
            )
            tags = result.stdout.strip()
            if tags:
                print("\nTags:")
                for tag in tags.split("\n"):
                    print(f"  {tag}")
        except subprocess.CalledProcessError:
            pass

        # Last commit
        try:
            result = subprocess.run(
                ["git", "--git-dir", str(repo_path), "log", "-1", "--format=%H%n%an <%ae>%n%ai%n%s"],
                capture_output=True,
                text=True,
                check=True,
            )
            commit_info = result.stdout.strip().split("\n")
            commit_info_fields = 4  # hash, author, date, message
            if len(commit_info) >= commit_info_fields:
                print("\nLast Commit:")
                print(f"  Hash: {commit_info[0]}")
                print(f"  Author: {commit_info[1]}")
                print(f"  Date: {commit_info[2]}")
                print(f"  Message: {commit_info[3]}")
        except subprocess.CalledProcessError:
            print("\nNo commits yet")

    def add_ssh_key(self, key_file: Path, name: str) -> None:
        """Add SSH public key with git-only restrictions.

        Args:
            key_file: Path to SSH public key file
            name: Identifier for this key
        """
        if not key_file.exists():
            print(f"Error: Key file not found: {key_file}", file=sys.stderr)
            sys.exit(1)

        # Read and validate public key
        try:
            key_content = key_file.read_text().strip()
        except OSError as e:
            print(f"Error: Failed to read key file: {e}", file=sys.stderr)
            sys.exit(1)

        # Basic validation - should start with ssh-rsa, ssh-ed25519, etc.
        if not any(key_content.startswith(kt) for kt in ["ssh-rsa", "ssh-ed25519", "ssh-dss", "ecdsa-sha2-"]):
            print("Error: Invalid SSH public key format", file=sys.stderr)
            sys.exit(1)

        # Create git-repos directory if needed
        if not self.base_path.exists():
            print("Error: Git server not initialized. Run 'ami-repo init' first.", file=sys.stderr)
            sys.exit(1)

        # Create authorized_keys file with restricted commands
        if not self.keys_path.exists():
            self.keys_path.touch(mode=0o600)

        # Check if key already exists
        if self.keys_path.exists():
            existing = self.keys_path.read_text()
            if key_content in existing:
                print("Error: This key is already authorized", file=sys.stderr)
                sys.exit(1)

        # Build restricted key entry
        # Restrictions: no-port-forwarding, no-X11-forwarding, no-agent-forwarding, no-pty
        # Force git-shell for all commands
        repos_path_str = str(self.repos_path.absolute())
        restrictions = (
            f'command="git-shell -c \\"cd {repos_path_str} && $SSH_ORIGINAL_COMMAND\\",' + "no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty "
        )

        key_entry = f"# {name}\n{restrictions}{key_content}\n"

        # Append to authorized_keys
        with self.keys_path.open("a") as f:
            f.write(key_entry)

        print("✓ SSH key added successfully")
        print(f"  Name: {name}")
        print(f"  Restrictions: git-only access to {repos_path_str}")
        print(f"  Keys file: {self.keys_path}")
        print("\nNext step: Link this file to ~/.ssh/authorized_keys:")
        print(f"  ln -sf {self.keys_path} ~/.ssh/authorized_keys")
        print("  (Or append to existing authorized_keys)")

    def list_ssh_keys(self) -> None:
        """List all authorized SSH keys."""
        if not self.keys_path.exists():
            print("No SSH keys configured")
            print("\nAdd keys with: ami-repo add-key <key-file> <name>")
            return

        content = self.keys_path.read_text()
        if not content.strip():
            print("No SSH keys configured")
            return

        print(f"Authorized SSH keys in {self.keys_path}:\n")

        lines = content.split("\n")
        current_name = None

        for line in lines:
            if line.startswith("# "):
                current_name = line[2:]
                print(f"  {current_name}")
            elif line.strip() and not line.startswith("#"):
                # Extract key type and fingerprint
                parts = line.split()
                min_key_parts = 2  # type + data minimum
                if len(parts) >= min_key_parts:
                    # Find the actual key (after restrictions)
                    for i, part in enumerate(parts):
                        if part.startswith(("ssh-", "ecdsa-")) and i + 1 < len(parts):
                            key_type = part
                            key_data = parts[i + 1]

                            # Calculate fingerprint
                            try:
                                import base64
                                import hashlib

                                key_bytes = base64.b64decode(key_data)
                                fingerprint = hashlib.sha256(key_bytes).hexdigest()
                                print(f"    Type: {key_type}")
                                print(f"    SHA256: {fingerprint[:16]}...")
                            except Exception:
                                print(f"    Type: {key_type}")
                            break
                print()

    def remove_ssh_key(self, name: str) -> None:
        """Remove an SSH key by name.

        Args:
            name: Key identifier to remove
        """
        if not self.keys_path.exists():
            print("Error: No keys configured", file=sys.stderr)
            sys.exit(1)

        content = self.keys_path.read_text()
        lines = content.split("\n")

        # Find and remove key entry (comment + key line)
        new_lines = []
        skip_next = False
        found = False

        for _i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            if line.strip() == f"# {name}":
                found = True
                skip_next = True  # Skip the key line after comment
                continue

            new_lines.append(line)

        if not found:
            print(f"Error: Key '{name}' not found", file=sys.stderr)
            sys.exit(1)

        # Write back
        self.keys_path.write_text("\n".join(new_lines))

        print(f"✓ SSH key '{name}' removed successfully")

    def setup_ssh_link(self) -> None:
        """Link git authorized_keys to ~/.ssh/authorized_keys."""
        if not self.keys_path.exists():
            print("Error: No keys configured. Run 'ami-repo add-key' first.", file=sys.stderr)
            sys.exit(1)

        # Ensure .ssh directory exists
        self.ssh_dir.mkdir(mode=0o700, exist_ok=True)

        ssh_authorized_keys = self.ssh_dir / "authorized_keys"

        # Check if it exists and is not a symlink
        if ssh_authorized_keys.exists() and not ssh_authorized_keys.is_symlink():
            print(f"Warning: {ssh_authorized_keys} already exists")
            print("\nOptions:")
            print(f"  1. Backup and replace: mv {ssh_authorized_keys} {ssh_authorized_keys}.backup")
            print(f"  2. Append git keys: cat {self.keys_path} >> {ssh_authorized_keys}")
            print("  3. Manual merge")
            sys.exit(1)

        # Create symlink
        if ssh_authorized_keys.is_symlink():
            ssh_authorized_keys.unlink()

        ssh_authorized_keys.symlink_to(self.keys_path)
        ssh_authorized_keys.chmod(0o600)

        print("✓ SSH authorized_keys linked successfully")
        print(f"  {ssh_authorized_keys} -> {self.keys_path}")

    def generate_ssh_key(self, name: str, key_type: str = "ed25519", comment: str | None = None) -> tuple[Path, Path]:
        """Generate a new SSH key pair with secure permissions.

        Args:
            name: Key name (used for filename)
            key_type: Key type (ed25519, rsa, ecdsa)
            comment: Optional comment for the key

        Returns:
            tuple: (private_key_path, public_key_path)
        """
        # Create keys directory in git server base
        keys_dir = self.base_path / "ssh-keys"
        keys_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        # Generate key filename
        key_path = keys_dir / f"{name}_id_{key_type}"

        # Check if key already exists
        if key_path.exists():
            print(f"Error: Key '{name}' already exists at {key_path}", file=sys.stderr)
            sys.exit(1)

        print(f"Generating SSH key pair: {name}")
        print(f"  Type: {key_type}")
        print(f"  Location: {keys_dir}")

        # Build ssh-keygen command
        cmd = [
            "ssh-keygen",
            "-t",
            key_type,
            "-f",
            str(key_path),
            "-N",
            "",  # No passphrase for automated use
            "-C",
            comment or f"{name}-{key_type}",
        ]

        # Add key-specific options
        if key_type == "rsa":
            cmd.extend(["-b", "4096"])  # 4096-bit RSA
        elif key_type == "ecdsa":
            cmd.extend(["-b", "521"])  # 521-bit ECDSA

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to generate key: {e.stderr}", file=sys.stderr)
            sys.exit(1)

        # Verify keys were created
        pub_key_path = key_path.with_suffix(".pub")
        if not key_path.exists() or not pub_key_path.exists():
            print("Error: Key generation failed - files not created", file=sys.stderr)
            sys.exit(1)

        # Set secure permissions
        key_path.chmod(0o600)  # Private key: owner read/write only
        pub_key_path.chmod(0o644)  # Public key: owner read/write, others read

        print("✓ SSH key pair generated successfully")
        print(f"  Private key: {key_path} (permissions: 0600)")
        print(f"  Public key: {pub_key_path} (permissions: 0644)")
        print("\nKey fingerprint:")
        print(f"  {result.stdout.strip()}")

        return (key_path, pub_key_path)

    def bootstrap_ssh_server(self, install_type: str = "system") -> None:
        """Bootstrap SSH server installation.

        Args:
            install_type: 'system' for system-wide or 'venv' for virtualenv
        """
        print(f"Bootstrapping SSH server ({install_type} installation)")

        if install_type == "venv":
            # Install OpenSSH in virtual environment on non-privileged port
            print("\nNote: SSH server in venv mode runs on non-privileged port (2222)")
            print("For production use on port 22, consider system installation.")

            venv_path = Path(__file__).resolve().parents[1] / ".venv"
            if not venv_path.exists():
                print(f"Error: Virtual environment not found at {venv_path}", file=sys.stderr)
                sys.exit(1)

            openssh_dir = venv_path / "openssh"
            sshd_bin = openssh_dir / "sbin" / "sshd"
            sshd_venv = venv_path / "bin" / "sshd-venv"

            # Check if OpenSSH is already installed in venv
            if sshd_bin.exists() and sshd_venv.exists():
                print(f"✓ OpenSSH already installed in venv: {openssh_dir}")
                print(f"✓ sshd control script: {sshd_venv}")

                # Check if running
                try:
                    result = subprocess.run([str(sshd_venv), "status"], check=False, capture_output=True, text=True)
                    if result.returncode == 0:
                        print("✓ SSH server is running")
                        print(result.stdout)
                    else:
                        print("⚠ SSH server is not running")
                        print("\nStart SSH server:")
                        print("  sshd-venv start")
                except subprocess.CalledProcessError:
                    print("⚠ Could not check SSH server status")
            else:
                print("\n⚠ OpenSSH not installed in venv")
                print("\nBootstrap OpenSSH in venv:")
                bootstrap_script = Path(__file__).parent / "bootstrap_openssh.sh"
                print(f"  {bootstrap_script}")
                print("\nOr run from repo root:")
                print("  bash scripts/bootstrap_openssh.sh")

                if not bootstrap_script.exists():
                    print(f"\nError: Bootstrap script not found at {bootstrap_script}", file=sys.stderr)
                    sys.exit(1)

                sys.exit(1)

        else:  # system installation
            print("\nChecking SSH server status...")

            # Check if SSH server is installed
            try:
                result = subprocess.run(["which", "sshd"], check=False, capture_output=True, text=True)

                if result.returncode == 0:
                    print(f"✓ SSH server (sshd) already installed: {result.stdout.strip()}")

                    # Check if running
                    status_result = subprocess.run(["systemctl", "is-active", "ssh"], check=False, capture_output=True, text=True)

                    if status_result.returncode == 0:
                        print("✓ SSH server is running")
                    else:
                        print("⚠ SSH server is installed but not running")
                        print("\nStart SSH server:")
                        print("  sudo systemctl start ssh")
                        print("  sudo systemctl enable ssh")
                else:
                    print("⚠ SSH server not installed")
                    print("\nInstall SSH server:")
                    print("  sudo apt-get update")
                    print("  sudo apt-get install openssh-server")
                    print("  sudo systemctl enable ssh")
                    print("  sudo systemctl start ssh")
                    sys.exit(1)

            except subprocess.CalledProcessError as e:
                print(f"Error: Failed to check SSH server: {e}", file=sys.stderr)
                sys.exit(1)

        # Verify SSH configuration (only for system mode)
        if install_type == "system":
            sshd_config = Path("/etc/ssh/sshd_config")
            if sshd_config.exists():
                print(f"\n✓ SSH configuration: {sshd_config}")
                print("\nRecommended security settings:")
                print("  PermitRootLogin no")
                print("  PubkeyAuthentication yes")
                print("  PasswordAuthentication no")
                print("  PermitEmptyPasswords no")
            else:
                print(f"\n⚠ SSH config not found at {sshd_config}")

        print("\n✓ SSH server bootstrap complete")
        print("\nNext steps:")
        if install_type == "venv":
            print("  1. Start SSH server: sshd-venv start")
            print("  2. Generate SSH key: ami-repo generate-key <name>")
            print("  3. Add key to git server: ami-repo add-key <key.pub> <name>")
            print("  4. Link authorized keys: ln -sf ~/git-repos/authorized_keys ~/.venv/openssh/etc/authorized_keys")
            print("  5. Test connection: ssh -p 2222 -i <key> user@host")
        else:
            print("  1. Generate SSH key: ami-repo generate-key <name>")
            print("  2. Add key to git server: ami-repo add-key <key.pub> <name>")
            print("  3. Test connection: ssh -i <key> user@host")


def service_status() -> None:
    """Check status of git server services."""
    print("Git Server Service Status\n")

    # Check development mode (setup_service.py)
    print("Development Mode (setup_service.py):")
    try:
        result = subprocess.run(
            ["scripts/ami-run.sh", "nodes/scripts/setup_service.py", "process", "status", "git-sshd"], capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("  ✓ git-sshd available in process manager")
        else:
            print("  ⚠ git-sshd not configured in process manager")
    except Exception as e:
        print(f"  ✗ Error checking process manager: {e}")

    # Check production mode (systemd)
    print("\nProduction Mode (systemd):")
    try:
        result = subprocess.run(["systemctl", "--user", "is-active", "git-sshd"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("  ✓ git-sshd: active")
        else:
            print("  ○ git-sshd: inactive")
    except Exception:
        print("  ⚠ systemd services not installed")

    try:
        result = subprocess.run(["systemctl", "--user", "is-active", "git-daemon"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("  ✓ git-daemon: active")
        else:
            print("  ○ git-daemon: inactive")
    except Exception:
        pass


def service_start(mode: str = "dev") -> None:
    """Start git server services."""
    if mode == "dev":
        print("Starting git server services (development mode)...")
        result = subprocess.run(["scripts/ami-run.sh", "nodes/scripts/setup_service.py", "profile", "start", "git-server"], check=False)
        if result.returncode == 0:
            print("✓ Git server services started")
        else:
            print("✗ Failed to start git server services", file=sys.stderr)
            sys.exit(1)
    elif mode == "systemd":
        print("Starting git server services (production mode)...")
        result = subprocess.run(["systemctl", "--user", "start", "git-sshd", "git-daemon"], check=False)
        if result.returncode == 0:
            print("✓ Git server services started")
        else:
            print("✗ Failed to start git server services", file=sys.stderr)
            sys.exit(1)


def service_stop(mode: str = "dev") -> None:
    """Stop git server services."""
    if mode == "dev":
        print("Stopping git server services (development mode)...")
        result = subprocess.run(["scripts/ami-run.sh", "nodes/scripts/setup_service.py", "profile", "stop", "git-server"], check=False)
        if result.returncode == 0:
            print("✓ Git server services stopped")
        else:
            print("✗ Failed to stop git server services", file=sys.stderr)
            sys.exit(1)
    elif mode == "systemd":
        print("Stopping git server services (production mode)...")
        result = subprocess.run(["systemctl", "--user", "stop", "git-sshd", "git-daemon"], check=False)
        if result.returncode == 0:
            print("✓ Git server services stopped")
        else:
            print("✗ Failed to stop git server services", file=sys.stderr)
            sys.exit(1)


def service_install_systemd() -> None:
    """Install systemd user services for git server."""
    print("Installing systemd user services...")

    base_path = get_base_path()
    repos_path = base_path / "repos"
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)

    # Create git-sshd.service
    sshd_service = systemd_dir / "git-sshd.service"
    sshd_service.write_text(f"""[Unit]
Description=Git SSH Server (venv)
After=network.target

[Service]
Type=forking
WorkingDirectory={Path.cwd()}
ExecStart={Path.cwd()}/.venv/openssh/sbin/sshd -f {Path.cwd()}/.venv/openssh/etc/sshd_config
ExecStop={Path.cwd()}/.venv/bin/sshd-venv stop
PIDFile={Path.cwd()}/.venv/openssh/var/run/sshd.pid
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=default.target
""")

    # Create git-daemon.service
    daemon_service = systemd_dir / "git-daemon.service"
    daemon_service.write_text(f"""[Unit]
Description=Git Daemon (unauthenticated access)
After=network.target

[Service]
Type=simple
WorkingDirectory={base_path}
Environment=GIT_EXEC_PATH={Path.cwd()}/.venv/git/libexec/git-core
ExecStart={Path.cwd()}/.venv/bin/git daemon --reuseaddr --base-path={repos_path} --export-all --enable=receive-pack --verbose {repos_path}
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=default.target
""")

    print(f"✓ Created {sshd_service}")
    print(f"✓ Created {daemon_service}")

    # Reload systemd
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    print("✓ Reloaded systemd user daemon")

    # Enable services
    subprocess.run(["systemctl", "--user", "enable", "git-sshd", "git-daemon"], check=True)
    print("✓ Enabled services (auto-start)")

    # Enable lingering
    subprocess.run(["loginctl", "enable-linger", os.getenv("USER", "")], check=False)
    print("✓ Enabled lingering (services persist after logout)")

    print("\n✓ Systemd services installed successfully")
    print("\nTo start services:")
    print("  systemctl --user start git-sshd git-daemon")
    print("\nTo check status:")
    print("  systemctl --user status git-sshd git-daemon")


def main() -> NoReturn:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Git repository server management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        help="Base directory for git repositories (default: $GIT_SERVER_BASE_PATH or ~/git-repos)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # init command
    _ = subparsers.add_parser("init", help="Initialize git server directory structure")

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new bare repository")
    create_parser.add_argument("name", help="Repository name")
    create_parser.add_argument("-d", "--description", help="Repository description")

    # list command
    list_parser = subparsers.add_parser("list", help="List all repositories")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed information")

    # url command
    url_parser = subparsers.add_parser("url", help="Get repository URL")
    url_parser.add_argument("name", help="Repository name")
    url_parser.add_argument("-p", "--protocol", choices=["file", "ssh"], default="file", help="URL protocol")

    # clone command
    clone_parser = subparsers.add_parser("clone", help="Clone a repository")
    clone_parser.add_argument("name", help="Repository name")
    clone_parser.add_argument("destination", nargs="?", type=Path, help="Destination directory")

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a repository")
    delete_parser.add_argument("name", help="Repository name")
    delete_parser.add_argument("-f", "--force", action="store_true", help="Skip confirmation")

    # info command
    info_parser = subparsers.add_parser("info", help="Show repository information")
    info_parser.add_argument("name", help="Repository name")

    # add-key command
    add_key_parser = subparsers.add_parser("add-key", help="Add SSH public key with git-only access")
    add_key_parser.add_argument("key_file", type=Path, help="Path to SSH public key file")
    add_key_parser.add_argument("name", help="Identifier for this key")

    # list-keys command
    _ = subparsers.add_parser("list-keys", help="List authorized SSH keys")

    # remove-key command
    remove_key_parser = subparsers.add_parser("remove-key", help="Remove an SSH key")
    remove_key_parser.add_argument("name", help="Key identifier to remove")

    # setup-ssh command
    _ = subparsers.add_parser("setup-ssh", help="Link git keys to ~/.ssh/authorized_keys")

    # generate-key command
    generate_key_parser = subparsers.add_parser("generate-key", help="Generate new SSH key pair")
    generate_key_parser.add_argument("name", help="Key name (used for filename)")
    generate_key_parser.add_argument("-t", "--type", choices=["ed25519", "rsa", "ecdsa"], default="ed25519", help="Key type (default: ed25519)")
    generate_key_parser.add_argument("-c", "--comment", help="Comment for the key")

    # bootstrap-ssh command
    bootstrap_ssh_parser = subparsers.add_parser("bootstrap-ssh", help="Bootstrap SSH server installation")
    bootstrap_ssh_parser.add_argument(
        "--install-type", choices=["system", "venv"], default="system", help="Installation type: system-wide or virtualenv (default: system)"
    )

    # service command
    service_parser = subparsers.add_parser("service", help="Manage git server services")
    service_subparsers = service_parser.add_subparsers(dest="service_action", help="Service action")

    _ = service_subparsers.add_parser("status", help="Check service status")

    service_start_parser = service_subparsers.add_parser("start", help="Start services")
    service_start_parser.add_argument(
        "--mode", choices=["dev", "systemd"], default="dev", help="Service mode: dev (setup_service.py) or systemd (default: dev)"
    )

    service_stop_parser = service_subparsers.add_parser("stop", help="Stop services")
    service_stop_parser.add_argument("--mode", choices=["dev", "systemd"], default="dev", help="Service mode: dev (setup_service.py) or systemd (default: dev)")

    _ = service_subparsers.add_parser("install-systemd", help="Install systemd user services")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    manager = GitRepoManager(args.base_path)

    if args.command == "init":
        manager.init_server()
    elif args.command == "create":
        manager.create_repo(args.name, args.description)
    elif args.command == "list":
        manager.list_repos(args.verbose)
    elif args.command == "url":
        manager.get_repo_url(args.name, args.protocol)
    elif args.command == "clone":
        manager.clone_repo(args.name, args.destination)
    elif args.command == "delete":
        manager.delete_repo(args.name, args.force)
    elif args.command == "info":
        manager.repo_info(args.name)
    elif args.command == "add-key":
        manager.add_ssh_key(args.key_file, args.name)
    elif args.command == "list-keys":
        manager.list_ssh_keys()
    elif args.command == "remove-key":
        manager.remove_ssh_key(args.name)
    elif args.command == "setup-ssh":
        manager.setup_ssh_link()
    elif args.command == "generate-key":
        priv_key, pub_key = manager.generate_ssh_key(args.name, args.type, args.comment)
        print("\nKey paths returned:")
        print(f"  Private: {priv_key}")
        print(f"  Public: {pub_key}")
    elif args.command == "bootstrap-ssh":
        manager.bootstrap_ssh_server(args.install_type)
    elif args.command == "service":
        if args.service_action == "status":
            service_status()
        elif args.service_action == "start":
            service_start(args.mode)
        elif args.service_action == "stop":
            service_stop(args.mode)
        elif args.service_action == "install-systemd":
            service_install_systemd()
        else:
            service_parser.print_help()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
