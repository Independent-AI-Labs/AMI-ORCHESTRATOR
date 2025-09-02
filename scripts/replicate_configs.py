#!/usr/bin/env python
"""
Replicate base module configurations to all submodules.
This script ensures all submodules have the same code quality standards as /base.
"""

import shutil
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger  # noqa: E402


class ConfigReplicator:
    """Replicate configuration files from base to submodules."""

    # Configuration files to replicate from base
    CONFIG_FILES = [
        # Python version management
        "python.ver",
        # Code quality tools
        "mypy.ini",
        "pytest.ini",
        "ruff.toml",
        ".pre-commit-config.yaml",
        # Git configuration
        ".gitignore",
        # Environment configuration
        "default.env",
        # Platform-specific pre-commit configs
        ("configs/.pre-commit-config.unix.yaml", ".pre-commit-config.unix.yaml"),
        ("configs/.pre-commit-config.win.yaml", ".pre-commit-config.win.yaml"),
    ]

    # Directories that might need config subdirectory
    CONFIG_DIRS = [
        "config",
        "configs",
    ]

    # Submodules to configure
    SUBMODULES = ["browser", "compliance", "domains", "ux"]

    def __init__(self, orchestrator_root: Path):
        """Initialize the config replicator.

        Args:
            orchestrator_root: Root directory of AMI-ORCHESTRATOR
        """
        self.root = orchestrator_root
        self.base_dir = self.root / "base"

        if not self.base_dir.exists():
            raise ValueError(f"Base directory not found: {self.base_dir}")

        logger.info(f"Initializing config replicator from {self.base_dir}")

    def replicate_to_module(self, module_name: str) -> list[str]:
        """Replicate configurations to a specific module.

        Args:
            module_name: Name of the module to configure

        Returns:
            List of files that were replicated
        """
        module_path = self.root / module_name

        if not module_path.exists():
            logger.warning(f"Module directory not found: {module_path}")
            return []

        logger.info(f"Replicating configs to {module_name}")
        replicated = []

        # Create config directories if needed
        for config_dir in self.CONFIG_DIRS:
            target_dir = module_path / config_dir
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {target_dir}")

        # Replicate each configuration file
        for config_item in self.CONFIG_FILES:
            if isinstance(config_item, tuple):
                source_file, target_file = config_item
            else:
                source_file = target_file = config_item

            source = self.base_dir / source_file
            target = module_path / target_file

            if not source.exists():
                logger.warning(f"Source file not found: {source}")
                continue

            # Create target directory if needed
            target.parent.mkdir(parents=True, exist_ok=True)

            # Check if target exists and differs
            if target.exists():
                if self._files_identical(source, target):
                    logger.debug(f"File already up-to-date: {target_file}")
                    continue
                logger.info(f"Updating existing file: {target_file}")
            else:
                logger.info(f"Creating new file: {target_file}")

            # Copy the file
            shutil.copy2(source, target)
            replicated.append(str(target_file))

        # Special handling for module-specific adjustments
        self._adjust_module_configs(module_name, module_path)

        return replicated

    def _files_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files have identical content.

        Args:
            file1: First file path
            file2: Second file path

        Returns:
            True if files are identical
        """
        try:
            return file1.read_bytes() == file2.read_bytes()
        except Exception as e:
            logger.error(f"Error comparing files: {e}")
            return False

    def _adjust_module_configs(self, module_name: str, module_path: Path) -> None:
        """Make module-specific adjustments to configurations.

        Args:
            module_name: Name of the module
            module_path: Path to the module
        """
        # Adjust pytest.ini to use correct test paths
        pytest_ini = module_path / "pytest.ini"
        if pytest_ini.exists():
            content = pytest_ini.read_text()

            # Update testpaths if needed
            if "testpaths = tests" in content and not (module_path / "tests").exists():
                # Check for alternative test locations
                if (module_path / "test").exists():
                    content = content.replace("testpaths = tests", "testpaths = test")
                elif module_name == "ux":
                    # UX module might use JavaScript testing
                    content = content.replace("testpaths = tests", "testpaths = __tests__")

                pytest_ini.write_text(content)
                logger.info(f"Adjusted pytest.ini for {module_name}")

        # Adjust .gitignore for module-specific patterns
        gitignore = module_path / ".gitignore"
        if gitignore.exists() and module_name == "ux":
            content = gitignore.read_text()

            # Add Node.js specific ignores if not present
            node_ignores = [
                "\n# Node.js",
                "node_modules/",
                ".next/",
                "out/",
                "dist/",
                "*.log",
                ".env.local",
                ".env.production",
            ]

            if "node_modules" not in content:
                content += "\n".join(node_ignores)
                gitignore.write_text(content)
                logger.info("Added Node.js patterns to .gitignore for ux module")

    def replicate_all(self) -> dict[str, list[str]]:
        """Replicate configurations to all submodules.

        Returns:
            Dictionary mapping module names to list of replicated files
        """
        results = {}

        for module in self.SUBMODULES:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing module: {module}")
            logger.info(f"{'='*60}")

            replicated = self.replicate_to_module(module)
            results[module] = replicated

            if replicated:
                logger.success(f"Replicated {len(replicated)} files to {module}")
            else:
                logger.warning(f"No files replicated to {module}")

        return results

    def verify_replication(self) -> dict[str, list[str]]:
        """Verify that all modules have required configurations.

        Returns:
            Dictionary mapping module names to missing files
        """
        missing = {}

        for module in self.SUBMODULES:
            module_path = self.root / module
            if not module_path.exists():
                missing[module] = ["MODULE_NOT_FOUND"]
                continue

            module_missing = []

            # Check essential files
            essential_files = [
                "python.ver",
                "mypy.ini",
                "pytest.ini",
                "ruff.toml",
                ".pre-commit-config.yaml",
                ".gitignore",
            ]

            for file in essential_files:
                if not (module_path / file).exists():
                    module_missing.append(file)

            if module_missing:
                missing[module] = module_missing

        return missing


def main() -> int:
    """Main entry point for config replication."""
    # Determine orchestrator root
    script_path = Path(__file__).resolve()
    orchestrator_root = script_path.parent.parent

    logger.info(f"AMI-ORCHESTRATOR root: {orchestrator_root}")

    # Initialize replicator
    replicator = ConfigReplicator(orchestrator_root)

    # Replicate to all modules
    results = replicator.replicate_all()

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("REPLICATION SUMMARY")
    logger.info(f"{'='*60}")

    for module, files in results.items():
        logger.info(f"\n{module}:")
        if files:
            for file in files:
                logger.info(f"  ✓ {file}")
        else:
            logger.info("  No files replicated")

    # Verify replication
    missing = replicator.verify_replication()

    if missing:
        logger.warning(f"\n{'='*60}")
        logger.warning("MISSING CONFIGURATIONS")
        logger.warning(f"{'='*60}")

        for module, files in missing.items():
            logger.warning(f"\n{module}:")
            for file in files:
                logger.warning(f"  ✗ {file}")

        return 1

    logger.success("\n✅ All modules successfully configured!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
