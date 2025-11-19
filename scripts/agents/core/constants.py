"""Constants for AMI agents."""

# Common file exclusion patterns used across all executors
COMMON_EXCLUDE_PATTERNS = [
    "**/node_modules/**",
    "**/.git/**",
    "**/.venv/**",
    "**/venv/**",
    "**/__pycache__/**",
    "**/*.egg-info/**",
    "**/.cache/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/dist/**",
    "**/build/**",
]
