"""Configuration management for AMI automation."""

import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

# Standard /base imports pattern
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))
from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()


class Config:
    """Automation configuration."""

    def __init__(self, config_file: Path | None = None):
        """Load configuration.

        Args:
            config_file: Path to configuration file. If None, uses default.

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is malformed or invalid
            PermissionError: If config file cannot be read
        """
        self.root = ORCHESTRATOR_ROOT
        self.config_file = config_file or self.root / "scripts/config/automation.yaml"
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        """Load and parse YAML config.

        Returns:
            Parsed configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is malformed
            ValueError: If config is empty or invalid
            PermissionError: If config file cannot be read
        """
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        try:
            with self.config_file.open() as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Malformed YAML in {self.config_file}: {e}") from e
        except PermissionError as e:
            raise PermissionError(f"Cannot read config file: {self.config_file}") from e

        if not data or not isinstance(data, dict):
            raise ValueError(f"Config is empty or invalid: {self.config_file}")

        # Substitute environment variables
        substituted = self._substitute_env(data)
        if not isinstance(substituted, dict):
            raise ValueError(f"Config must be a dict, got {type(substituted)}")

        # Test mode override: explicitly disable file locking when AMI_TEST_MODE environment variable is set to "1"
        # This is required for integration tests to run without sudo permissions
        test_mode_value = os.environ.get("AMI_TEST_MODE", "")
        if test_mode_value == "1":
            if "tasks" not in substituted:
                substituted["tasks"] = {}
            if not isinstance(substituted["tasks"], dict):
                raise ValueError("tasks config must be a dict")
            substituted["tasks"]["file_locking"] = False

        return substituted

    def _substitute_env(self, data: Any) -> Any:
        """Recursively substitute ${VAR:default} patterns.

        Args:
            data: Data to process (dict, list, str, or other)

        Returns:
            Data with environment variables substituted
        """
        if isinstance(data, dict):
            return {k: self._substitute_env(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._substitute_env(v) for v in data]
        if isinstance(data, str) and "${" in data:
            # Simple substitution: ${VAR:default}
            def replace(match: re.Match[str]) -> str:
                var = match.group(1)
                default = match.group(2) or ""
                return os.environ.get(var, default)

            return re.sub(r"\$\{([A-Z_]+)(?::([^}]*))?\}", replace, data)
        return data

    def resolve_path(self, key: str, **kwargs: Any) -> Path:
        """Resolve path template with variables.

        Args:
            key: Dot-notation key to path template
            **kwargs: Variables for template substitution

        Returns:
            Absolute path with template substituted
        """
        template = self.get(key)
        if not isinstance(template, str):
            raise ValueError(f"Path template at '{key}' must be a string, got {type(template)}")
        path_str = template.format(**kwargs)
        return self.root / path_str

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot notation.

        Args:
            key: Dot-separated key (e.g., "logging.level")
            default: Default value if key not found

        Returns:
            Config value or default
        """
        keys = key.split(".")
        value: Any = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default


class _ConfigSingleton:
    """Config singleton holder to avoid global statement."""

    instance: Config | None = None


def get_config() -> Config:
    """Get global config instance.

    Returns:
        Singleton Config instance
    """
    if _ConfigSingleton.instance is None:
        _ConfigSingleton.instance = Config()
    return _ConfigSingleton.instance
