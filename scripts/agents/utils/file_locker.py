"""File locking utilities for task execution."""

import os
import shutil
import subprocess
from pathlib import Path


class FileLockManager:
    """Manages file locking using chattr for task files."""

    def __init__(self, sudo_password: str | None = None):
        """Initialize file lock manager.

        Args:
            sudo_password: Sudo password if not running as root
        """
        self.sudo_password = sudo_password
        self.is_root = os.geteuid() == 0
        # Cache for filesystems that don't support chattr
        self._unsupported_filesystems: set[str] = set()

    def _filesystem_supports_chattr(self, file_path: Path) -> bool:
        """Check if filesystem supports chattr by getting mount point.

        Args:
            file_path: File to check

        Returns:
            True if chattr is supported, False otherwise
        """
        # Get absolute resolved path
        abs_path = file_path.resolve()

        # Find mount point by walking up the directory tree
        current = abs_path
        while current != current.parent:
            if str(current) in self._unsupported_filesystems:
                return False
            current = current.parent

        # Check root too
        return str(current) not in self._unsupported_filesystems

    def _mark_filesystem_unsupported(self, file_path: Path) -> None:
        """Mark a filesystem as not supporting chattr.

        Args:
            file_path: File on the unsupported filesystem
        """
        # Get the directory (mount point will be a parent)
        current = file_path.resolve().parent
        self._unsupported_filesystems.add(str(current))

    def lock_file(self, file_path: Path) -> None:
        """Lock file using chattr +i with sudo password injection.

        Args:
            file_path: File to lock

        Raises:
            subprocess.CalledProcessError: If chattr command fails
        """
        # Skip if filesystem doesn't support chattr
        if not self._filesystem_supports_chattr(file_path):
            return

        if self.is_root:
            # Already running as root, no sudo needed
            chattr_exec = shutil.which("chattr")
            if not chattr_exec:
                raise RuntimeError("chattr command not found in PATH")
            cmd = [chattr_exec, "+i", str(file_path)]
            # S603: chattr_exec validated via shutil.which()
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)  # noqa: S603
            if result.returncode != 0:
                # Check if filesystem doesn't support it
                if "Operation not supported" in result.stderr:
                    self._mark_filesystem_unsupported(file_path)
                    return
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        else:
            # Not root, use sudo with password
            sudo_exec = shutil.which("sudo")
            if not sudo_exec:
                raise RuntimeError("sudo command not found in PATH")
            chattr_exec = shutil.which("chattr")
            if not chattr_exec:
                raise RuntimeError("chattr command not found in PATH")
            cmd = [sudo_exec, "-S", chattr_exec, "+i", str(file_path)]
            # S603: sudo_exec and chattr_exec validated via shutil.which()
            process = subprocess.Popen(  # noqa: S603
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=f"{self.sudo_password}\n")

            if process.returncode != 0:
                # Check if filesystem doesn't support it
                if "Operation not supported" in stderr:
                    self._mark_filesystem_unsupported(file_path)
                    return
                raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)

    def unlock_file(self, file_path: Path) -> None:
        """Unlock file using chattr -i with sudo password injection.

        Args:
            file_path: File to unlock

        Raises:
            subprocess.CalledProcessError: If chattr command fails
        """
        if self.is_root:
            # Already running as root, no sudo needed
            chattr_exec = shutil.which("chattr")
            if not chattr_exec:
                raise RuntimeError("chattr command not found in PATH")
            cmd = [chattr_exec, "-i", str(file_path)]
            # S603: chattr_exec validated via shutil.which()
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)  # noqa: S603
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        else:
            # Not root, use sudo with password
            sudo_exec = shutil.which("sudo")
            if not sudo_exec:
                raise RuntimeError("sudo command not found in PATH")
            chattr_exec = shutil.which("chattr")
            if not chattr_exec:
                raise RuntimeError("chattr command not found in PATH")
            cmd = [sudo_exec, "-S", chattr_exec, "-i", str(file_path)]
            # S603: sudo_exec and chattr_exec validated via shutil.which()
            process = subprocess.Popen(  # noqa: S603
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=f"{self.sudo_password}\n")

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)
