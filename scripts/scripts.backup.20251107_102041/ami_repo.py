#!/usr/bin/env bash
"""'exec "$(dirname "$0")/ami-run.sh" "$0" "$@" #"""

"""Git repository server management CLI.

Creates and manages bare git repositories for local/remote development.
"""

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

from base.scripts.env.paths import setup_imports

# Bootstrap imports
setup_imports(Path(__file__))

from backend.git_server.bootstrap_ops import GitBootstrapOps
from backend.git_server.repo_ops import GitRepoOps
from backend.git_server.results import BootstrapInfo, GitServerError, RepositoryError, ServiceError, SSHConfigInfo, SSHKeyError, SSHServerStatus
from backend.git_server.service_ops import GitServiceOps
from backend.git_server.ssh_ops import GitSSHOps


def get_base_path() -> Path:
    """Get git server base path from environment or default.

    Returns:
        Base path for git repositories (default: ~/git-repos)
    """
    env_path = os.getenv("GIT_SERVER_BASE_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / "git-repos"


def _print_success(message: str) -> None:
    """Print success message."""


def _print_info(message: str, indent: int = 0) -> None:
    """Print info message with optional indentation."""
    sys.stdout.write("  " * indent + message + "\n")


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

        # Initialize backend operations
        self.repo_ops = GitRepoOps(self.base_path, self.repos_path)
        self.ssh_ops = GitSSHOps(self.base_path, self.repos_path, self.keys_path, self.ssh_dir)
        self.service_ops = GitServiceOps(self.base_path, self.repos_path)
        self.bootstrap_ops = GitBootstrapOps(self.base_path)

    def init_server(self) -> None:
        """Initialize git server directory structure."""
        try:
            result = self.repo_ops.init_server()
            _print_success(result.message)
            if result.data:
                if result.data.get("already_exists"):
                    _print_info(f"Base path: {result.data['base_path']}", 1)
                    _print_info(f"Repositories: {result.data['repos_path']}", 1)
                else:
                    _print_info(f"Base path: {result.data['base_path']}", 1)
                    _print_info(f"Repositories: {result.data['repos_path']}", 1)
                    _print_info(f"README: {result.data['readme_path']}", 1)
        except (RepositoryError, GitServerError):
            sys.exit(1)

    def create_repo(self, name: str, description: str | None = None) -> None:
        """Create a new bare git repository.

        Args:
            name: Repository name (without .git extension)
            description: Optional repository description
        """
        try:
            result = self.repo_ops.create_repo(name, description)
            _print_success(result.message)
            _print_info(f"Repository: {result.repo_name}", 1)
            _print_info(f"Path: {result.repo_path}", 1)
            _print_info(f"URL: {result.url}", 1)
            if result.data and result.data.get("description"):
                _print_info(f"Description: {result.data['description']}", 1)
        except (RepositoryError, GitServerError):
            sys.exit(1)

    def list_repos(self, verbose: bool = False) -> None:
        """List all repositories.

        Args:
            verbose: Show detailed information
        """
        try:
            result = self.repo_ops.list_repos(verbose)
            _print_success(result.message)
            if result.data and result.data.get("repos"):
                for repo in result.data["repos"]:
                    _print_info(f"Path: {repo['path']}", 1)
                    _print_info(f"URL: {repo['url']}", 1)
                    if verbose and "description" in repo:
                        _print_info(f"Description: {repo['description']}", 1)
                    if verbose and "branches" in repo:
                        _print_info(f"Branches: {repo['branches']}", 1)
        except (RepositoryError, GitServerError):
            sys.exit(1)

    def get_repo_url(self, name: str, protocol: str = "file") -> None:
        """Get repository URL.

        Args:
            name: Repository name
            protocol: URL protocol (file, ssh, http)
        """
        try:
            self.repo_ops.get_repo_url(name, protocol)
        except (RepositoryError, GitServerError):
            sys.exit(1)

    def clone_repo(self, name: str, destination: Path | None = None) -> None:
        """Clone a repository.

        Args:
            name: Repository name
            destination: Destination directory (defaults to repo name without .git)
        """
        try:
            result = self.repo_ops.clone_repo(name, destination)
            _print_success(result.message)
            if result.data:
                _print_info(f"Source: {result.data['source']}", 1)
                _print_info(f"Destination: {result.data['destination']}", 1)
        except (RepositoryError, GitServerError):
            sys.exit(1)

    def delete_repo(self, name: str, force: bool = False) -> None:
        """Delete a repository.

        Args:
            name: Repository name
            force: Skip confirmation prompt
        """
        try:
            result = self.repo_ops.delete_repo(name, confirmed=force)
            if not result.success and result.data and result.data.get("requires_confirmation"):
                response = input("Type 'yes' to confirm: ")
                if response.lower() == "yes":
                    result = self.repo_ops.delete_repo(name, confirmed=True)
                    _print_success(result.message)
                else:
                    return
            else:
                _print_success(result.message)
        except (RepositoryError, GitServerError):
            sys.exit(1)

    def repo_info(self, name: str) -> None:
        """Show detailed repository information.

        Args:
            name: Repository name
        """
        try:
            result = self.repo_ops.repo_info(name)
            if result.data:
                _print_info(f"Path: {result.data['path']}", 1)
                _print_info(f"URL: {result.data['url']}", 1)
                if result.data.get("description"):
                    _print_info(f"Description: {result.data['description']}", 1)

                branches = result.data.get("branches")
                if branches:
                    for branch in branches:
                        _print_info(branch, 1)
                else:
                    pass

                if result.data.get("tags"):
                    for tag in result.data["tags"]:
                        _print_info(tag, 1)
                if result.data.get("last_commit"):
                    commit = result.data["last_commit"]
                    _print_info(f"Hash: {commit['hash']}", 1)
                    _print_info(f"Author: {commit['author']}", 1)
                    _print_info(f"Date: {commit['date']}", 1)
                    _print_info(f"Message: {commit['message']}", 1)
        except (RepositoryError, GitServerError):
            sys.exit(1)

    def add_ssh_key(self, key_file: Path, name: str) -> None:
        """Add SSH public key with git-only restrictions.

        Args:
            key_file: Path to SSH public key file
            name: Identifier for this key
        """
        try:
            result = self.ssh_ops.add_ssh_key(key_file, name)
            _print_success(result.message)
            if result.data:
                _print_info(f"Key name: {result.data['name']}", 1)
                _print_info(f"Restrictions: {result.data['restrictions']}", 1)
                _print_info(f"Link command: {result.data['link_command']}", 1)
        except (SSHKeyError, GitServerError):
            sys.exit(1)

    def list_ssh_keys(self) -> None:
        """List all authorized SSH keys."""
        try:
            result = self.ssh_ops.list_ssh_keys()
            _print_success(result.message)
            if result.data and result.data.get("keys"):
                for key in result.data["keys"]:
                    if "type" in key:
                        _print_info(f"Type: {key['type']}", 1)
                    if "fingerprint" in key:
                        _print_info(f"Fingerprint: {key['fingerprint']}", 1)
        except (SSHKeyError, GitServerError):
            sys.exit(1)

    def remove_ssh_key(self, name: str) -> None:
        """Remove an SSH key by name.

        Args:
            name: Key identifier to remove
        """
        try:
            result = self.ssh_ops.remove_ssh_key(name)
            _print_success(result.message)
        except (SSHKeyError, GitServerError):
            sys.exit(1)

    def setup_ssh_link(self) -> None:
        """Link git authorized_keys to ~/.ssh/authorized_keys."""
        try:
            result = self.ssh_ops.setup_ssh_link()
            _print_success(result.message)
            if result.data:
                _print_info(f"{result.data['link_target']} -> {result.data['link_source']}", 1)
        except (SSHKeyError, GitServerError):
            sys.exit(1)

    def generate_ssh_key(self, name: str, key_type: str = "ed25519", comment: str | None = None) -> None:
        """Generate a new SSH key pair with secure permissions.

        Args:
            name: Key name (used for filename)
            key_type: Key type (ed25519, rsa, ecdsa)
            comment: Optional comment for the key
        """
        try:
            result = self.ssh_ops.generate_ssh_key(name, key_type, comment)
            _print_success(result.message)
            if result.data:
                _print_info(f"Name: {result.data['name']}", 1)
                _print_info(f"Type: {result.data['type']}", 1)
                _print_info(f"Private key: {result.data['private_key']} (permissions: 0600)", 1)
                _print_info(f"Public key: {result.data['public_key']} (permissions: 0644)", 1)
                _print_info(result.data["fingerprint"], 1)
        except (SSHKeyError, GitServerError):
            sys.exit(1)

    def bootstrap_ssh_server(self, install_type: str = "system") -> None:
        """Bootstrap SSH server installation.

        Args:
            install_type: 'system' for system-wide or 'venv' for virtualenv
        """
        try:
            result = self.bootstrap_ops.bootstrap_ssh_server(install_type)
            if result.data and result.data.get("bootstrap_info"):
                bootstrap_info: BootstrapInfo = result.data["bootstrap_info"]
                if bootstrap_info.note:
                    pass
                if bootstrap_info.ssh_status:
                    self._print_ssh_status(bootstrap_info.ssh_status)
                if bootstrap_info.ssh_config:
                    self._print_ssh_config(bootstrap_info.ssh_config)
            _print_success(result.message)
            if result.data and result.data.get("next_steps"):
                for i, step in enumerate(result.data["next_steps"], 1):
                    _print_info(f"{i}. {step}", 1)
        except (ServiceError, GitServerError):
            sys.exit(1)

    def _print_ssh_status(self, ssh_status: SSHServerStatus) -> None:
        """Print SSH status information."""
        if ssh_status.status == "running":
            self._print_running_ssh_status(ssh_status)
        elif ssh_status.status == "not_running":
            self._print_not_running_ssh_status(ssh_status)
        else:
            self._print_unknown_ssh_status(ssh_status)

    def _print_running_ssh_status(self, ssh_status: SSHServerStatus) -> None:
        """Print running SSH server status."""
        _print_success("SSH server is running")
        if ssh_status.openssh_dir:
            _print_info(f"OpenSSH: {ssh_status.openssh_dir}", 1)
        if ssh_status.sshd_venv:
            _print_info(f"Control script: {ssh_status.sshd_venv}", 1)
        if ssh_status.sshd_path:
            _print_info(f"sshd: {ssh_status.sshd_path}", 1)

    def _print_not_running_ssh_status(self, ssh_status: SSHServerStatus) -> None:
        """Print not running SSH server status."""
        if ssh_status.start_command:
            _print_info(ssh_status.start_command, 1)
        if ssh_status.start_commands:
            for cmd in ssh_status.start_commands:
                _print_info(cmd, 1)

    def _print_unknown_ssh_status(self, ssh_status: SSHServerStatus) -> None:
        """Print unknown SSH server status."""
        if ssh_status.message:
            _print_info(ssh_status.message, 1)

    def _print_ssh_config(self, ssh_config: SSHConfigInfo) -> None:
        """Print SSH configuration information."""
        if ssh_config.status == "found":
            _print_success(f"SSH configuration: {ssh_config.config_path}")
            if ssh_config.recommended_settings:
                for setting in ssh_config.recommended_settings:
                    _print_info(setting, 1)
        else:
            pass


def service_status() -> None:
    """Check status of git server services."""
    base_path = get_base_path()
    repos_path = base_path / "repos"
    service_ops = GitServiceOps(base_path, repos_path)
    result = service_ops.service_status()
    if result.services:
        # Group by mode
        dev_services = [s for s in result.services if s.get("mode") == "dev"]
        systemd_services = [s for s in result.services if s.get("mode") == "systemd"]

        if dev_services:
            for svc in dev_services:
                if "message" in svc:
                    _print_info(svc["message"], 2)

        if systemd_services:
            for svc in systemd_services:
                if "message" in svc:
                    _print_info(svc["message"], 2)


def service_start(mode: str = "dev") -> None:
    """Start git server services."""
    base_path = get_base_path()
    repos_path = base_path / "repos"
    service_ops = GitServiceOps(base_path, repos_path)
    result = service_ops.service_start(mode)
    _print_success(result.message)


def service_stop(mode: str = "dev") -> None:
    """Stop git server services."""
    base_path = get_base_path()
    repos_path = base_path / "repos"
    service_ops = GitServiceOps(base_path, repos_path)
    result = service_ops.service_stop(mode)
    _print_success(result.message)


def service_install_systemd() -> None:
    """Install systemd user services for git server."""
    base_path = get_base_path()
    repos_path = base_path / "repos"
    service_ops = GitServiceOps(base_path, repos_path)
    result = service_ops.service_install_systemd()
    if result.data:
        _print_success(f"Created {result.data['sshd_service']}")
        _print_success(f"Created {result.data['daemon_service']}")
        _print_success("Reloaded systemd user daemon")
        _print_success("Enabled services (auto-start)")
        _print_success("Enabled lingering (services persist after logout)")
        _print_info(result.data["start_command"], 1)
        _print_info(result.data["status_command"], 1)


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Set up and return configured argument parser."""
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

    # Repository commands
    _ = subparsers.add_parser("init", help="Initialize git server directory structure")

    create_parser = subparsers.add_parser("create", help="Create a new bare repository")
    create_parser.add_argument("name", help="Repository name")
    create_parser.add_argument("-d", "--description", help="Repository description")

    list_parser = subparsers.add_parser("list", help="List all repositories")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed information")

    url_parser = subparsers.add_parser("url", help="Get repository URL")
    url_parser.add_argument("name", help="Repository name")
    url_parser.add_argument("-p", "--protocol", choices=["file", "ssh"], default="file", help="URL protocol")

    clone_parser = subparsers.add_parser("clone", help="Clone a repository")
    clone_parser.add_argument("name", help="Repository name")
    clone_parser.add_argument("destination", nargs="?", type=Path, help="Destination directory")

    delete_parser = subparsers.add_parser("delete", help="Delete a repository")
    delete_parser.add_argument("name", help="Repository name")
    delete_parser.add_argument("-f", "--force", action="store_true", help="Skip confirmation")

    info_parser = subparsers.add_parser("info", help="Show repository information")
    info_parser.add_argument("name", help="Repository name")

    # SSH commands
    add_key_parser = subparsers.add_parser("add-key", help="Add SSH public key with git-only access")
    add_key_parser.add_argument("key_file", type=Path, help="Path to SSH public key file")
    add_key_parser.add_argument("name", help="Identifier for this key")

    _ = subparsers.add_parser("list-keys", help="List authorized SSH keys")

    remove_key_parser = subparsers.add_parser("remove-key", help="Remove an SSH key")
    remove_key_parser.add_argument("name", help="Key identifier to remove")

    _ = subparsers.add_parser("setup-ssh", help="Link git keys to ~/.ssh/authorized_keys")

    generate_key_parser = subparsers.add_parser("generate-key", help="Generate new SSH key pair")
    generate_key_parser.add_argument("name", help="Key name (used for filename)")
    generate_key_parser.add_argument(
        "-t", "--type", dest="key_type", choices=["ed25519", "rsa", "ecdsa"], default="ed25519", help="Key type (default: ed25519)"
    )
    generate_key_parser.add_argument("-c", "--comment", help="Comment for the key")

    bootstrap_ssh_parser = subparsers.add_parser("bootstrap-ssh", help="Bootstrap SSH server installation")
    bootstrap_ssh_parser.add_argument(
        "--install-type", choices=["system", "venv"], default="system", help="Installation type: system-wide or virtualenv (default: system)"
    )

    # Service commands
    service_parser = subparsers.add_parser("service", help="Manage git server services")
    service_subparsers = service_parser.add_subparsers(dest="service_action", help="Service action")

    _ = service_subparsers.add_parser("status", help="Check service status")

    service_start_parser = service_subparsers.add_parser("start", help="Start services")
    service_start_parser.add_argument(
        "--mode", dest="service_mode", choices=["dev", "systemd"], default="dev", help="Service mode: dev (setup_service.py) or systemd (default: dev)"
    )

    service_stop_parser = service_subparsers.add_parser("stop", help="Stop services")
    service_stop_parser.add_argument(
        "--mode", dest="service_mode", choices=["dev", "systemd"], default="dev", help="Service mode: dev (setup_service.py) or systemd (default: dev)"
    )

    _ = service_subparsers.add_parser("install-systemd", help="Install systemd user services")

    return parser


def _execute_command(args: argparse.Namespace, manager: GitRepoManager) -> None:
    """Execute command based on parsed arguments."""
    command_handlers: dict[str, Callable[[], None]] = {
        "init": lambda: manager.init_server(),
        "create": lambda: manager.create_repo(args.name, args.description),
        "list": lambda: manager.list_repos(args.verbose),
        "url": lambda: manager.get_repo_url(args.name, args.protocol),
        "clone": lambda: manager.clone_repo(args.name, args.destination),
        "delete": lambda: manager.delete_repo(args.name, args.force),
        "info": lambda: manager.repo_info(args.name),
        "add-key": lambda: manager.add_ssh_key(args.key_file, args.name),
        "list-keys": lambda: manager.list_ssh_keys(),
        "remove-key": lambda: manager.remove_ssh_key(args.name),
        "setup-ssh": lambda: manager.setup_ssh_link(),
        "generate-key": lambda: manager.generate_ssh_key(args.name, args.key_type, args.comment),
        "bootstrap-ssh": lambda: manager.bootstrap_ssh_server(args.install_type),
    }

    if args.command == "service":
        _execute_service_command(args)
    elif args.command in command_handlers:
        command_handlers[args.command]()
    else:
        raise ValueError(f"Unknown command: {args.command}")


def _execute_service_command(args: argparse.Namespace) -> None:
    """Execute service subcommand."""
    service_handlers: dict[str, Callable[[], None]] = {
        "status": lambda: service_status(),
        "start": lambda: service_start(args.service_mode),
        "stop": lambda: service_stop(args.service_mode),
        "install-systemd": lambda: service_install_systemd(),
    }

    if args.service_action in service_handlers:
        service_handlers[args.service_action]()
    else:
        raise ValueError(f"Unknown service action: {args.service_action}")


def main() -> NoReturn:
    """Main CLI entry point."""
    parser = _setup_argument_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    manager = GitRepoManager(args.base_path)

    try:
        _execute_command(args, manager)
    except (RepositoryError, SSHKeyError, ServiceError, GitServerError):
        sys.exit(1)
    except ValueError:
        parser.print_help()
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
