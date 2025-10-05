#!/usr/bin/env bash
# PreToolUse hook to block dangerous command patterns anywhere in the command

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

# Extract tool name - use the entire input to search for patterns
TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)

# Only check Bash commands
if [[ "$TOOL_NAME" != "Bash" ]]; then
    exit 0
fi

# For command checking, use the ENTIRE JSON input to catch patterns anywhere
COMMAND="$INPUT"

# Patterns that are always denied
DENY_PATTERNS=(
    'python3'
    'python[[:space:]]'
    'pip[[:space:]]+install'
    'pip3[[:space:]]+install'
    'pkill'
    'killall'
    '--no-verify'
    'no-verify'
    'pytest'
    'uv[[:space:]]+run'
    'noqa'
    'git[[:space:]]+revert'
    'git[[:space:]]+checkout'
)

# Patterns that require permission
ASK_PATTERNS=(
    '^git[[:space:]]'
    'rm[[:space:]]+-rf'
    'rm[[:space:]]+-fr'
)

# Check deny patterns first
for pattern in "${DENY_PATTERNS[@]}"; do
    if [[ "$COMMAND" =~ $pattern ]]; then
        cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Blocked: command contains forbidden pattern '$pattern'"
  }
}
EOF
        exit 0
    fi
done

# Check ask patterns
for pattern in "${ASK_PATTERNS[@]}"; do
    if [[ "$COMMAND" =~ $pattern ]]; then
        cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "Warning: command contains potentially dangerous pattern '$pattern'"
  }
}
EOF
        exit 0
    fi
done

# Allow command
exit 0
