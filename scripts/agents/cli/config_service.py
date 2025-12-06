"""Configuration service to provide access to configuration without circular imports."""

from pathlib import Path
from typing import Any

import yaml

from scripts.agents.cli.provider_type import ProviderType


class ConfigService:
    """Service to provide configuration access without circular imports."""

    _instance = None
    _config_data: dict[str, Any] | None = None

    def __new__(cls) -> "ConfigService":
        """Singleton implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the config service."""
        # Only initialize if not already initialized
        if ConfigService._config_data is None:
            # Find orchestrator root (similar to config.py pattern)
            current_file = Path(__file__).resolve()
            try:
                root = next(p for p in current_file.parents if (p / "base").exists())
            except StopIteration:
                raise FileNotFoundError("Could not find orchestrator root with 'base' directory") from None

            config_file = root / "scripts/config/automation.yaml"
            if not config_file.exists():
                raise FileNotFoundError(f"Config file not found: {config_file}")

            with config_file.open() as f:
                config_data: dict[str, Any] = yaml.safe_load(f)

            if not config_data or not isinstance(config_data, dict):
                raise ValueError(f"Config is empty or invalid: {config_file}")

            ConfigService._config_data = config_data

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot notation."""
        keys = key.split(".")
        value = self._config_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_provider_command(self, provider: ProviderType) -> str:
        """Get the command for a specific provider."""
        # Map provider to default command
        provider_to_command = {ProviderType.CLAUDE: "ami-claude", ProviderType.QWEN: "ami-qwen", ProviderType.GEMINI: "ami-gemini"}

        # Get the default command, defaulting to Claude if provider not found
        default_cmd = provider_to_command.get(provider, "ami-claude")

        # Replace {root} template with actual root path
        current_file = Path(__file__).resolve()
        try:
            root = next(p for p in current_file.parents if (p / "base").exists())
        except StopIteration:
            raise FileNotFoundError("Could not find orchestrator root with 'base' directory") from None
        return default_cmd.format(root=str(root))

    def get_provider_default_model(self, provider: ProviderType) -> str:
        """Get the default model for a specific provider."""
        # Map provider to default model
        provider_to_model = {ProviderType.CLAUDE: "claude-sonnet-4-5", ProviderType.QWEN: "qwen-coder", ProviderType.GEMINI: "gemini-2.5-pro"}

        # Get the default model, defaulting to Claude if provider not found
        return provider_to_model.get(provider, "claude-sonnet-4-5")

    def get_provider_audit_model(self, provider: ProviderType) -> str:
        """Get the audit model for a specific provider."""
        # Map provider to audit model
        provider_to_model = {ProviderType.CLAUDE: "claude-sonnet-4-5", ProviderType.QWEN: "qwen-coder", ProviderType.GEMINI: "gemini-2.5-flash"}

        # Get the audit model, defaulting to Claude if provider not found
        return provider_to_model.get(provider, "claude-sonnet-4-5")
