"""Git server service management operations."""

import os
import subprocess
from pathlib import Path

from backend.git_server.results import ServiceError, ServiceResult


class GitServiceOps:
    """Service management operations for git server."""

    def __init__(self, base_path: Path, repos_path: Path):
        """Initialize service operations.

        Args:
            base_path: Base git server directory
            repos_path: Repositories directory
        """
        self.base_path = base_path
        self.repos_path = repos_path

    def service_status(self) -> ServiceResult:
        """Check status of git server services."""
        services = []

        # Check development mode (setup_service.py)
        try:
            result = subprocess.run(
                ["scripts/ami-run.sh", "nodes/scripts/setup_service.py", "process", "status", "git-sshd"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                services.append({"mode": "dev", "service": "git-sshd", "status": "available", "symbol": "✓"})
            else:
                services.append({"mode": "dev", "service": "git-sshd", "status": "not_configured", "symbol": "⚠"})
        except Exception as e:
            services.append({"mode": "dev", "service": "git-sshd", "status": "error", "message": str(e), "symbol": "✗"})

        # Check production mode (systemd)
        sshd_status = self._check_systemd_service_status("git-sshd")
        daemon_status = self._check_systemd_service_status("git-daemon")
        services.append({"mode": "systemd", **sshd_status})
        services.append({"mode": "systemd", **daemon_status})

        return ServiceResult(
            success=True,
            message="Service status retrieved",
            services=services,
        )

    def _check_systemd_service_status(self, service_name: str) -> dict[str, str]:
        """Check status of a systemd service.

        Args:
            service_name: Name of the systemd service to check

        Returns:
            Dict with service_name and status
        """
        try:
            result = subprocess.run(["systemctl", "--user", "is-active", service_name], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return {"service": service_name, "status": "active", "symbol": "✓"}
            return {"service": service_name, "status": "inactive", "symbol": "○"}
        except FileNotFoundError:
            return {"service": service_name, "status": "error", "message": "systemctl not found", "symbol": "⚠"}
        except Exception as e:
            return {"service": service_name, "status": "error", "message": str(e), "symbol": "⚠"}

    def service_start(self, mode: str = "dev") -> ServiceResult:
        """Start git server services.

        Args:
            mode: Service mode - 'dev' for setup_service.py, 'systemd' for production
        """
        if mode == "dev":
            result = subprocess.run(["scripts/ami-run.sh", "nodes/scripts/setup_service.py", "profile", "start", "git-server"], check=False)
            if result.returncode != 0:
                raise ServiceError("Failed to start git server services (development mode)")
            return ServiceResult(
                success=True,
                message="Git server services started (development mode)",
                data={"mode": mode},
            )
        if mode == "systemd":
            result = subprocess.run(["systemctl", "--user", "start", "git-sshd", "git-daemon"], check=False)
            if result.returncode != 0:
                raise ServiceError("Failed to start git server services (production mode)")
            return ServiceResult(
                success=True,
                message="Git server services started (production mode)",
                data={"mode": mode, "services": ["git-sshd", "git-daemon"]},
            )
        raise ServiceError(f"Unsupported mode '{mode}'. Use: dev, systemd")

    def service_stop(self, mode: str = "dev") -> ServiceResult:
        """Stop git server services.

        Args:
            mode: Service mode - 'dev' for setup_service.py, 'systemd' for production
        """
        if mode == "dev":
            result = subprocess.run(["scripts/ami-run.sh", "nodes/scripts/setup_service.py", "profile", "stop", "git-server"], check=False)
            if result.returncode != 0:
                raise ServiceError("Failed to stop git server services (development mode)")
            return ServiceResult(
                success=True,
                message="Git server services stopped (development mode)",
                data={"mode": mode},
            )
        if mode == "systemd":
            result = subprocess.run(["systemctl", "--user", "stop", "git-sshd", "git-daemon"], check=False)
            if result.returncode != 0:
                raise ServiceError("Failed to stop git server services (production mode)")
            return ServiceResult(
                success=True,
                message="Git server services stopped (production mode)",
                data={"mode": mode, "services": ["git-sshd", "git-daemon"]},
            )
        raise ServiceError(f"Unsupported mode '{mode}'. Use: dev, systemd")

    def service_install_systemd(self) -> ServiceResult:
        """Install systemd user services for git server."""
        systemd_dir = Path.home() / ".config" / "systemd" / "user"
        systemd_dir.mkdir(parents=True, exist_ok=True)

        # Create git-sshd.service
        sshd_service = systemd_dir / "git-sshd.service"
        sshd_service.write_text(
            f"""[Unit]
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
"""
        )

        # Create git-daemon.service
        daemon_service = systemd_dir / "git-daemon.service"
        daemon_service.write_text(
            f"""[Unit]
Description=Git Daemon (unauthenticated access)
After=network.target

[Service]
Type=simple
WorkingDirectory={self.base_path}
Environment=GIT_EXEC_PATH={Path.cwd()}/.venv/git/libexec/git-core
ExecStart={Path.cwd()}/.venv/bin/git daemon --reuseaddr --base-path={self.repos_path} --export-all --enable=receive-pack --verbose {self.repos_path}
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=default.target
"""
        )

        # Reload systemd
        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        except subprocess.CalledProcessError as e:
            raise ServiceError(f"Failed to reload systemd: {e}") from e

        # Enable services
        try:
            subprocess.run(["systemctl", "--user", "enable", "git-sshd", "git-daemon"], check=True)
        except subprocess.CalledProcessError as e:
            raise ServiceError(f"Failed to enable services: {e}") from e

        # Enable lingering
        subprocess.run(["loginctl", "enable-linger", os.getenv("USER", "")], check=False)

        return ServiceResult(
            success=True,
            message="Systemd services installed successfully",
            data={
                "sshd_service": str(sshd_service),
                "daemon_service": str(daemon_service),
                "start_command": "systemctl --user start git-sshd git-daemon",
                "status_command": "systemctl --user status git-sshd git-daemon",
            },
        )
