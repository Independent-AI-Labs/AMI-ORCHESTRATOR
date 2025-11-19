"""Backup secondary module.

Handles copying backups to secondary locations (e.g., mounted AMI-BACKUP drives).
"""

import asyncio
import subprocess
import shutil
import sys
from pathlib import Path

from loguru import logger

# Add orchestrator root to path for imports
_repo_root = next((p for p in Path(__file__).resolve().parents if (p / "base").exists()), None)
if not _repo_root:
    raise RuntimeError("Unable to locate AMI orchestrator root")
sys.path.insert(0, str(_repo_root))


async def copy_to_secondary_backup(archive_path: Path) -> None:
    """Copy the backup archive to any mounted AMI-BACKUP drives.

    Args:
        archive_path: Path to the archive file to copy
    """
    # Function to check if a device has the AMI-BACKUP label
    def is_ami_backup_device(device: str) -> bool:
        try:
            # Use lsblk to get the label of the device
            result = subprocess.run(['lsblk', '-n', '-o', 'LABEL', device],
                                    capture_output=True, text=True, check=True)
            label = result.stdout.strip()
            return label == 'AMI-BACKUP'
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    ami_backup_mounts = []

    try:
        # Find all mounted filesystems with their device information
        result = subprocess.run(['findmnt', '-n', '-o', 'SOURCE,TARGET'],
                                capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')

        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2:
                device, mount_point = parts[0], parts[1]

                # Check if mount point name contains AMI-BACKUP
                if 'AMI-BACKUP' in mount_point:
                    backup_path = Path(mount_point)
                    if backup_path.exists():
                        ami_backup_mounts.append(backup_path)

                # Also check if the device label is AMI-BACKUP
                elif is_ami_backup_device(device):
                    backup_path = Path(mount_point)
                    if backup_path.exists():
                        ami_backup_mounts.append(backup_path)

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Alternative: try using mount command to list mounted filesystems
        try:
            result = subprocess.run(['mount'], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')

            for line in lines:
                # Typical mount line format: /dev/sdb1 on /media/backup type ext4 (rw,relatime) [AMI-BACKUP]
                # or: /dev/sdb1 on /media/backup type ext4 (rw,relatime) - contains AMI-BACKUP in device name
                parts = line.split()

                # Look for mount entries that might contain AMI-BACKUP
                device = None
                mount_point = None

                if 'on' in parts and 'type' in parts:
                    device_idx = parts.index('on') - 1
                    on_idx = parts.index('on')
                    type_idx = parts.index('type')

                    if device_idx >= 0:
                        device = parts[device_idx]

                    if on_idx + 1 < len(parts):
                        mount_point = parts[on_idx + 1]

                if device and mount_point:
                    # Check if mount point name contains AMI-BACKUP
                    if 'AMI-BACKUP' in mount_point:
                        backup_path = Path(mount_point)
                        if backup_path.exists():
                            ami_backup_mounts.append(backup_path)

                    # Also check if the device label is AMI-BACKUP
                    elif is_ami_backup_device(device):
                        backup_path = Path(mount_point)
                        if backup_path.exists():
                            ami_backup_mounts.append(backup_path)

        except (subprocess.CalledProcessError, FileNotFoundError):
            # If findmnt and mount commands are not available, try to look in common mount points
            common_mounts = ["/mnt", "/media", "/mount"]

            for base_mount in common_mounts:
                base_path = Path(base_mount)
                if base_path.exists():
                    # Look for subdirectories potentially containing AMI-BACKUP devices
                    for sub_path in base_path.iterdir():
                        if sub_path.is_mount():
                            # Check if this mount point itself has AMI-BACKUP in the name
                            if "AMI-BACKUP" in sub_path.name:
                                ami_backup_mounts.append(sub_path)
                            else:
                                # Try to determine the underlying device and check its label
                                # This is more complex without mount info, so we'll use blkid if available
                                try:
                                    result = subprocess.run(['findmnt', '-n', '-o', 'SOURCE', str(sub_path)],
                                                            capture_output=True, text=True, check=True)
                                    device = result.stdout.strip()
                                    if device and is_ami_backup_device(device):
                                        ami_backup_mounts.append(sub_path)
                                except (subprocess.CalledProcessError, FileNotFoundError):
                                    pass  # Continue with other paths

    if not ami_backup_mounts:
        logger.info("No AMI-BACKUP drives found (by name or label), skipping secondary backup")
        return

    # Copy the archive to each AMI-BACKUP drive
    for backup_mount in ami_backup_mounts:
        try:
            backup_dest = backup_mount / archive_path.name
            logger.info(f"Copying backup to secondary location: {backup_dest}")

            # Copy the file
            shutil.copy2(archive_path, backup_dest)
            logger.info(f"✓ Backup copied to: {backup_dest}")

        except Exception as e:
            logger.error(f"Failed to copy backup to {backup_mount}: {e}")