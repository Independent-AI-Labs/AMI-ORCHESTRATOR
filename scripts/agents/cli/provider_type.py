"""Provider enum for CLI agent implementations."""

from enum import Enum


class ProviderType(Enum):
    """Enum for different AI CLI providers."""

    CLAUDE = "claude"
    GEMINI = "gemini"
    QWEN = "qwen"
