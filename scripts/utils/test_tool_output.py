#!/usr/bin/env bash
""":'
exec "$(dirname "$0")/../ami-run" "$0" "$@"
"""

from __future__ import annotations

"""Test how Claude Code Bash tool displays different output scenarios."""

import argparse
import sys


def test_stdout_only() -> None:
    """Test 1: Only stdout, exit 0."""
    sys.stdout.write("This is stdout output\n")
    sys.exit(0)


def test_stderr_only() -> None:
    """Test 2: Only stderr, exit 0."""
    sys.stderr.write("This is stderr output\n")
    sys.exit(0)


def test_both_streams() -> None:
    """Test 3: Both stdout and stderr, exit 0."""
    sys.stdout.write("This is stdout\n")
    sys.stderr.write("This is stderr\n")
    sys.exit(0)


def test_stdout_exit_1() -> None:
    """Test 4: Stdout with exit 1."""
    sys.stdout.write("This is stdout before error\n")
    sys.exit(1)


def test_stderr_exit_1() -> None:
    """Test 5: Stderr with exit 1."""
    sys.stderr.write("This is stderr before error\n")
    sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test Bash tool output display")
    parser.add_argument("test", choices=["stdout", "stderr", "both", "stdout-error", "stderr-error"])
    args = parser.parse_args()

    if args.test == "stdout":
        test_stdout_only()
    elif args.test == "stderr":
        test_stderr_only()
    elif args.test == "both":
        test_both_streams()
    elif args.test == "stdout-error":
        test_stdout_exit_1()
    elif args.test == "stderr-error":
        test_stderr_exit_1()


if __name__ == "__main__":
    main()
