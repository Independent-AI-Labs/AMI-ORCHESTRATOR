#!/usr/bin/env bash
# Safe git commit wrapper - stages all changes before committing
# Usage: git_commit.sh [--fix] [--dry-run] <module-path> <commit-message>
#        git_commit.sh [--fix] [--dry-run] <module-path> -F <file>
#        git_commit.sh [--fix] [--dry-run] <module-path> --amend
#        git_commit.sh [--fix] [--dry-run] <module-path> --amend <commit-message>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Error: Module path required"
    echo "Usage: $0 [--fix] [--dry-run] <module-path> <commit-message>"
    echo "       $0 [--fix] [--dry-run] <module-path> -F <file>"
    echo "       $0 [--fix] [--dry-run] <module-path> --amend"
    echo "       $0 [--fix] [--dry-run] <module-path> --amend <commit-message>"
    echo ""
    echo "Options:"
    echo "  --fix       Run auto-fixes (ruff --fix --unsafe-fixes) before committing"
    echo "  --dry-run   Run all checks without creating commit"
    echo ""
    echo "Examples:"
    echo "  $0 . \"fix: update root\""
    echo "  $0 --fix . \"fix: update root with auto-fixes\""
    echo "  $0 --dry-run . \"test commit\""
    echo "  $0 . -F /tmp/commit_msg.txt"
    echo "  $0 . --amend"
    echo "  $0 . --amend \"fix: corrected message\""
    echo "  $0 clients/irisai/demo \"fix: add migrations\""
    exit 1
fi

# Parse flags
RUN_AUTOFIXES=false
DRY_RUN=false
while [[ "$1" == --* ]]; do
    case "$1" in
        --fix)
            RUN_AUTOFIXES=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Error: Unknown option: $1"
            exit 1
            ;;
    esac
done

MODULE_PATH="$1"
shift

# Parse commit message argument
USE_AMEND=false
AMEND_MESSAGE=""
if [ $# -eq 0 ]; then
    echo "Error: Commit message or --amend flag required"
    exit 1
elif [ "$1" = "--amend" ]; then
    USE_AMEND=true
    USE_FILE=false
    shift
    # Check if there's a message after --amend
    if [ $# -gt 0 ]; then
        AMEND_MESSAGE="$1"
    fi
elif [ "$1" = "-F" ]; then
    if [ $# -lt 2 ]; then
        echo "Error: -F flag requires file path"
        exit 1
    fi
    COMMIT_FILE="$2"
    if [ ! -f "$COMMIT_FILE" ]; then
        echo "Error: Commit message file does not exist: $COMMIT_FILE"
        exit 1
    fi
    USE_FILE=true
else
    COMMIT_MSG="$1"
    USE_FILE=false
fi

# Resolve to absolute path
if [ ! -d "$MODULE_PATH" ]; then
    echo "Error: Module path does not exist: $MODULE_PATH"
    exit 1
fi

MODULE_ROOT="$(cd "$MODULE_PATH" && pwd)"

# Determine if this is orchestrator root or submodule
if [ -f "$MODULE_ROOT/.git" ]; then
    # Submodule - find orchestrator root
    CURRENT_DIR="$MODULE_ROOT"
    while [ -f "$CURRENT_DIR/.git" ]; do
        CURRENT_DIR="$(cd "$CURRENT_DIR/.." && pwd)"
        if [ "$CURRENT_DIR" = "/" ]; then
            echo "Error: Could not find orchestrator root"
            exit 1
        fi
    done
    ORCHESTRATOR_ROOT="$CURRENT_DIR"
else
    # Orchestrator root
    ORCHESTRATOR_ROOT="$MODULE_ROOT"
fi

# Verify it's a git repository
if [ ! -e "$MODULE_ROOT/.git" ]; then
    echo "Error: Not a git repository: $MODULE_ROOT"
    echo "(.git directory or file not found)"
    exit 1
fi

# Run autofixes if requested
if [ "$RUN_AUTOFIXES" = true ]; then
    echo "Running auto-fixes..."
    cd "$MODULE_ROOT"

    # Determine ruff config based on module type
    if [ "$ORCHESTRATOR_ROOT" = "$MODULE_ROOT" ]; then
        # Orchestrator root - use root ruff.toml if exists, otherwise base/ruff.toml
        if [ -f "${ORCHESTRATOR_ROOT}/ruff.toml" ]; then
            RUFF_CONFIG="${ORCHESTRATOR_ROOT}/ruff.toml"
        else
            RUFF_CONFIG="${ORCHESTRATOR_ROOT}/base/ruff.toml"
        fi
    else
        # Submodule - use base/ruff.toml
        RUFF_CONFIG="${ORCHESTRATOR_ROOT}/base/ruff.toml"
    fi

    # Find nearest .venv by walking up from target directory - NO FALLBACKS
    find_venv_for_target() {
        local target_dir="${1:-$ORCHESTRATOR_ROOT}"
        local search_dir="$target_dir"

        # If target is a file, get its directory
        if [ -f "$target_dir" ]; then
            search_dir="$(dirname "$target_dir")"
        fi

        while [ "$search_dir" != "/" ]; do
            if [ -d "$search_dir/.venv" ]; then
                echo "$search_dir/.venv"
                return 0
            fi
            search_dir="$(dirname "$search_dir")"
        done

        return 1
    }

    # Find nearest .venv for the current context - NO FALLBACKS
    if ! NEAREST_VENV_DIR="$(find_venv_for_target "$MODULE_ROOT" 2>/dev/null)"; then
        echo "Error: No .venv found in hierarchy from $MODULE_ROOT to root" >&2
        exit 1
    fi

    RUFF_BIN="${NEAREST_VENV_DIR}/bin/ruff"

    if [ ! -f "$RUFF_BIN" ]; then
        echo "Error: ruff not found in nearest .venv at $RUFF_BIN"
        exit 1
    fi

    # Determine targets for autofixes (same as check targets to avoid touching submodules)
    if [ "$ORCHESTRATOR_ROOT" = "$MODULE_ROOT" ]; then
        AUTOFIX_TARGETS="backend scripts tests"
    else
        AUTOFIX_TARGETS="."
    fi

    echo "Running ruff format on $AUTOFIX_TARGETS..."
    "$RUFF_BIN" format --no-cache --config "$RUFF_CONFIG" --exclude ".gcloud" $AUTOFIX_TARGETS || true

    echo "Running ruff check --fix --unsafe-fixes on $AUTOFIX_TARGETS..."
    "$RUFF_BIN" check --no-cache --config "$RUFF_CONFIG" --fix --unsafe-fixes --exclude ".gcloud" $AUTOFIX_TARGETS || true

    echo "✓ Auto-fixes complete"

    # Re-stage after autofixes
    echo "Re-staging autofix changes..."
    cd "$MODULE_ROOT"
    git add -A
fi

echo "Staging all changes in ${MODULE_ROOT}..."
cd "$MODULE_ROOT"
git add -A

# Determine target directories early, before relative imports section
# IMPORTANT:
# - Autofixes (lines 148-158) target specific dirs to avoid modifying submodules
# - Quality checks skip submodules when committing from root (they're checked separately)
# - Submodules are independent repos checked when committed from their own directory
# - This avoids double-scanning and ruff relative path mismatches
IS_ROOT=false
if [ "$ORCHESTRATOR_ROOT" = "$MODULE_ROOT" ]; then
    IS_ROOT=true
    # Only check orchestrator-level directories, skip submodules
    CHECK_TARGETS="backend scripts tests"
    MODULE_ARG="root"
else
    CHECK_TARGETS="."  # Submodules check their own directory
    MODULE_ARG="$(realpath --relative-to="$ORCHESTRATOR_ROOT" "$MODULE_ROOT")"
fi

# Convert relative imports to absolute imports before quality checks
# Only run during actual commits (not during dry-run), and only with --fix flag
if [ "$DRY_RUN" = false ]; then
    if [ "$RUN_AUTOFIXES" = true ]; then
        echo ""
        echo "Converting relative imports to absolute imports..."

        # Define PYTHON_BIN for use in this section
        PYTHON_BIN="${ORCHESTRATOR_ROOT}/.venv/bin/python"
        if [ ! -f "$PYTHON_BIN" ]; then
            PYTHON_BIN="${MODULE_ROOT}/.venv/bin/python"
        fi
        if [ ! -f "$PYTHON_BIN" ]; then
            PYTHON_BIN="python3"
        fi

        FIX_RELATIVE_IMPORTS_SCRIPT="${ORCHESTRATOR_ROOT}/base/scripts/quality/fix_relative_imports.py"
        if [ -f "$FIX_RELATIVE_IMPORTS_SCRIPT" ]; then
            if ! "$PYTHON_BIN" "$FIX_RELATIVE_IMPORTS_SCRIPT" "$MODULE_ARG"; then
                echo "⚠ Relative imports fixer failed (non-critical)"
            else
                # Re-stage any changes made by the script
                git add -A
                echo "✓ Relative imports converted to absolute imports"
            fi
        else
            echo "ℹ Relative imports fixer not found, skipping"
        fi
    else
        # When --fix is not specified, inform user about relative imports but don't fix them
        echo ""
        echo "ℹ Relative imports check skipped (use --fix to convert relative imports to absolute)"
    fi
else
    echo ""
    echo "ℹ Skipping relative imports check during dry-run"
fi

# ============================================================================
# QUALITY CHECKS (run before commit)
# ============================================================================

# Determine target directories
# IMPORTANT:
# - Autofixes (lines 148-158) target specific dirs to avoid modifying submodules
# - Quality checks skip submodules when committing from root (they're checked separately)
# - Submodules are independent repos checked when committed from their own directory
# - This avoids double-scanning and ruff relative path mismatches
# Determine config paths
if [ "$IS_ROOT" = true ]; then
    if [ -f "${ORCHESTRATOR_ROOT}/ruff.toml" ]; then
        RUFF_CONFIG="${ORCHESTRATOR_ROOT}/ruff.toml"
    else
        RUFF_CONFIG="${ORCHESTRATOR_ROOT}/base/ruff.toml"
    fi
else
    RUFF_CONFIG="${ORCHESTRATOR_ROOT}/base/ruff.toml"
fi

RUFF_BIN="${ORCHESTRATOR_ROOT}/.venv/bin/ruff"
if [ ! -f "$RUFF_BIN" ]; then
    RUFF_BIN="${MODULE_ROOT}/.venv/bin/ruff"
fi

PYTHON_BIN="${ORCHESTRATOR_ROOT}/.venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="${MODULE_ROOT}/.venv/bin/python"
fi
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

echo ""
echo "========================================"
echo "Running quality checks..."
echo "========================================"

# Merge conflict markers
echo ""
echo "Checking for merge conflict markers..."
CONFLICT_FILES=$(git diff --cached --name-only --diff-filter=ACM | while read file; do
    if [ -f "$file" ] && grep -qE '^(<<<<<<<|=======|>>>>>>>) ' "$file"; then
        echo "$file"
    fi
done)
if [ -n "$CONFLICT_FILES" ]; then
    echo "✗ Merge conflict markers found:"
    echo "$CONFLICT_FILES"
    exit 1
fi
echo "✓ No merge conflicts"

# Max line check
echo ""
echo "Checking for files with too many lines..."
MAX_LINE_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' | while read file; do
    if [ -f "$file" ]; then
        # Check if it's a text file and count lines
        if file --mime-type "$file" 2>/dev/null | grep -q 'text/'; then
            LINE_COUNT=$(wc -l < "$file")
            if [ "$LINE_COUNT" -gt 512 ]; then
                echo "$file: $LINE_COUNT lines"
            fi
        fi
    fi
done)
if [ -n "$MAX_LINE_FILES" ]; then
    echo "✗ Files with more than 512 lines detected:"
    echo "$MAX_LINE_FILES"
    echo ""
    echo "Consider splitting large files into smaller modules."
    exit 1
fi
echo "✓ All files have reasonable line counts"

# Format check
echo ""
echo "Running format check..."
if ! "$RUFF_BIN" format --no-cache --check --config "$RUFF_CONFIG" --exclude ".gcloud" $CHECK_TARGETS; then
    echo "✗ Format check failed - files need formatting"
    echo "Run with --fix flag to auto-format"
    exit 1
fi
echo "✓ Format check passed"

# Lint check
echo ""
echo "Running lint check..."
if ! "$RUFF_BIN" check --no-cache --config "$RUFF_CONFIG" --exclude ".gcloud" $CHECK_TARGETS; then
    echo "✗ Lint check failed - violations detected"
    echo "Run with --fix flag to auto-fix"
    exit 1
fi
echo "✓ Lint check passed"

# Fix polyglot shebang formatting
FIX_SCRIPT="${ORCHESTRATOR_ROOT}/base/scripts/fix_polyglot_formatting.py"
if [ -f "$FIX_SCRIPT" ]; then
    echo ""
    echo "Fixing polyglot shebang formatting..."
    if ! "$PYTHON_BIN" "$FIX_SCRIPT"; then
        echo "⚠ Polyglot formatting fix failed (non-critical)"
    fi
    cd "$MODULE_ROOT"
    git add -A
    echo "✓ Polyglot formatting complete"
fi

# Shebang security check
echo ""
echo "Running shebang security check..."
AUDIT_SCRIPT="${ORCHESTRATOR_ROOT}/scripts/agents/validation/audit_shebangs.py"
if [ -f "$AUDIT_SCRIPT" ]; then
    if ! "$PYTHON_BIN" "$AUDIT_SCRIPT" --staged-only --directory "$MODULE_ROOT"; then
        echo "✗ Shebang security check failed"
        exit 1
    fi
    echo "✓ Shebang security check passed"
else
    echo "✗ BLOCKED: Shebang audit script not found"
    exit 1
fi

# Banned words
echo ""
echo "Running banned-words check..."
BANNED_WORDS_SCRIPT="${ORCHESTRATOR_ROOT}/base/scripts/quality/banned_words.py"
if [ -f "$BANNED_WORDS_SCRIPT" ]; then
    if ! "$PYTHON_BIN" "$BANNED_WORDS_SCRIPT" "$MODULE_ARG"; then
        echo "✗ Banned words check failed"
        exit 1
    fi
    echo "✓ Banned words check passed"
fi

# Config-based lint suppressions
echo ""
echo "Running config ignores check..."
CONFIG_IGNORES_SCRIPT="${ORCHESTRATOR_ROOT}/base/scripts/quality/check_config_ignores.py"
if [ -f "$CONFIG_IGNORES_SCRIPT" ]; then
    if ! "$PYTHON_BIN" "$CONFIG_IGNORES_SCRIPT" "$MODULE_ARG"; then
        echo "✗ Config ignores check failed"
        exit 1
    fi
    echo "✓ Config ignores check passed"
fi

# No lint suppressions
echo ""
echo "Running no-lint-suppressions check..."
CODE_CHECK_SCRIPT="${ORCHESTRATOR_ROOT}/base/scripts/quality/code_check.py"
if [ -f "$CODE_CHECK_SCRIPT" ]; then
    if ! "$PYTHON_BIN" "$CODE_CHECK_SCRIPT" "$MODULE_ARG"; then
        echo "✗ No-lint-suppressions check failed"
        exit 1
    fi
    echo "✓ No-lint-suppressions check passed"
fi

# Mypy
echo ""
echo "Running mypy..."
MYPY_CONFIG="${ORCHESTRATOR_ROOT}/base/scripts/mypy.ini"
if [ "$IS_ROOT" = true ]; then
    MYPY_TARGETS="backend scripts"
    if ! (cd "$ORCHESTRATOR_ROOT" && "$PYTHON_BIN" -m mypy $MYPY_TARGETS --config-file="$MYPY_CONFIG"); then
        echo "✗ Mypy check failed"
        exit 1
    fi
else
    if ! (cd "$ORCHESTRATOR_ROOT" && "$PYTHON_BIN" -m mypy "$MODULE_ARG" --config-file="$MYPY_CONFIG"); then
        echo "✗ Mypy check failed"
        exit 1
    fi
fi
echo "✓ Mypy check passed"

# YAML validation
echo ""
echo "Checking YAML files..."
YAML_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ya?ml)$' || true)
if [ -n "$YAML_FILES" ]; then
    for file in $YAML_FILES; do
        if ! python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            echo "✗ Invalid YAML: $file"
            exit 1
        fi
    done
    echo "✓ YAML files valid"
else
    echo "✓ No YAML files to check"
fi

# Large files check
echo ""
echo "Checking for large files..."
LARGE_FILES=$(git diff --cached --name-only --diff-filter=ACM | while read file; do
    if [ -f "$file" ]; then
        if stat -f%z "$file" >/dev/null 2>&1; then
            SIZE=$(stat -f%z "$file")
        elif stat -c%s "$file" >/dev/null 2>&1; then
            SIZE=$(stat -c%s "$file")
        else
            echo "✗ ERROR: Cannot stat file: $file" >&2
            exit 1
        fi
        if [ "$SIZE" -gt 52428800 ]; then
            echo "$file"
        fi
    fi
done)
if [ -n "$LARGE_FILES" ]; then
    echo "✗ Large files detected (>50MB):"
    echo "$LARGE_FILES"
    exit 1
fi
echo "✓ No large files"

# Debug statements
echo ""
echo "Checking for debug statements..."
PY_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)
if [ -n "$PY_FILES" ]; then
    DEBUG_FILES=$(echo "$PY_FILES" | while read file; do
        if [ -f "$file" ] && grep -qE '(^|[^a-zA-Z0-9_])(pdb|ipdb|pudb|debugpy|breakpoint)\.(set_trace|runcall)\(' "$file"; then
            echo "$file"
        fi
    done)
    if [ -n "$DEBUG_FILES" ]; then
        echo "✗ Debug statements found:"
        echo "$DEBUG_FILES"
        exit 1
    fi
    echo "✓ No debug statements"
else
    echo "✓ No Python files to check"
fi

# Commit message validation
echo ""
echo "Running commit message validation..."
if [ "$USE_FILE" = true ]; then
    # If using a file for the commit message, read from the file
    COMMIT_MSG_FOR_VALIDATION=$(cat "$COMMIT_FILE")
elif [ "$USE_AMEND" = true ]; then
    # If amending without a new message, we need to get the current commit message
    if [ -z "$AMEND_MESSAGE" ]; then
        COMMIT_MSG_FOR_VALIDATION=$(git log -1 --pretty=%B)
    else
        COMMIT_MSG_FOR_VALIDATION="$AMEND_MESSAGE"
    fi
else
    # Direct commit message
    COMMIT_MSG_FOR_VALIDATION="$COMMIT_MSG"
fi

# Load patterns from config file and check each one individually to show violations
PATTERNS_FILE="${ORCHESTRATOR_ROOT}/base/scripts/quality/commit_message_patterns.txt"
if [ -f "$PATTERNS_FILE" ]; then
    VIOLATIONS=()
    while IFS= read -r pattern; do
        # Skip empty lines and comments
        if [[ -n "$pattern" && ! "$pattern" =~ ^# ]]; then
            if echo "$COMMIT_MSG_FOR_VALIDATION" | grep -qiE "$pattern"; then
                VIOLATIONS+=("$pattern")
            fi
        fi
    done < "$PATTERNS_FILE"

    if [ ${#VIOLATIONS[@]} -gt 0 ]; then
        echo "✗ BLOCKED: Commit message contains banned patterns"
        echo ""
        echo "Violations detected:"
        for violation in "${VIOLATIONS[@]}"; do
            echo "  - Pattern: $violation"
            # Show the matching line in the commit message
            MATCHING_LINE=$(echo "$COMMIT_MSG_FOR_VALIDATION" | grep -iE "$violation" | head -1 | sed 's/^/    Line: /')
            echo "$MATCHING_LINE"
        done
        echo ""
        echo "Check $PATTERNS_FILE for list of banned patterns"
        echo ""
        echo "Please remove these patterns from your commit message."
        exit 1
    fi
    echo "✓ Commit message validation passed"
else
    echo "ℹ Commit message patterns file not found, skipping commit message validation"
fi

echo ""
echo "========================================"
echo "✓ All quality checks passed!"
echo "========================================"

if [ "$DRY_RUN" = true ]; then
    echo "✓ DRY RUN: Would create commit"
    exit 0
fi

echo "Creating commit..."
if [ "$USE_AMEND" = true ]; then
    if [ -n "$AMEND_MESSAGE" ]; then
        if ! git commit --amend -m "$AMEND_MESSAGE"; then
            echo "✗ Commit failed"
            exit 1
        fi
    else
        if ! git commit --amend --no-edit; then
            echo "✗ Commit failed"
            exit 1
        fi
    fi
elif [ "$USE_FILE" = true ]; then
    if ! git commit -F "$COMMIT_FILE"; then
        echo "✗ Commit failed"
        exit 1
    fi
else
    if ! git commit -m "$COMMIT_MSG"; then
        echo "✗ Commit failed"
        exit 1
    fi
fi

echo "✓ Commit created successfully"
