#!/usr/bin/env bash
# Debug script for ami-agent --tasks mode
# Shows detailed execution flow, hook configuration, and Claude Code commands

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

section() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

info() {
    echo -e "${BLUE}$1${NC}"
}

value() {
    echo -e "${CYAN}$1${NC}"
}

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <task_file.md>"
    echo ""
    echo "Debug a single task execution with full logging."
    exit 1
fi

TASK_FILE="$1"
if [[ ! -f "$TASK_FILE" ]]; then
    echo "Error: Task file not found: $TASK_FILE"
    exit 1
fi

TASK_NAME=$(basename "$TASK_FILE" .md)
TASK_DIR=$(dirname "$TASK_FILE")

section "Task Information"
info "Task file: $(value "$TASK_FILE")"
info "Task name: $(value "$TASK_NAME")"
info "Task directory: $(value "$TASK_DIR")"
echo ""
info "Task content:"
cat "$TASK_FILE"

section "Hook Configuration"
HOOKS_FILE="$ROOT_DIR/scripts/config/hooks.yaml"
if [[ -f "$HOOKS_FILE" ]]; then
    info "Hooks file: $(value "$HOOKS_FILE")"
    value "$(cat "$HOOKS_FILE")"
else
    info "Hooks file NOT FOUND: $HOOKS_FILE"
fi

section "Agent Configuration"
CONFIG_FILE="$ROOT_DIR/scripts/config/automation.yaml"
if [[ -f "$CONFIG_FILE" ]]; then
    info "Automation config: $(value "$CONFIG_FILE")"
    info "Task settings:"
    value "$(grep -A 20 '^tasks:' "$CONFIG_FILE" || echo 'tasks section not found')"
else
    info "Config file NOT FOUND: $CONFIG_FILE"
fi

section "Running Task with Debug Logging"
info "Executing: $(value "scripts/ami-agent --tasks '$TASK_DIR' --root-dir '$TASK_DIR'")"
echo ""

# Tail logs in background
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
LATEST_LOG=$(find "$LOG_DIR" -name "automation-*.jsonl" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2)

if [[ -n "$LATEST_LOG" ]]; then
    info "Tailing log file: $(value "$LATEST_LOG")"
    # Tail in background, kill on script exit
    tail -f "$LATEST_LOG" &
    TAIL_PID=$!
    trap "kill $TAIL_PID 2>/dev/null || true" EXIT
else
    info "No existing log file found, new one will be created"
fi

echo ""
section "Task Execution Output"

# Run the task
set +e
"$ROOT_DIR/scripts/ami-agent" --tasks "$TASK_DIR" --root-dir "$TASK_DIR"
EXIT_CODE=$?
set -e

echo ""
section "Execution Results"
info "Exit code: $(value "$EXIT_CODE")"

# Check for progress file
PROGRESS_FILE=$(find "$TASK_DIR" -name "progress-*-${TASK_NAME}.md" -type f | head -1)
if [[ -f "$PROGRESS_FILE" ]]; then
    info "Progress file: $(value "$PROGRESS_FILE")"
    echo ""
    value "$(cat "$PROGRESS_FILE")"
else
    info "No progress file created"
fi

# Check for feedback file
FEEDBACK_FILE=$(find "$TASK_DIR" -name "feedback-*-${TASK_NAME}.md" -type f | head -1)
if [[ -f "$FEEDBACK_FILE" ]]; then
    info "Feedback file: $(value "$FEEDBACK_FILE")"
    echo ""
    value "$(cat "$FEEDBACK_FILE")"
fi

section "Recent Log Entries"
if [[ -n "$LATEST_LOG" && -f "$LATEST_LOG" ]]; then
    info "Last 20 log entries:"
    tail -20 "$LATEST_LOG" | while IFS= read -r line; do
        # Pretty-print JSON logs
        if command -v jq &> /dev/null; then
            echo "$line" | jq -C '.'
        else
            echo "$line"
        fi
    done
fi

section "Debug Summary"
info "Task: $(value "$TASK_NAME")"
info "Exit code: $(value "$EXIT_CODE")"
if [[ $EXIT_CODE -eq 0 ]]; then
    info "Status: $(value 'SUCCESS ✓')"
else
    info "Status: $(value 'FAILED ✗')"
fi

exit $EXIT_CODE
