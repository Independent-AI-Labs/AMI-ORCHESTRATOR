#!/usr/bin/env bash
""":"
exec "$(dirname "$0")/scripts/ami-run" "$(dirname "$0")/text_input_cli.py" "$@"
"""

import sys
from typing import Any

from scripts.cli_components.text_editor import TextEditor

"""
Simple in-line text input with borders that preserves terminal scrollability.
Arrow keys for navigation, Ctrl+D to save and exit.
"""


def create_text_editor(initial_text: str = "") -> Any:
    """Create a text input that supports arrow key navigation."""
    editor = TextEditor(initial_text)
    return editor.run()


def main() -> None:
    """Main function to run the text editor."""
    # Accept command line arguments as initial text
    initial_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    create_text_editor(initial_text)


if __name__ == "__main__":
    main()
