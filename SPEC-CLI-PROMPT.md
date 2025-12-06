# CLI Prompt Component Specification

## Overview
A minimal, non-intrusive text input component for the terminal that maintains shell scrollability while providing a clean editing interface.

## Requirements

### 1. Non-Fullscreen Behavior
- The CLI prompt should not take over the entire terminal screen
- Should not clear existing shell contents
- Should not clear the terminal when launched
- Should operate in a localized area of the terminal

### 2. Visual Components

#### 2.1 Bordered Information Line
- Shows keyboard shortcuts in a bordered header
- Uses top and bottom borders with content in between (┌─...─┐, content, └─...─┘)
- Short, concise information about available shortcuts
- Should be minimal and not take up excessive space
- Example: `┌ Arrow Keys: navigate | Enter: new line | BS: edit | Ctrl+S: send ┐`

#### 2.2 Expandable Text Editor
- Line-numbered text editor area with optional navigation indicators
- Display ALL input lines at all times to maintain terminal scrollability
- As user types, the editor expands to accommodate more content
- Each line has format: `{indicator}{line_number}| {line_content}` where indicator shows current line
- Display all lines simultaneously - THE TERMINAL NEEDS TO REMAIN SCROLLABLE NOT IMPLEMENT SCROLL IN THE EDITOR

#### 2.3 Cursor Position Indicator
- Current character position should be highlighted with inverted colors
- Use black text on white background rectangle for the character at cursor position
- Cursor should be precisely positioned using ANSI escape codes

### 3. Post-Close Display
When the user exits the prompt (save or cancel), the terminal should display:

#### 3.1 Opening Border
- Horizontal border at the top of the saved content (┌─...─┐)

#### 3.2 Saved Text Content
- The text that was entered, with line numbers
- Format: `   {line_number}| {line_content}` (three spaces for border)

#### 3.3 Closing Border
- Horizontal border at the bottom (└─...─┘)

#### 3.4 Timestamp and Status
- Timestamp in the format: `HH:MM:SS` (24-hour format)
- Status indicator with emoji:
  - ✅ Sent to agent (when Ctrl+S pressed)
  - ❌ Message discarded (when Ctrl+C pressed)

## Implementation Notes

### ANSI Escape Sequences
- Use `\033[7m` for inverted (reverse) video (black on white)
- Use `\033[0m` to reset formatting
- Use `\033[{row};{col}H` for precise cursor positioning
- Use `\033[s` and `\033[u` for save/restore cursor position
- Use `\033[2K` to clear entire line
- Use `\033[1G` to move cursor to beginning of line

### Terminal Size Handling
- Use `shutil.get_terminal_size()` to get terminal dimensions
- Respect terminal width when drawing borders
- Only redraw the minimum necessary lines to prevent flicker

### Key Bindings
- Arrow keys (↑↓←→): Navigate between characters/lines
- Enter: Start new line
- Backspace: Delete character before cursor
- Ctrl+S: Send to agent and exit
- Ctrl+C: Cancel and exit
- Ctrl+W: Delete word (optional)
- Ctrl+U: Delete line (optional)

### Behavior Requirements
- The editor should only take up the minimal vertical space required
- Should not scroll the terminal unless content exceeds visible area
- Should maintain scrollback buffer integrity
- Should not interfere with shell command history
- Should not affect other shell operations