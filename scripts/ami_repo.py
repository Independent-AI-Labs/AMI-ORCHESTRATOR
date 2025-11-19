#!/usr/bin/env bash
""":'
exec "$(dirname "$0")/ami-run" "$0" "$@"
"""

"""Git repository server management CLI.

Creates and manages bare git repositories for local/remote development.
"""

import sys  # noqa: E402
from collections.abc import Callable  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, NoReturn  # noqa: E402

from base.scripts.env.paths import setup_imports  # noqa: E402

# Bootstrap imports
setup_imports(Path(__file__))

from backend.git_server.bootstrap_ops import GitBootstrapOps
from backend.git_server.repo_ops import GitRepoOps
from backend.git_server.results import BootstrapInfo, GitServerError, RepositoryError, ServiceError, SSHConfigInfo, SSHKeyError, SSHServerStatus
from backend.git_server.service_ops import GitServiceOps
from backend.git_server.ssh_ops import GitSSHOps
from scripts.cli_components.cli_helpers import print_error, print_info, print_success
from scripts.cli_components.command_executor import execute_service_command
from scripts.cli_components.path_utils import get_base_path
from scripts.cli_components.repo_cli_parser import setup_argument_parser


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
            print_success(result.message)
            if result.data:
                if result.data.get("already_exists"):
                    print_info(f"Base path: {result.data['base_path']}", 1)
                    print_info(f"Repositories: {result.data['repos_path']}", 1)
                else:
                    print_info(f"Base path: {result.data['base_path']}", 1)
                    print_info(f"Repositories: {result.data['repos_path']}", 1)
                    print_info(f"README: {result.data['readme_path']}", 1)
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
            print_success(result.message)
            print_info(f"Repository: {result.repo_name}", 1)
            print_info(f"Path: {result.repo_path}", 1)
            print_info(f"URL: {result.url}", 1)
            if result.data and result.data.get("description"):
                print_info(f"Description: {result.data['description']}", 1)
        except (RepositoryError, GitServerError):
            sys.exit(1)

    def list_repos(self, verbose: bool = False) -> None:
        """List all repositories.

        Args:
            verbose: Show detailed information
        """
        try:
            result = self.repo_ops.list_repos(verbose)
            print_success(result.message)
            if result.data and result.data.get("repos"):
                for repo in result.data["repos"]:
                    print_info(f"Path: {repo['path']}", 1)
                    print_info(f"URL: {repo['url']}", 1)
                    if verbose and "description" in repo:
                        print_info(f"Description: {repo['description']}", 1)
                    if verbose and "branches" in repo:
                        print_info(f"Branches: {repo['branches']}", 1)
            else:
                # Print message when no repositories exist
                print_info("No repositories found")
        except (RepositoryError, GitServerError):
            sys.exit(1)

    def get_repo_url(self, name: str, protocol: str = "file") -> None:
        """Get repository URL.

        Args:
            name: Repository name
            protocol: URL protocol (file, ssh, http)
        """
        try:
            result = self.repo_ops.get_repo_url(name, protocol)
            if result.url is not None:
                print_info(result.url)  # Print the URL to stdout
            else:
                print_error("No URL returned for repository")
                sys.exit(1)
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
            print_success(result.message)
            if result.data:
                print_info(f"Source: {result.data['source']}", 1)
                print_info(f"Destination: {result.data['destination']}", 1)
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
                    print_success(result.message)
                else:
                    return
            else:
                print_success(result.message)
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
                print_info(f"Path: {result.data['path']}", 1)
                print_info(f"URL: {result.data['url']}", 1)
                if result.data.get("description"):
                    print_info(f"Description: {result.data['description']}", 1)

                branches = result.data.get("branches")
                if branches:
                    for branch in branches:
                        print_info(branch, 1)
                else:
                    print_info("No commits yet", 1)

                if result.data.get("tags"):
                    for tag in result.data["tags"]:
                        print_info(tag, 1)
                if result.data.get("last_commit"):
                    commit = result.data["last_commit"]
                    print_info(f"Hash: {commit['hash']}", 1)
                    print_info(f"Author: {commit['author']}", 1)
                    print_info(f"Date: {commit['date']}", 1)
                    print_info(f"Message: {commit['message']}", 1)
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
            print_success(result.message)
            if result.data:
                print_info(f"Key name: {result.data['name']}", 1)
                print_info(f"Restrictions: {result.data['restrictions']}", 1)
                print_info(f"Link command: {result.data['link_command']}", 1)
        except (SSHKeyError, GitServerError):
            sys.exit(1)

    def list_ssh_keys(self) -> None:
        """List all authorized SSH keys."""
        try:
            result = self.ssh_ops.list_ssh_keys()
            print_success(result.message)
            if result.data and result.data.get("keys"):
                for key in result.data["keys"]:
                    if "name" in key:
                        print_info(f"Name: {key['name']}", 1)
                    if "type" in key:
                        print_info(f"Type: {key['type']}", 1)
                    if "fingerprint" in key:
                        print_info(f"Fingerprint: {key['fingerprint']}", 1)
            else:
                # Print message when no SSH keys exist
                print_info("No SSH keys configured")
        except (SSHKeyError, GitServerError):
            sys.exit(1)

    def remove_ssh_key(self, name: str) -> None:
        """Remove an SSH key by name.

        Args:
            name: Key identifier to remove
        """
        try:
            result = self.ssh_ops.remove_ssh_key(name)
            print_success(result.message)
        except (SSHKeyError, GitServerError):
            sys.exit(1)

    def setup_ssh_link(self) -> None:
        """Link git authorized_keys to ~/.ssh/authorized_keys."""
        try:
            result = self.ssh_ops.setup_ssh_link()
            print_success(result.message)
            if result.data:
                print_info(f"{result.data['link_target']} -> {result.data['link_source']}", 1)
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
            print_success(result.message)
            if result.data:
                print_info(f"Name: {result.data['name']}", 1)
                print_info(f"Type: {result.data['type']}", 1)
                print_info(f"Private key: {result.data['private_key']} (permissions: 0600)", 1)
                print_info(f"Public key: {result.data['public_key']} (permissions: 0644)", 1)
                print_info(result.data["fingerprint"], 1)
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
            print_success(result.message)
            if result.data and result.data.get("next_steps"):
                for i, step in enumerate(result.data["next_steps"], 1):
                    print_info(f"{i}. {step}", 1)
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
        print_success("SSH server is running")
        if ssh_status.openssh_dir:
            print_info(f"OpenSSH: {ssh_status.openssh_dir}", 1)
        if ssh_status.sshd_venv:
            print_info(f"Control script: {ssh_status.sshd_venv}", 1)
        if ssh_status.sshd_path:
            print_info(f"sshd: {ssh_status.sshd_path}", 1)

    def _print_not_running_ssh_status(self, ssh_status: SSHServerStatus) -> None:
        """Print not running SSH server status."""
        if ssh_status.start_command:
            print_info(ssh_status.start_command, 1)
        if ssh_status.start_commands:
            for cmd in ssh_status.start_commands:
                print_info(cmd, 1)

    def _print_unknown_ssh_status(self, ssh_status: SSHServerStatus) -> None:
        """Print unknown SSH server status."""
        if ssh_status.message:
            print_info(ssh_status.message, 1)

    def _print_ssh_config(self, ssh_config: SSHConfigInfo) -> None:
        """Print SSH configuration information."""
        if ssh_config.status == "found":
            print_success(f"SSH configuration: {ssh_config.config_path}")
            if ssh_config.recommended_settings:
                for setting in ssh_config.recommended_settings:
                    print_info(setting, 1)
        else:
            pass


def execute_command(args: Any, manager: GitRepoManager) -> None:
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
        execute_service_command(args, get_base_path, print_success, print_info)
    elif args.command in command_handlers:
        command_handlers[args.command]()
    else:
        raise ValueError(f"Unknown command: {args.command}")


def main() -> NoReturn:
    """Main CLI entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    manager = GitRepoManager(args.base_path)

    try:
        execute_command(args, manager)
    except (RepositoryError, SSHKeyError, ServiceError, GitServerError):
        sys.exit(1)
    except ValueError:
        parser.print_help()
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
