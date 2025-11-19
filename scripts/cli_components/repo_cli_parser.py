#!/usr/bin/env python3
"""CLI argument parser for git repository server management."""

import argparse
from pathlib import Path


def setup_argument_parser() -> argparse.ArgumentParser:
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
