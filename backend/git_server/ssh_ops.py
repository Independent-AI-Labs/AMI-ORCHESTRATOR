"""SSH key management operations."""

import base64
import hashlib
import subprocess
from pathlib import Path

from backend.git_server.results import SSHKeyError, SSHKeyResult


class GitSSHOps:
    """SSH key management operations."""

    def __init__(self, base_path: Path, repos_path: Path, keys_path: Path, ssh_dir: Path):
        """Initialize SSH operations.

        Args:
            base_path: Base git server directory
            repos_path: Repositories directory
            keys_path: Path to authorized_keys file
            ssh_dir: SSH configuration directory
        """
        self.base_path = base_path
        self.repos_path = repos_path
        self.keys_path = keys_path
        self.ssh_dir = ssh_dir

    def add_ssh_key(self, key_file: Path, name: str) -> SSHKeyResult:
        """Add SSH public key with git-only restrictions."""
        if not key_file.exists():
            raise SSHKeyError(f"Key file not found: {key_file}")

        try:
            key_content = key_file.read_text().strip()
        except OSError as e:
            raise SSHKeyError(f"Failed to read key file: {e}") from e

        if not any(key_content.startswith(kt) for kt in ["ssh-rsa", "ssh-ed25519", "ssh-dss", "ecdsa-sha2-"]):
            raise SSHKeyError("Invalid SSH public key format")

        if not self.base_path.exists():
            raise SSHKeyError("Git server not initialized. Run 'ami-repo init' first.")

        if not self.keys_path.exists():
            self.keys_path.touch(mode=0o600)

        if self.keys_path.exists():
            existing = self.keys_path.read_text()
            if key_content in existing:
                raise SSHKeyError("This key is already authorized")

        repos_path_str = str(self.repos_path.absolute())
        restrictions = (
            f'command="git-shell -c \\"cd {repos_path_str} && $SSH_ORIGINAL_COMMAND\\",' + "no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty "
        )

        key_entry = f"# {name}\n{restrictions}{key_content}\n"

        with self.keys_path.open("a") as f:
            f.write(key_entry)

        return SSHKeyResult(
            success=True,
            message="SSH key added successfully",
            keys_file=self.keys_path,
            data={"name": name, "restrictions": f"git-only access to {repos_path_str}", "link_command": f"ln -sf {self.keys_path} ~/.ssh/authorized_keys"},
        )

    def _parse_key_info(self, line: str) -> tuple[str, str] | None:
        """Parse SSH key line to extract type and fingerprint.

        Returns:
            Tuple of (key_type, fingerprint) or None if parsing fails
        """
        parts = line.split()
        min_key_parts = 2
        if len(parts) < min_key_parts:
            return None

        for i, part in enumerate(parts):
            if part.startswith(("ssh-", "ecdsa-")) and i + 1 < len(parts):
                key_type = part
                key_data = parts[i + 1]

                try:
                    key_bytes = base64.b64decode(key_data)
                    fingerprint = hashlib.sha256(key_bytes).hexdigest()
                    return (key_type, fingerprint)
                except Exception:
                    return (key_type, "")

        return None

    def list_ssh_keys(self) -> SSHKeyResult:
        """List all authorized SSH keys."""
        if not self.keys_path.exists():
            return SSHKeyResult(success=True, message="No SSH keys configured", data={"keys": [], "keys_path": str(self.keys_path)})

        content = self.keys_path.read_text()
        if not content.strip():
            return SSHKeyResult(success=True, message="No SSH keys configured", data={"keys": [], "keys_path": str(self.keys_path)})

        lines = content.split("\n")
        keys = []
        current_key = None

        for line in lines:
            if line.startswith("# "):
                if current_key:
                    keys.append(current_key)
                current_key = {"name": line[2:]}
            elif line.strip() and not line.startswith("#") and current_key:
                key_info = self._parse_key_info(line)
                if key_info:
                    key_type, fingerprint = key_info
                    current_key["type"] = key_type
                    current_key["fingerprint"] = fingerprint[:16] + "..." if fingerprint else ""

        if current_key:
            keys.append(current_key)

        return SSHKeyResult(
            success=True,
            message=f"Found {len(keys)} SSH key(s)",
            keys_file=self.keys_path,
            data={"keys": keys, "keys_path": str(self.keys_path)},
        )

    def remove_ssh_key(self, name: str) -> SSHKeyResult:
        """Remove an SSH key by name."""
        if not self.keys_path.exists():
            raise SSHKeyError("No keys configured")

        content = self.keys_path.read_text()
        lines = content.split("\n")

        new_lines = []
        skip_next = False
        found = False

        for line in lines:
            if skip_next:
                skip_next = False
                continue

            if line.strip() == f"# {name}":
                found = True
                skip_next = True
                continue

            new_lines.append(line)

        if not found:
            raise SSHKeyError(f"Key '{name}' not found")

        self.keys_path.write_text("\n".join(new_lines))

        return SSHKeyResult(success=True, message=f"SSH key '{name}' removed successfully", keys_file=self.keys_path, data={"removed_key": name})

    def setup_ssh_link(self) -> SSHKeyResult:
        """Link git authorized_keys to ~/.ssh/authorized_keys."""
        if not self.keys_path.exists():
            raise SSHKeyError("No keys configured. Run 'ami-repo add-key' first.")

        self.ssh_dir.mkdir(mode=0o700, exist_ok=True)

        ssh_authorized_keys = self.ssh_dir / "authorized_keys"

        if ssh_authorized_keys.exists() and not ssh_authorized_keys.is_symlink():
            raise SSHKeyError(
                f"File {ssh_authorized_keys} already exists. Options:\n"
                f"  1. Backup and replace: mv {ssh_authorized_keys} {ssh_authorized_keys}.backup\n"
                f"  2. Append git keys: cat {self.keys_path} >> {ssh_authorized_keys}\n"
                f"  3. Manual merge"
            )

        if ssh_authorized_keys.is_symlink():
            ssh_authorized_keys.unlink()

        ssh_authorized_keys.symlink_to(self.keys_path)
        ssh_authorized_keys.chmod(0o600)

        return SSHKeyResult(
            success=True,
            message="SSH authorized_keys linked successfully",
            keys_file=self.keys_path,
            data={"link_source": str(self.keys_path), "link_target": str(ssh_authorized_keys)},
        )

    def generate_ssh_key(self, name: str, key_type: str = "ed25519", comment: str | None = None) -> SSHKeyResult:
        """Generate a new SSH key pair with secure permissions."""
        keys_dir = self.base_path / "ssh-keys"
        keys_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        key_path = keys_dir / f"{name}_id_{key_type}"

        if key_path.exists():
            raise SSHKeyError(f"Key '{name}' already exists at {key_path}")

        cmd = [
            "ssh-keygen",
            "-t",
            key_type,
            "-f",
            str(key_path),
            "-N",
            "",
            "-C",
            comment or f"{name}-{key_type}",
        ]

        if key_type == "rsa":
            cmd.extend(["-b", "4096"])
        elif key_type == "ecdsa":
            cmd.extend(["-b", "521"])

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise SSHKeyError(f"Failed to generate key: {e.stderr}") from e

        pub_key_path = key_path.with_suffix(".pub")
        if not key_path.exists() or not pub_key_path.exists():
            raise SSHKeyError("Key generation failed - files not created")

        key_path.chmod(0o600)
        pub_key_path.chmod(0o644)

        return SSHKeyResult(
            success=True,
            message="SSH key pair generated successfully",
            key_path=key_path,
            pub_key_path=pub_key_path,
            data={
                "name": name,
                "type": key_type,
                "private_key": str(key_path),
                "public_key": str(pub_key_path),
                "fingerprint": result.stdout.strip(),
                "keys_dir": str(keys_dir),
            },
        )
