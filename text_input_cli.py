#!/usr/bin/env bash
""":"
exec "$(dirname "$0")/scripts/ami-run" "$(dirname "$0")/text_input_cli.py" "$@"
"""

"""
Simple in-line text input with borders that preserves terminal scrollability.
Ctrl+D (EOF) saves and exits. Line numbers shown. Enter adds newlines.
"""

import os
import sys
import datetime


def create_text_editor():
    """Create a text input that preserves terminal scrollability with line numbers."""
    # Print a blank line to ensure the editor appears below the command
    print()
    
    print("┌─────────────────────────────────────────────────────────────────────────────┐")
    print("│ Ctrl+D: save & exit | Enter: add new line | Line numbers shown              │")
    print("└─────────────────────────────────────────────────────────────────────────────┘")
    
    # Read from stdin with manual line processing to implement line numbers
    line_num = 1
    lines = []
    
    try:
        while True:
            # Read a line from stdin with line number
            try:
                user_input = input(f"{line_num:2d}| ")
                
                # Add the current line to our collection
                lines.append(user_input)
                
                # Increment line number for the next input
                line_num += 1
            except EOFError:
                # Ctrl+D was pressed
                break
            
    except KeyboardInterrupt:
        print('\n\nOperation cancelled by user.')
        return

    # Combine all lines
    content = "\n".join(lines)
    
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Generate timestamped filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{logs_dir}/text_input_{timestamp}.txt"
    
    # Save the content to the file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\nContent saved to {filename}")


def main():
    """Main function to run the text editor."""
    create_text_editor()


if __name__ == "__main__":
    main()