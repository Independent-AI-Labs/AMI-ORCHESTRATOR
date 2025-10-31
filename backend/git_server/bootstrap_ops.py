"""SSH server bootstrap operations."""

import subprocess
from pathlib import Path

from backend.git_server.results import BootstrapInfo, ServiceError, ServiceResult, SSHConfigInfo, SSHServerStatus
from base.scripts.env.paths import find_orchestrator_root


class GitBootstrapOps:
    """SSH server bootstrap operations."""

    def __init__(self, base_path: Path):
        """Initialize bootstrap operations.

        Args:
            base_path: Base git server directory
        """
        self.base_path = base_path

    def bootstrap_ssh_server(self, install_type: str = "system") -> ServiceResult:
        """Bootstrap SSH server installation.

        Args:
            install_type: 'system' for system-wide or 'venv' for virtualenv
        """
        if install_type == "venv":
            bootstrap_data = self._bootstrap_venv_ssh()
            next_steps = self._get_venv_next_steps()
        elif install_type == "system":
            bootstrap_data = self._bootstrap_system_ssh()
            next_steps = self._get_system_next_steps()
        else:
            raise ServiceError(f"Unsupported install_type '{install_type}'. Use: system, venv")

        return ServiceResult(
            success=True,
            message="SSH server bootstrap complete",
            data={
                "install_type": install_type,
                "bootstrap_info": bootstrap_data,
                "next_steps": next_steps,
            },
        )

    def _bootstrap_venv_ssh(self) -> BootstrapInfo:
        """Bootstrap SSH server in virtual environment."""
        orchestrator_root = find_orchestrator_root(Path(__file__))
        if not orchestrator_root:
            raise ServiceError("Could not find orchestrator root")

        venv_path = orchestrator_root / ".venv"
        if not venv_path.exists():
            raise ServiceError(f"Virtual environment not found at {venv_path}")

        openssh_dir = venv_path / "openssh"
        sshd_bin = openssh_dir / "sbin" / "sshd"
        sshd_venv = venv_path / "bin" / "sshd-venv"

        # Check if OpenSSH is already installed in venv
        if sshd_bin.exists() and sshd_venv.exists():
            ssh_status = self._check_venv_ssh_running(sshd_venv, openssh_dir)
            return BootstrapInfo(
                ssh_status=ssh_status,
                note="SSH server in venv mode runs on non-privileged port (2222). For production use on port 22, consider system installation.",
            )
        # This will always raise an exception, but ruff requires explicit return
        self._get_venv_install_instructions()
        return BootstrapInfo(ssh_status=SSHServerStatus(status="error"))

    def _check_venv_ssh_running(self, sshd_venv: Path, openssh_dir: Path) -> SSHServerStatus:
        """Check if venv SSH server is running.

        Args:
            sshd_venv: Path to sshd-venv control script
            openssh_dir: Path to OpenSSH installation directory
        """
        try:
            result = subprocess.run([str(sshd_venv), "status"], check=False, capture_output=True, text=True)
            if result.returncode == 0:
                return SSHServerStatus(
                    status="running",
                    openssh_dir=str(openssh_dir),
                    sshd_venv=str(sshd_venv),
                    output=result.stdout,
                )
            return SSHServerStatus(
                status="not_running",
                openssh_dir=str(openssh_dir),
                sshd_venv=str(sshd_venv),
                start_command="sshd-venv start",
            )
        except subprocess.CalledProcessError:
            return SSHServerStatus(
                status="error",
                openssh_dir=str(openssh_dir),
                sshd_venv=str(sshd_venv),
                message="Could not check SSH server status",
            )

    def _get_venv_install_instructions(self) -> None:
        """Get instructions for installing OpenSSH in venv."""
        orchestrator_root = find_orchestrator_root(Path(__file__))
        if not orchestrator_root:
            raise ServiceError("Could not find orchestrator root")

        bootstrap_script = orchestrator_root / "scripts" / "bootstrap_openssh.sh"

        if not bootstrap_script.exists():
            raise ServiceError(f"Bootstrap script not found at {bootstrap_script}")

        raise ServiceError(f"OpenSSH not installed in venv. Bootstrap with:\n  {bootstrap_script}\nOr run from repo root:\n  bash scripts/bootstrap_openssh.sh")

    def _bootstrap_system_ssh(self) -> BootstrapInfo:
        """Bootstrap system SSH server installation."""
        try:
            result = subprocess.run(["which", "sshd"], check=False, capture_output=True, text=True)

            if result.returncode == 0:
                ssh_status = self._check_system_ssh_running(result.stdout.strip())
            else:
                self._get_system_install_instructions()
                # This line won't be reached because _get_system_install_instructions raises

        except subprocess.CalledProcessError as e:
            raise ServiceError(f"Failed to check SSH server: {e}") from e

        # Verify SSH configuration
        ssh_config = self._verify_ssh_configuration()

        return BootstrapInfo(
            ssh_status=ssh_status,
            ssh_config=ssh_config,
        )

    def _check_system_ssh_running(self, sshd_path: str) -> SSHServerStatus:
        """Check if system SSH server is running.

        Args:
            sshd_path: Path to sshd binary
        """
        status_result = subprocess.run(["systemctl", "is-active", "ssh"], check=False, capture_output=True, text=True)

        if status_result.returncode == 0:
            return SSHServerStatus(
                status="running",
                sshd_path=sshd_path,
            )
        return SSHServerStatus(
            status="not_running",
            sshd_path=sshd_path,
            start_commands=[
                "sudo systemctl start ssh",
                "sudo systemctl enable ssh",
            ],
        )

    def _get_system_install_instructions(self) -> None:
        """Get instructions for installing system SSH server."""
        instructions = [
            "sudo apt-get update",
            "sudo apt-get install openssh-server",
            "sudo systemctl enable ssh",
            "sudo systemctl start ssh",
        ]
        raise ServiceError("SSH server not installed. Install with:\n" + "\n".join(f"  {cmd}" for cmd in instructions))

    def _verify_ssh_configuration(self) -> SSHConfigInfo:
        """Verify SSH configuration for system installation."""
        sshd_config = Path("/etc/ssh/sshd_config")
        if sshd_config.exists():
            return SSHConfigInfo(
                status="found",
                config_path=str(sshd_config),
                recommended_settings=[
                    "PermitRootLogin no",
                    "PubkeyAuthentication yes",
                    "PasswordAuthentication no",
                    "PermitEmptyPasswords no",
                ],
            )
        return SSHConfigInfo(
            status="not_found",
            config_path=str(sshd_config),
            message=f"SSH config not found at {sshd_config}",
        )

    def _get_venv_next_steps(self) -> list[str]:
        """Get next steps for venv installation."""
        return [
            "Start SSH server: sshd-venv start",
            "Generate SSH key: ami-repo generate-key <name>",
            "Add key to git server: ami-repo add-key <key.pub> <name>",
            "Link authorized keys: ln -sf ~/git-repos/authorized_keys ~/.venv/openssh/etc/authorized_keys",
            "Test connection: ssh -p 2222 -i <key> user@host",
        ]

    def _get_system_next_steps(self) -> list[str]:
        """Get next steps for system installation."""
        return [
            "Generate SSH key: ami-repo generate-key <name>",
            "Add key to git server: ami-repo add-key <key.pub> <name>",
            "Test connection: ssh -i <key> user@host",
        ]
