"""Result classes and exceptions for git server operations."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# Custom exceptions
class GitServerError(Exception):
    """Base exception for git server operations."""


class RepositoryError(GitServerError):
    """Repository operation failed."""


class SSHKeyError(GitServerError):
    """SSH key operation failed."""


class ServiceError(GitServerError):
    """Service operation failed."""


# Result classes
class OperationResult(BaseModel):
    """Base result for operations."""

    success: bool
    message: str
    data: dict[str, Any] | None = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class RepoResult(OperationResult):
    """Result from repository operations."""

    repo_path: Path | None = None
    repo_name: str | None = None
    url: str | None = None


class SSHKeyResult(OperationResult):
    """Result from SSH key operations."""

    key_path: Path | None = None
    pub_key_path: Path | None = None
    keys_file: Path | None = None


class ServiceResult(OperationResult):
    """Result from service operations."""

    service_name: str | None = None
    status: str | None = None
    services: list[dict[str, str]] | None = None


class SSHServerStatus(BaseModel):
    """SSH server status information."""

    status: str = Field(description="Server status: running, not_running, or error")
    openssh_dir: str | None = None
    sshd_venv: str | None = None
    sshd_path: str | None = None
    start_command: str | None = None
    start_commands: list[str] | None = None
    message: str | None = None
    output: str | None = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class SSHConfigInfo(BaseModel):
    """SSH configuration information."""

    status: str = Field(description="Config status: found or not_found")
    config_path: str
    recommended_settings: list[str] | None = None
    message: str | None = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class BootstrapInfo(BaseModel):
    """Bootstrap operation information."""

    ssh_status: SSHServerStatus
    note: str | None = None
    ssh_config: SSHConfigInfo | None = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
