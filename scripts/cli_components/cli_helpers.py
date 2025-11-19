#!/usr/bin/env python3
"""Helper functions for git repository server management CLI."""

import sys


def print_success(message: str) -> None:
    """Print success message."""
    sys.stdout.write(f"✓ {message}\n")


def print_info(message: str, indent: int = 0) -> None:
    """Print info message with optional indentation."""
    sys.stdout.write("  " * indent + message + "\n")


def print_error(message: str) -> None:
    """Print error message to stderr."""
    sys.stderr.write(f"✗ {message}\n")
