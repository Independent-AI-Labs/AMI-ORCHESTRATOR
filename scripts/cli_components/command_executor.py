#!/usr/bin/env python3
"""Command execution logic for git repository server management."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from backend.git_server.service_ops import GitServiceOps
from scripts.agents.config import get_config


def execute_command(args: Any, manager: Any) -> None:
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
        # The call to execute_service_command now needs additional arguments
        # These should be passed from the calling function or we need to refactor
        # For now, I'll add a comment to indicate what's needed

        config = get_config()

        def get_base_path() -> Path:
            return config.root

        def print_success(msg: str) -> None:
            pass

        def print_info(msg: str, verbosity: int = 0) -> None:
            pass

        execute_service_command(args, get_base_path, print_success, print_info)
    elif args.command in command_handlers:
        command_handlers[args.command]()
    else:
        raise ValueError(f"Unknown command: {args.command}")


def _service_status(get_base_path: Callable[[], Any], print_info: Callable[[str, int], None]) -> None:
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
                    print_info(svc["message"], 2)

        if systemd_services:
            for svc in systemd_services:
                if "message" in svc:
                    print_info(svc["message"], 2)


def _service_start(get_base_path: Callable[[], Any], print_success: Callable[[str], None], mode: str = "dev") -> None:
    """Start git server services."""
    base_path = get_base_path()
    repos_path = base_path / "repos"
    service_ops = GitServiceOps(base_path, repos_path)
    result = service_ops.service_start(mode)
    print_success(result.message)


def _service_stop(get_base_path: Callable[[], Any], print_success: Callable[[str], None], mode: str = "dev") -> None:
    """Stop git server services."""
    base_path = get_base_path()
    repos_path = base_path / "repos"
    service_ops = GitServiceOps(base_path, repos_path)
    result = service_ops.service_stop(mode)
    print_success(result.message)


def _service_install_systemd(get_base_path: Callable[[], Any], print_success: Callable[[str], None], print_info: Callable[[str, int], None]) -> None:
    """Install systemd user services for git server."""
    base_path = get_base_path()
    repos_path = base_path / "repos"
    service_ops = GitServiceOps(base_path, repos_path)
    result = service_ops.service_install_systemd()
    if result.data:
        print_success(f"Created {result.data['sshd_service']}")
        print_success(f"Created {result.data['daemon_service']}")
        print_success("Reloaded systemd user daemon")
        print_success("Enabled services (auto-start)")
        print_success("Enabled lingering (services persist after logout)")
        print_info(result.data["start_command"], 1)
        print_info(result.data["status_command"], 1)


def execute_service_command(args: Any, get_base_path: Callable[[], Any], print_success: Callable[[str], None], print_info: Callable[[str, int], None]) -> None:
    """Execute service subcommand."""
    service_handlers: dict[str, Callable[[], None]] = {
        "status": lambda: _service_status(get_base_path, print_info),
        "start": lambda: _service_start(get_base_path, print_success, args.service_mode),
        "stop": lambda: _service_stop(get_base_path, print_success, args.service_mode),
        "install-systemd": lambda: _service_install_systemd(get_base_path, print_success, print_info),
    }

    if args.service_action in service_handlers:
        service_handlers[args.service_action]()
    else:
        raise ValueError(f"Unknown service action: {args.service_action}")
