#!/bin/bash
set -euo pipefail

# Dynamically determine the script's directory and set ROOT_DIR relative to it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DRY_RUN=false

show_usage() {
    cat << EOF
Usage: sudo $0 <command> [path] [--dry-run]

Toggle immutable protection for source code files and config files across the repository.
Uses chattr +i (immutable flag) to prevent ANY modification, even by root.

Commands:
  lock [path]     - Lock all files, or specific file/directory if path provided
  unlock [path]   - Unlock all files, or specific file/directory if path provided
  lock-file PATH  - Lock a single file or all files in a directory (explicit)
  unlock-file PATH- Unlock a single file or all files in a directory (explicit)
  status          - Show current protection status
  test            - Run dry-run test without root (shows what would happen)

Options:
  --dry-run - Simulate operations without actually modifying files (no root required)

Protected files:
  - Source files in /scripts and /base/scripts: .py, .sh, .yaml, .yml, .json, .toml, .ini, .cfg, .md
  - Config files across entire repo: pyproject.toml, ruff.toml, mypy.ini, pytest.ini
  - Git hooks: All files in .git/hooks/ directories (prevents hook tampering)

Examples:
  sudo $0 lock                              # Lock all source and config files
  sudo $0 unlock                            # Unlock all source and config files
  sudo $0 lock scripts/README.md            # Lock single file (simple syntax)
  sudo $0 unlock scripts/README.md          # Unlock single file (simple syntax)
  sudo $0 lock scripts/                     # Lock entire directory
  sudo $0 unlock base/scripts/              # Unlock entire directory
  sudo $0 lock scripts/ami-agent --dry-run  # Test without changes

Requires root privileges to modify immutable flags (except in dry-run mode).
EOF
}

check_root() {
    if [[ $DRY_RUN == true ]]; then
        return 0  # Skip root check in dry-run mode
    fi
    if [[ $EUID -ne 0 ]]; then
        echo "ERROR: This script must be run as root (use sudo)" >&2
        echo "       Or use --dry-run flag to test without root" >&2
        exit 1
    fi
}

get_status() {
    local test_file="$ROOT_DIR/scripts/toggle_root_protection.sh"
    if lsattr "$test_file" 2>/dev/null | grep -q "^....i"; then
        echo "LOCKED (immutable)"
        return 0
    else
        echo "UNLOCKED (mutable)"
        return 1
    fi
}

lock_files() {
    if [[ $DRY_RUN == true ]]; then
        echo "[DRY RUN] Would lock source code files in: $ROOT_DIR/scripts and $ROOT_DIR/base/scripts"
        echo "[DRY RUN] Would lock config files across entire repo"
        echo "[DRY RUN] Would set immutable flag (chattr +i)..."
    else
        echo "Locking source code files in: $ROOT_DIR/scripts and $ROOT_DIR/base/scripts"
        echo "Locking config files across entire repo"
        echo "Setting immutable flag (chattr +i)..."
    fi

    # Build array of files to lock
    echo "Building file list..."
    local files=()
    # Use mapfile/readarray to avoid process substitution deadlock
    mapfile -d '' files < <(find "$ROOT_DIR/scripts" "$ROOT_DIR/base/scripts" -type f \( \
        -name "*.py" -o \
        -name "*.sh" -o \
        -name "*.yaml" -o \
        -name "*.yml" -o \
        -name "*.json" -o \
        -name "*.toml" -o \
        -name "*.ini" -o \
        -name "*.cfg" -o \
        -name "*.md" \
    \) -print0)

    # Also find config files across entire repo (excluding build/cache dirs)
    local config_files=()
    mapfile -d '' config_files < <(find "$ROOT_DIR" \
        \( -path "*/.venv*" -o -path "*/node_modules" -o -path "*/.git" -o -path "*/__pycache__" -o -path "*/.cache" -o -path "*/.pytest_cache" -o -path "*/.mypy_cache" -o -path "*/.ruff_cache" -o -path "*/build" -o -path "*/dist" -o -path "*/chromium*" -o -path "*/.gcloud" \) -prune -o \
        -type f \( -name "pyproject.toml" -o -name "ruff.toml" -o -name "mypy.ini" -o -name "pytest.ini" \) -print0)
    files+=("${config_files[@]}")

    # Also find git hooks across entire repo (prevents hook tampering)
    local git_hook_files=()
    mapfile -d '' git_hook_files < <(find "$ROOT_DIR" \
        -path "*/.git/hooks/*" -type f -print0)
    files+=("${git_hook_files[@]}")

    echo "Found ${#files[@]} files to lock"

    if [[ ${#files[@]} -eq 0 ]]; then
        echo "ERROR: No files found to lock!" >&2
        exit 1
    fi

    # Lock each file with progress
    local count=0
    local failed=0
    for file in "${files[@]}"; do
        if [[ $DRY_RUN == true ]]; then
            ((count++)) || true
            # Show progress every 50 files in dry-run
            if (( count % 50 == 0 )) || [[ $count -eq 1 ]]; then
                echo "[DRY RUN] Processing $count/${#files[@]} files..."
            fi
        else
            if chattr +i "$file" 2>&1; then
                ((count++)) || true
                # Show progress every 50 files
                if (( count % 50 == 0 )) || [[ $count -eq 1 ]]; then
                    echo "Locked $count/${#files[@]} files..."
                fi
            else
                echo "WARNING: Failed to lock $file" >&2
                ((failed++)) || true
            fi
        fi
    done

    echo ""
    if [[ $DRY_RUN == true ]]; then
        echo "[DRY RUN] Would lock $count source code files"
        echo "[DRY RUN] Test completed successfully"
    else
        echo "✓ $count source code files are now IMMUTABLE"
        if (( failed > 0 )); then
            echo "✗ $failed files failed to lock"
            exit 1
        fi
        echo "✓ Cannot be modified even with chmod or sudo"
        echo "✓ Must run 'sudo $0 unlock' before making changes"
    fi
}

unlock_files() {
    if [[ $DRY_RUN == true ]]; then
        echo "[DRY RUN] Would unlock source code files in: $ROOT_DIR/scripts and $ROOT_DIR/base/scripts"
        echo "[DRY RUN] Would unlock config files across entire repo"
        echo "[DRY RUN] Would remove immutable flag (chattr -i)..."
    else
        echo "Unlocking source code files in: $ROOT_DIR/scripts and $ROOT_DIR/base/scripts"
        echo "Unlocking config files across entire repo"
        echo "Removing immutable flag (chattr -i)..."
    fi

    # Build array of files to unlock
    echo "Building file list..."
    local files=()
    # Use mapfile/readarray to avoid process substitution deadlock
    mapfile -d '' files < <(find "$ROOT_DIR/scripts" "$ROOT_DIR/base/scripts" -type f \( \
        -name "*.py" -o \
        -name "*.sh" -o \
        -name "*.yaml" -o \
        -name "*.yml" -o \
        -name "*.json" -o \
        -name "*.toml" -o \
        -name "*.ini" -o \
        -name "*.cfg" -o \
        -name "*.md" \
    \) -print0)

    # Also find config files across entire repo (excluding build/cache dirs)
    local config_files=()
    mapfile -d '' config_files < <(find "$ROOT_DIR" \
        \( -path "*/.venv*" -o -path "*/node_modules" -o -path "*/.git" -o -path "*/__pycache__" -o -path "*/.cache" -o -path "*/.pytest_cache" -o -path "*/.mypy_cache" -o -path "*/.ruff_cache" -o -path "*/build" -o -path "*/dist" -o -path "*/chromium*" -o -path "*/.gcloud" \) -prune -o \
        -type f \( -name "pyproject.toml" -o -name "ruff.toml" -o -name "mypy.ini" -o -name "pytest.ini" \) -print0)
    files+=("${config_files[@]}")

    # Also find git hooks across entire repo (prevents hook tampering)
    local git_hook_files=()
    mapfile -d '' git_hook_files < <(find "$ROOT_DIR" \
        -path "*/.git/hooks/*" -type f -print0)
    files+=("${git_hook_files[@]}")

    echo "Found ${#files[@]} files to unlock"

    if [[ ${#files[@]} -eq 0 ]]; then
        echo "ERROR: No files found to unlock!" >&2
        exit 1
    fi

    # Unlock each file with progress
    local count=0
    local failed=0
    for file in "${files[@]}"; do
        if [[ $DRY_RUN == true ]]; then
            ((count++)) || true
            # Show progress every 50 files in dry-run
            if (( count % 50 == 0 )) || [[ $count -eq 1 ]]; then
                echo "[DRY RUN] Processing $count/${#files[@]} files..."
            fi
        else
            if chattr -i "$file" 2>&1; then
                ((count++)) || true
                # Show progress every 50 files
                if (( count % 50 == 0 )) || [[ $count -eq 1 ]]; then
                    echo "Unlocked $count/${#files[@]} files..."
                fi
            else
                echo "WARNING: Failed to unlock $file" >&2
                ((failed++)) || true
            fi
        fi
    done

    echo ""

    # Restore write permissions
    if [[ $DRY_RUN == true ]]; then
        echo "[DRY RUN] Would restore write permissions..."
        echo "[DRY RUN] Would unlock $count source code files"
        echo "[DRY RUN] Test completed successfully"
    else
        echo "Restoring write permissions..."
        find "$ROOT_DIR/scripts" "$ROOT_DIR/base/scripts" -type f \( \
            -name "*.py" -o \
            -name "*.sh" -o \
            -name "*.yaml" -o \
            -name "*.yml" -o \
            -name "*.json" -o \
            -name "*.toml" -o \
            -name "*.ini" -o \
            -name "*.cfg" -o \
            -name "*.md" \
        \) -exec chmod u+w {} +
        # Also restore permissions on config files
        find "$ROOT_DIR" \
            \( -path "*/.venv*" -o -path "*/node_modules" -o -path "*/.git" -o -path "*/__pycache__" -o -path "*/.cache" -o -path "*/.pytest_cache" -o -path "*/.mypy_cache" -o -path "*/.ruff_cache" -o -path "*/build" -o -path "*/dist" -o -path "*/chromium*" -o -path "*/.gcloud" \) -prune -o \
            -type f \( -name "pyproject.toml" -o -name "ruff.toml" -o -name "mypy.ini" -o -name "pytest.ini" \) -print -exec chmod u+w {} +
        # Also restore permissions on git hooks
        find "$ROOT_DIR" \
            -path "*/.git/hooks/*" -type f -exec chmod u+w {} +

        echo "✓ $count source code files are now MUTABLE"
        if (( failed > 0 )); then
            echo "✗ $failed files failed to unlock"
            exit 1
        fi
        echo "✓ Files can be modified normally"
    fi
}

lock_single() {
    local target_path="$1"

    # Convert to absolute path if relative
    if [[ ! "$target_path" = /* ]]; then
        target_path="$ROOT_DIR/$target_path"
    fi

    # Validate path exists
    if [[ ! -e "$target_path" ]]; then
        echo "ERROR: Path not found: $target_path" >&2
        exit 1
    fi

    if [[ $DRY_RUN == true ]]; then
        echo "[DRY RUN] Would lock: $target_path"
        echo "[DRY RUN] Would set immutable flag (chattr +i)..."
    else
        echo "Locking: $target_path"
        echo "Setting immutable flag (chattr +i)..."
    fi

    # Build array of files to lock
    local files=()
    if [[ -f "$target_path" ]]; then
        # Single file
        files=("$target_path")
    elif [[ -d "$target_path" ]]; then
        # Directory - find all matching files
        mapfile -d '' files < <(find "$target_path" -type f \( \
            -name "*.py" -o \
            -name "*.sh" -o \
            -name "*.yaml" -o \
            -name "*.yml" -o \
            -name "*.json" -o \
            -name "*.toml" -o \
            -name "*.ini" -o \
            -name "*.cfg" -o \
            -name "*.md" -o \
            -name "pyproject.toml" -o \
            -name "ruff.toml" -o \
            -name "mypy.ini" -o \
            -name "pytest.ini" \
        \) -print0)
    fi

    if [[ ${#files[@]} -eq 0 ]]; then
        echo "ERROR: No matching source files found" >&2
        exit 1
    fi

    echo "Found ${#files[@]} file(s) to lock"

    # Lock each file
    local count=0
    local failed=0
    for file in "${files[@]}"; do
        if [[ $DRY_RUN == true ]]; then
            echo "[DRY RUN] Would lock: $file"
            ((count++)) || true
        else
            if chattr +i "$file" 2>&1; then
                echo "✓ Locked: $file"
                ((count++)) || true
            else
                echo "✗ Failed to lock: $file" >&2
                ((failed++)) || true
            fi
        fi
    done

    echo ""
    if [[ $DRY_RUN == true ]]; then
        echo "[DRY RUN] Would lock $count file(s)"
    else
        echo "✓ Locked $count file(s)"
        if (( failed > 0 )); then
            echo "✗ $failed file(s) failed to lock"
            exit 1
        fi
    fi
}

unlock_single() {
    local target_path="$1"

    # Convert to absolute path if relative
    if [[ ! "$target_path" = /* ]]; then
        target_path="$ROOT_DIR/$target_path"
    fi

    # Validate path exists
    if [[ ! -e "$target_path" ]]; then
        echo "ERROR: Path not found: $target_path" >&2
        exit 1
    fi

    if [[ $DRY_RUN == true ]]; then
        echo "[DRY RUN] Would unlock: $target_path"
        echo "[DRY RUN] Would remove immutable flag (chattr -i)..."
    else
        echo "Unlocking: $target_path"
        echo "Removing immutable flag (chattr -i)..."
    fi

    # Build array of files to unlock
    local files=()
    if [[ -f "$target_path" ]]; then
        # Single file
        files=("$target_path")
    elif [[ -d "$target_path" ]]; then
        # Directory - find all matching files
        mapfile -d '' files < <(find "$target_path" -type f \( \
            -name "*.py" -o \
            -name "*.sh" -o \
            -name "*.yaml" -o \
            -name "*.yml" -o \
            -name "*.json" -o \
            -name "*.toml" -o \
            -name "*.ini" -o \
            -name "*.cfg" -o \
            -name "*.md" -o \
            -name "pyproject.toml" -o \
            -name "ruff.toml" -o \
            -name "mypy.ini" -o \
            -name "pytest.ini" \
        \) -print0)
    fi

    if [[ ${#files[@]} -eq 0 ]]; then
        echo "ERROR: No matching source files found" >&2
        exit 1
    fi

    echo "Found ${#files[@]} file(s) to unlock"

    # Unlock each file
    local count=0
    local failed=0
    for file in "${files[@]}"; do
        if [[ $DRY_RUN == true ]]; then
            echo "[DRY RUN] Would unlock: $file"
            ((count++)) || true
        else
            if chattr -i "$file" 2>&1; then
                echo "✓ Unlocked: $file"
                ((count++)) || true
                # Restore write permission
                chmod u+w "$file"
            else
                echo "✗ Failed to unlock: $file" >&2
                ((failed++)) || true
            fi
        fi
    done

    echo ""
    if [[ $DRY_RUN == true ]]; then
        echo "[DRY RUN] Would unlock $count file(s)"
    else
        echo "✓ Unlocked $count file(s)"
        if (( failed > 0 )); then
            echo "✗ $failed file(s) failed to unlock"
            exit 1
        fi
    fi
}

show_status() {
    echo "Protected directories: $ROOT_DIR/scripts and $ROOT_DIR/base/scripts"
    echo -n "Protection status: "
    get_status

    # Count locked vs unlocked files
    local locked=0
    local unlocked=0

    # Count script files
    while IFS= read -r -d '' file; do
        if lsattr "$file" 2>/dev/null | grep -q "^....i"; then
            ((locked++))
        else
            ((unlocked++))
        fi
    done < <(find "$ROOT_DIR/scripts" "$ROOT_DIR/base/scripts" -type f \( \
        -name "*.py" -o \
        -name "*.sh" -o \
        -name "*.yaml" -o \
        -name "*.yml" -o \
        -name "*.json" -o \
        -name "*.toml" -o \
        -name "*.ini" -o \
        -name "*.cfg" -o \
        -name "*.md" \
    \) -print0)

    # Count config files across repo
    while IFS= read -r -d '' file; do
        if lsattr "$file" 2>/dev/null | grep -q "^....i"; then
            ((locked++))
        else
            ((unlocked++))
        fi
    done < <(find "$ROOT_DIR" \
        \( -path "*/.venv*" -o -path "*/node_modules" -o -path "*/.git" -o -path "*/__pycache__" -o -path "*/.cache" -o -path "*/.pytest_cache" -o -path "*/.mypy_cache" -o -path "*/.ruff_cache" -o -path "*/build" -o -path "*/dist" -o -path "*/chromium*" -o -path "*/.gcloud" \) -prune -o \
        -type f \( -name "pyproject.toml" -o -name "ruff.toml" -o -name "mypy.ini" -o -name "pytest.ini" \) -print0)

    # Count git hooks across repo
    while IFS= read -r -d '' file; do
        if lsattr "$file" 2>/dev/null | grep -q "^....i"; then
            ((locked++))
        else
            ((unlocked++))
        fi
    done < <(find "$ROOT_DIR" \
        -path "*/.git/hooks/*" -type f -print0)

    echo ""
    echo "Source files:"
    echo "  Locked (immutable):   $locked"
    echo "  Unlocked (mutable):   $unlocked"
    echo "  Total:                $((locked + unlocked))"
}

run_test() {
    echo "=== RUNNING COMPREHENSIVE TEST ==="
    echo ""

    DRY_RUN=true

    echo "TEST 1: Lock operation"
    echo "======================"
    lock_files
    echo ""

    echo "TEST 2: Unlock operation"
    echo "========================"
    unlock_files
    echo ""

    echo "TEST 3: File discovery"
    echo "======================"
    local script_count=$(find "$ROOT_DIR/scripts" "$ROOT_DIR/base/scripts" -type f \( \
        -name "*.py" -o \
        -name "*.sh" -o \
        -name "*.yaml" -o \
        -name "*.yml" -o \
        -name "*.json" -o \
        -name "*.toml" -o \
        -name "*.ini" -o \
        -name "*.cfg" -o \
        -name "*.md" \
    \) | wc -l)
    local config_count=$(find "$ROOT_DIR" \
        \( -path "*/.venv*" -o -path "*/node_modules" -o -path "*/.git" -o -path "*/__pycache__" -o -path "*/.cache" -o -path "*/.pytest_cache" -o -path "*/.mypy_cache" -o -path "*/.ruff_cache" -o -path "*/build" -o -path "*/dist" -o -path "*/chromium*" -o -path "*/.gcloud" \) -prune -o \
        -type f \( -name "pyproject.toml" -o -name "ruff.toml" -o -name "mypy.ini" -o -name "pytest.ini" \) -print | wc -l)
    local git_hooks_count=$(find "$ROOT_DIR" \
        -path "*/.git/hooks/*" -type f | wc -l)
    echo "✓ Found $script_count script files"
    echo "✓ Found $config_count config files"
    echo "✓ Found $git_hooks_count git hook files"
    echo "✓ Total: $((script_count + config_count + git_hooks_count)) files"
    echo ""

    echo "TEST 4: Sample files"
    echo "===================="
    echo "First 5 files from each directory that would be protected:"
    echo ""
    echo "From /scripts:"
    find "$ROOT_DIR/scripts" -type f \( \
        -name "*.py" -o \
        -name "*.sh" -o \
        -name "*.toml" \
    \) | head -5
    echo ""
    echo "From /base/scripts:"
    find "$ROOT_DIR/base/scripts" -type f \( \
        -name "*.py" -o \
        -name "*.sh" -o \
        -name "*.toml" \
    \) 2>/dev/null | head -5 || echo "(base/scripts not found or empty)"
    echo ""
    echo "Git hooks:"
    find "$ROOT_DIR" -path "*/.git/hooks/*" -type f 2>/dev/null | head -5 || echo "(no git hooks found)"
    echo ""

    echo "=== ALL TESTS PASSED ==="
    echo ""
    echo "To actually lock files, run:"
    echo "  sudo $0 lock"
}

main() {
    # Parse arguments
    local command=""
    local target_path=""

    for arg in "$@"; do
        case "$arg" in
            --dry-run)
                DRY_RUN=true
                ;;
            lock|unlock|status|test|lock-file|unlock-file|-h|--help|help)
                command="$arg"
                ;;
            *)
                # If command is set and this doesn't start with -, it's a path argument
                if [[ -n "$command" && "$arg" != -* ]]; then
                    target_path="$arg"
                else
                    echo "ERROR: Unknown argument '$arg'" >&2
                    show_usage
                    exit 1
                fi
                ;;
        esac
    done

    if [[ -z "$command" ]]; then
        show_usage
        exit 1
    fi

    # Validate path for single file/directory commands
    if [[ "$command" == "lock-file" || "$command" == "unlock-file" ]]; then
        if [[ -z "$target_path" ]]; then
            echo "ERROR: $command requires a path argument" >&2
            echo "" >&2
            show_usage
            exit 1
        fi
    fi

    # Test command runs in dry-run mode automatically
    if [[ "$command" == "test" ]]; then
        DRY_RUN=true
    fi

    # Skip root check for help and test commands
    if [[ "$command" != "-h" && "$command" != "--help" && "$command" != "help" ]]; then
        check_root
    fi

    case "$command" in
        lock)
            # If target_path provided, use lock_single; otherwise lock_files
            if [[ -n "$target_path" ]]; then
                lock_single "$target_path"
            else
                lock_files
            fi
            ;;
        unlock)
            # If target_path provided, use unlock_single; otherwise unlock_files
            if [[ -n "$target_path" ]]; then
                unlock_single "$target_path"
            else
                unlock_files
            fi
            ;;
        lock-file)
            lock_single "$target_path"
            ;;
        unlock-file)
            unlock_single "$target_path"
            ;;
        status)
            show_status
            ;;
        test)
            run_test
            ;;
        -h|--help|help)
            show_usage
            ;;
        *)
            echo "ERROR: Unknown command '$command'" >&2
            echo "" >&2
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
