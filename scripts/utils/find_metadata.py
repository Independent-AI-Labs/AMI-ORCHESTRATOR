#!/usr/bin/env bash
""":'
exec "$(dirname "$0")/ami-run" "$0" "$@"
"""

"""Find and migrate metadata artifacts."""

import contextlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml

if TYPE_CHECKING:
    from files.backend.mcp.filesys.utils.metadata_config import resolve_artifact_path

from files.backend.mcp.filesys.utils.metadata_config import get_metadata_mappings

MIN_ARG_COUNT = 2  # Minimum number of arguments required for the script

ArtifactType = Literal["progress", "feedback", "meta"]


def load_modules() -> list[str]:
    """Load modules from YAML configuration."""
    repo_root = _ensure_repo_on_path()
    config_file = repo_root / "config" / "modules.yaml"
    if config_file.exists():
        with config_file.open() as f:
            config: dict[str, Any] = yaml.safe_load(f)
        # Use extended_modules as find_metadata needs the backend module too
        modules = config.get("extended_modules", [])
        return modules if isinstance(modules, list) else []
    # Default to hardcoded list if config doesn't exist
    return ["base", "compliance", "backend", "browser", "domains", "files", "nodes", "streams", "ux"]


def _ensure_repo_on_path() -> Path:
    """Ensure AMI orchestrator root is on sys.path."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists() and (current / "base").exists():
            sys.path.insert(0, str(current))
            return current
        current = current.parent
    raise RuntimeError("Unable to locate AMI orchestrator root")


def discover_artifacts() -> dict[str, dict[str, list[Path]]]:
    """Find all metadata artifacts in the repository.

    Returns:
        Dict mapping module name to artifact types to list of paths
    """
    artifacts = {}

    # Known module directories
    modules = load_modules()

    for module in modules:
        module_path = Path(module)
        if not module_path.exists() or not module_path.is_dir():
            continue

        module_artifacts = {
            "progress": list(module_path.rglob("progress-*.md")),
            "feedback": list(module_path.rglob("feedback-*.md")),
            "meta": [p for p in module_path.rglob("*.meta") if p.is_dir()],
        }

        # Only include if artifacts found
        if any(module_artifacts.values()):
            artifacts[module] = module_artifacts

    return artifacts


def init_mappings(artifacts: dict[str, dict[str, list[Path]]], default_root: str = ".ami-metadata", confirm: bool = False) -> None:
    """Create metadata-mappings.json from discovered artifacts.

    Args:
        artifacts: Discovered artifacts
        default_root: Default metadata root directory
        confirm: Whether to actually create mappings
    """
    mappings = []

    for module in artifacts:
        meta_path = Path(default_root) / module

        if confirm:
            meta_path.mkdir(parents=True, exist_ok=True)

            # Init git repo
            if not (meta_path / ".git").exists():
                git_executable = shutil.which("git")
                if git_executable:
                    with contextlib.suppress(subprocess.CalledProcessError):
                        subprocess.run([git_executable, "init"], cwd=meta_path, check=True, capture_output=True)

        mappings.append({"module": module, "metadataPath": str(meta_path), "isActive": True})

    config = {"defaultRoot": default_root, "mappings": mappings}

    if confirm:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        with (data_dir / "metadata-mappings.json").open("w") as f:
            json.dump(config, f, indent=2)
    else:
        pass


def migrate_artifacts(artifacts: dict[str, dict[str, list[Path]]], dry_run: bool = True) -> None:
    """Move artifacts to metadata directories.

    Args:
        artifacts: Discovered artifacts
        dry_run: If True, only print what would be done
    """
    # Ensure repo is on path
    _ensure_repo_on_path()

    total_moved = 0

    for module, types in artifacts.items():
        for artifact_type, paths in types.items():
            for src_path in paths:
                # Get relative path from module root
                try:
                    rel_path = src_path.relative_to(module)
                except ValueError:
                    continue

                # Resolve destination
                dest_path = resolve_artifact_path(module, artifact_type, str(rel_path))

                if dry_run:
                    pass
                else:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src_path), str(dest_path))
                    total_moved += 1

    if not dry_run:
        pass


def clean_artifacts(artifacts: dict[str, dict[str, list[Path]]], confirm: bool = False) -> None:
    """Delete source artifacts after migration.

    Args:
        artifacts: Discovered artifacts
        confirm: If True, actually delete files
    """
    total_deleted = 0

    for _module, types in artifacts.items():
        for _artifact_type, paths in types.items():
            for p in paths:
                if not p.exists():
                    continue

                if confirm:
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
                    total_deleted += 1
                else:
                    pass

    if confirm:
        pass


def list_mappings() -> None:
    """List current metadata mappings."""
    _ensure_repo_on_path()

    mappings = get_metadata_mappings()

    if not mappings:
        return

    for mapping in mappings:
        "Yes" if mapping.get("isActive", True) else "No"


def _handle_discover_command() -> None:
    """Handle the 'discover' command."""
    artifacts = discover_artifacts()
    for _module, types in artifacts.items():
        sum(len(paths) for paths in types.values())
        for _artifact_type, paths in types.items():
            if paths:
                pass


def _handle_init_mappings_command(confirm: bool) -> None:
    """Handle the 'init-mappings' command."""
    artifacts = discover_artifacts()
    init_mappings(artifacts, confirm=confirm)


def _handle_migrate_command(dry_run: bool) -> None:
    """Handle the 'migrate' command."""
    artifacts = discover_artifacts()
    if dry_run:
        pass
    migrate_artifacts(artifacts, dry_run=dry_run)


def _handle_clean_command(confirm: bool) -> None:
    """Handle the 'clean' command."""
    if not confirm:
        pass
    artifacts = discover_artifacts()
    clean_artifacts(artifacts, confirm=confirm)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < MIN_ARG_COUNT or (len(sys.argv) >= MIN_ARG_COUNT and sys.argv[1] in ("--help", "-h")):
        sys.exit(0 if len(sys.argv) >= MIN_ARG_COUNT and sys.argv[1] in ("--help", "-h") else 1)

    command = sys.argv[1]
    confirm = "--confirm" in sys.argv
    dry_run = not confirm

    if command == "discover":
        _handle_discover_command()
    elif command == "init-mappings":
        _handle_init_mappings_command(confirm)
    elif command == "migrate":
        _handle_migrate_command(dry_run)
    elif command == "clean":
        _handle_clean_command(confirm)
    elif command == "list-mappings":
        list_mappings()
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
