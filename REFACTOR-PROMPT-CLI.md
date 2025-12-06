# CLI Refactoring Prompt

## Overview
This document outlines the critical issues and refactoring requirements for the CLI components in the AMI Orchestrator project. The main focus areas are security improvements, code simplification, and architecture improvements.

## Issue 1: Command Injection Vulnerability in text_input_cli.py

### Problem
The `text_input_cli.py` file contains a potential command injection vulnerability in the main function:

```python
def main() -> None:
    """Main function to run the text editor."""
    # Accept command line arguments as initial text
    initial_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    create_text_editor(initial_text)
```

The current implementation concatenates all command-line arguments without proper validation or sanitization, which could potentially allow malicious input to be processed.

### Risk
- Command injection through specially crafted command line arguments
- Potential execution of unintended operations if arguments contain special shell characters

### Solution Required
- Implement proper input validation and sanitization
- Use a safer method to join arguments that doesn't concatenate arguments that could contain special characters
- Add input validation to ensure only valid text is accepted as initial content

## Issue 2: Complex Terminal Sequence Handling in text_input_utils.py

### Problem
The `text_input_utils.py` file contains complex nested functions for terminal sequence handling:
- `_handle_escape_sequence()`
- `_handle_ansi_sequence()`
- `_handle_ctrl_arrow_sequence()`
- `_handle_control_characters()`
- `read_key_sequence()`

These functions have deeply nested conditionals and complex logic that makes them hard to maintain and debug.

### Risk
- Difficult to debug terminal input handling issues
- Potential for security vulnerabilities in input processing
- High maintenance burden

### Solution Required
- Simplify the nested conditional logic
- Extract complex functions into clear, well-defined modules
- Add comprehensive tests for all key sequence handling
- Add proper input validation and sanitization

### Current Complex Code Structure
```python
def read_key_sequence() -> str | int | None:
    """Read potential multi-character key sequences like arrow keys."""
    ch1, ord1 = get_char_with_ordinals()

    # Check if this is an escape sequence (like arrow keys)
    if ord1 == ESC:  # ESC character
        result = _handle_escape_sequence()
        if result == "ESC_NOT_HANDLED":
            return ch1  # Return original ESC character
        return result

    # Handle control characters
    control_result = _handle_control_characters(ord1)
    if control_result is not None:
        return control_result

    # Handle printable characters
    if PRINTABLE_MIN <= ord1 <= PRINTABLE_MAX:  # Printable ASCII characters
        return ch1

    # Filter out other control characters to prevent them from appearing in content
    # Control characters are typically 0-31 and 127, we've already handled the useful ones
    # So we'll return a special code for unhandled control characters to skip them
    if 0 <= ord1 <= CONTROL_MAX and ord1 not in [CTRL_C, TAB, ENTER_LF, ENTER_CR, CTRL_S, CTRL_U, CTRL_W, ESC]:  # Skip handled control chars
        return None  # Skip unhandled control characters
    return ch1
```

## Issue 3: Insufficient Input Validation in read_key_sequence()

### Problem
The `read_key_sequence()` function handles raw terminal input without sufficient validation. While it handles various key sequences, it could potentially be exploited with crafted terminal escape sequences or invalid character codes.

### Risk
- Terminal escape sequence attacks
- Potential for buffer overflow or invalid memory access
- Unexpected behavior from invalid character codes

### Solution Required
- Add input validation for character codes
- Sanitize and validate all escape sequences
- Implement proper bounds checking
- Add logging for unexpected character sequences

## Issue 4: Tight Coupling Between CLI Components

### Problem
Multiple CLI components show tight coupling:
- `TextEditor` class in `text_editor.py` directly depends on `EditorDisplay`, `save_content`, and `read_key_sequence`
- The display, input handling, and saving logic are all tightly integrated
- No clear separation of concerns between input, processing, and output

### Risk
- High maintenance burden due to interdependencies
- Difficult to unit test individual components
- Difficult to extend or modify functionality without affecting other parts
- Hard to implement alternative implementations

### Solution Required
- Implement proper separation of concerns
- Apply dependency injection to reduce coupling
- Create clear interfaces between components
- Apply SOLID principles (especially Single Responsibility and Dependency Inversion)

### Current Tightly Coupled Structure
```python
class TextEditor:
    def __init__(self, initial_text: str = "") -> None:
        self.lines: list[str] = initial_text.split("\n") if initial_text else [""]
        self.cursor_manager = CursorManager(self.lines)  # Tight coupling

    def run(self) -> str | Any | None:
        display = EditorDisplay()  # Direct instantiation, tight coupling
        # ... 
        key = read_key_sequence()  # Direct function call
        # ...
        return save_content(self.lines, display.previous_display_lines)  # Direct call
```

## Issue 5: Polyglot Script Security Issues

### Problem
Multiple CLI scripts use a complex polyglot shebang pattern that redirects execution:

```bash
#!/usr/bin/env bash
""":"
exec "$(dirname "$0")/scripts/ami-run" "$(dirname "$0")/text_input_cli.py" "$@"
"""
```

This adds an unnecessary execution layer that could introduce security risks.

### Risk
- Additional attack surface through the redirection mechanism
- Potential for path manipulation if ami-run is compromised
- Complexity increases likelihood of security vulnerabilities

### Solution Required
- Either use simple Python shebangs for Python files or simple bash shebangs for shell scripts
- Remove the complex redirection pattern where possible
- If the ami-run wrapper is necessary, ensure it properly validates all inputs

## Recommended Architecture Improvements

### 1. Input Validation Layer
Create a dedicated input validation module that handles all user input sanitization:

```python
class InputValidator:
    @staticmethod
    def validate_command_line_args(args: list[str]) -> str:
        # Sanitize and validate command line input
        pass

    @staticmethod
    def validate_terminal_input(input_sequence: str) -> str:
        # Validate and sanitize terminal input
        pass
```

### 2. Interface-Based Design
Use interfaces to reduce coupling:

```python
from abc import ABC, abstractmethod

class DisplayInterface(ABC):
    @abstractmethod
    def display_editor(self, lines: list[str], current_line: int, current_col: int) -> None:
        pass

class InputHandlerInterface(ABC):
    @abstractmethod
    def read_key_sequence(self) -> str | int | None:
        pass
```

### 3. Security-Focused Terminal Input Handler
Replace the complex terminal sequence handling with a more secure, validated approach:

```python
class SecureTerminalInputHandler:
    def __init__(self):
        self.allowed_sequences = self._get_allowed_sequences()
    
    def read_key_sequence(self) -> str | None:
        # Secure, validated input handling
        pass
    
    def _validate_sequence(self, sequence: str) -> bool:
        # Proper validation of sequences
        pass
```

## Implementation Priority

1. **High Priority**: Fix the command injection vulnerability in `text_input_cli.py`
2. **High Priority**: Implement proper input validation in `read_key_sequence()`
3. **Medium Priority**: Apply interface-based design to reduce coupling
4. **Medium Priority**: Simplify the terminal sequence handling logic
5. **Low Priority**: Evaluate and potentially remove polyglot script patterns

## Testing Requirements

Each refactoring should include:
- Unit tests for all input validation functions
- Integration tests for the new interface-based components
- Security testing for input handling
- Terminal sequence testing with various edge cases