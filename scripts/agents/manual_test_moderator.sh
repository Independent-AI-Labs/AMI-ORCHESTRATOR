#!/usr/bin/env bash
# Manual end-to-end testing for completion moderator functionality

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== Completion Moderator Manual Testing ==="
echo "Root: $ROOT_DIR"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass_count=0
fail_count=0

log_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((pass_count++))
}

log_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((fail_count++))
}

log_info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

# Test 1: Verify transcript utilities exist
echo "Test 1: Verify transcript.py exists and has required functions"
if [[ -f "$ROOT_DIR/scripts/automation/transcript.py" ]]; then
    if grep -q "def get_last_n_messages" "$ROOT_DIR/scripts/automation/transcript.py" && \
       grep -q "def get_messages_until_last_user" "$ROOT_DIR/scripts/automation/transcript.py" && \
       grep -q "def format_messages_for_prompt" "$ROOT_DIR/scripts/automation/transcript.py"; then
        log_pass "transcript.py exists with all required functions"
    else
        log_fail "transcript.py missing required functions"
    fi
else
    log_fail "transcript.py not found"
fi
echo ""

# Test 2: Verify moderator prompt exists
echo "Test 2: Verify completion_moderator.txt prompt exists"
if [[ -f "$ROOT_DIR/scripts/config/prompts/completion_moderator.txt" ]]; then
    if grep -q "ALLOW" "$ROOT_DIR/scripts/config/prompts/completion_moderator.txt" && \
       grep -q "BLOCK" "$ROOT_DIR/scripts/config/prompts/completion_moderator.txt"; then
        log_pass "completion_moderator.txt exists with ALLOW/BLOCK format"
    else
        log_fail "completion_moderator.txt missing ALLOW/BLOCK format"
    fi
else
    log_fail "completion_moderator.txt not found"
fi
echo ""

# Test 3: Verify agent config preset exists
echo "Test 3: Verify completion_moderator() preset in AgentConfigPresets"
if grep -q "def completion_moderator" "$ROOT_DIR/scripts/automation/agent_cli.py"; then
    if grep -A 5 "def completion_moderator" "$ROOT_DIR/scripts/automation/agent_cli.py" | grep -q "enable_hooks=False"; then
        log_pass "completion_moderator() preset exists with enable_hooks=False"
    else
        log_fail "completion_moderator() preset has incorrect enable_hooks setting"
    fi
else
    log_fail "completion_moderator() preset not found in agent_cli.py"
fi
echo ""

# Test 4: Verify ResponseScanner integration
echo "Test 4: Verify ResponseScanner has _validate_completion() method"
if grep -q "def _validate_completion" "$ROOT_DIR/scripts/automation/hooks.py"; then
    log_pass "_validate_completion() method exists in ResponseScanner"
else
    log_fail "_validate_completion() method not found"
fi
echo ""

# Test 5: Verify bash hooks fix
echo "Test 5: Verify bash hooks ALWAYS enabled via _create_bash_only_hooks_file()"
if grep -q "def _create_bash_only_hooks_file" "$ROOT_DIR/scripts/automation/agent_cli.py"; then
    if grep -q "SECURITY: Bash command guard ALWAYS enabled" "$ROOT_DIR/scripts/automation/agent_cli.py"; then
        log_pass "_create_bash_only_hooks_file() exists with security comment"
    else
        log_fail "_create_bash_only_hooks_file() missing security documentation"
    fi
else
    log_fail "_create_bash_only_hooks_file() not found"
fi
echo ""

# Test 6: Verify configuration
echo "Test 6: Verify automation.yaml has completion moderator config"
if grep -q "completion_moderator:" "$ROOT_DIR/scripts/config/automation.yaml"; then
    if grep -q "completion_moderator_enabled: true" "$ROOT_DIR/scripts/config/automation.yaml"; then
        log_pass "automation.yaml has completion_moderator configuration"
    else
        log_fail "automation.yaml missing completion_moderator_enabled setting"
    fi
else
    log_fail "automation.yaml missing completion_moderator prompt path"
fi
echo ""

# Test 7: Check if hooks.yaml has bash guard
echo "Test 7: Verify hooks.yaml contains bash command guard"
if grep -q "matcher: \"Bash\"" "$ROOT_DIR/scripts/config/hooks.yaml" || \
   grep -q 'matcher: Bash' "$ROOT_DIR/scripts/config/hooks.yaml"; then
    if grep -q "command: \"command-guard\"" "$ROOT_DIR/scripts/config/hooks.yaml" || \
       grep -q 'command: command-guard' "$ROOT_DIR/scripts/config/hooks.yaml"; then
        log_pass "hooks.yaml contains bash command guard"
    else
        log_fail "hooks.yaml missing command-guard command"
    fi
else
    log_fail "hooks.yaml missing Bash matcher"
fi
echo ""

# Test 8: Python import test
echo "Test 8: Test Python imports"
cd "$ROOT_DIR"
if python3 -c "from scripts.automation.transcript import get_last_n_messages, get_messages_until_last_user, format_messages_for_prompt" 2>/dev/null; then
    log_pass "Transcript utilities can be imported"
else
    log_fail "Failed to import transcript utilities"
fi
echo ""

# Test 9: Verify test files exist
echo "Test 9: Verify test files exist"
test_files_exist=0
if [[ -f "$ROOT_DIR/scripts/automation/tests/test_transcript.py" ]]; then
    ((test_files_exist++))
fi
if [[ -f "$ROOT_DIR/scripts/automation/tests/test_completion_moderator.py" ]]; then
    ((test_files_exist++))
fi
if [[ -f "$ROOT_DIR/scripts/automation/tests/test_bash_hooks.py" ]]; then
    ((test_files_exist++))
fi

if [[ $test_files_exist -eq 3 ]]; then
    log_pass "All 3 test files exist"
else
    log_fail "Missing test files ($test_files_exist/3 found)"
fi
echo ""

# Test 10: Check for completion markers in ResponseScanner
echo "Test 10: Verify COMPLETION_MARKERS includes WORK DONE and FEEDBACK:"
if grep -q 'COMPLETION_MARKERS = \["WORK DONE", "FEEDBACK:"\]' "$ROOT_DIR/scripts/automation/hooks.py"; then
    log_pass "COMPLETION_MARKERS correctly defined"
else
    log_fail "COMPLETION_MARKERS not found or incorrect"
fi
echo ""

# Summary
echo "======================================"
echo "Test Summary:"
echo -e "${GREEN}Passed: $pass_count${NC}"
echo -e "${RED}Failed: $fail_count${NC}"
echo "======================================"

if [[ $fail_count -eq 0 ]]; then
    echo -e "${GREEN}All manual checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed. Please review.${NC}"
    exit 1
fi
