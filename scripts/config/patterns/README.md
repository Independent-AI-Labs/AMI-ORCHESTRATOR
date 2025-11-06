# Pattern Validation System

This directory contains YAML configuration files for the automated pattern validation system used by Claude Code hooks.

## Overview

Pattern validation provides fast, consistent checks that run **before** expensive LLM audits. Patterns are defined in YAML files for easy maintenance and modification without code changes.

## Pattern Files

### bash_commands.yaml

Defines forbidden Bash command patterns checked by `CommandValidator` in `scripts/automation/hooks.py`.

**Purpose**: Enforce use of Claude Code tools and approved wrappers instead of raw shell commands.

**Structure**:
```yaml
deny_patterns:
  - pattern: '\bdocker\b'          # Regex pattern to match
    message: "Use setup_service.py to manage containers"  # Error message
```

**Examples**:
- Block `docker` → require `setup_service.py`
- Block `python3` → require `ami-run`
- Block pipes `|` → require dedicated tools (Read/Grep)
- Block operators `&&`, `;`, `||` → require separate Bash calls

### python_fast.yaml

Defines Python code patterns checked by `validate_python_patterns()` in `scripts/automation/validators.py`.

**Purpose**: Fast pattern checks before LLM diff audit (non-empty __init__.py, path manipulation, code suppressions).

**Structure**:
```yaml
patterns:
  - name: "pattern_name"
    check_type: "content_pattern"  # or "file_content"
    pattern: '.parent.parent'       # String pattern to match
    allow_removal: true             # Only block ADDITIONS (allow cleanup)
    error_template: |
      ❌ ERROR MESSAGE HERE
    exemptions:
      - path_patterns:
          - "**/module_setup.py"
        allowed_patterns:
          - '# noqa: E402'
```

**Check Types**:
- `file_content`: Match file path + check condition (e.g., non-empty __init__.py)
- `content_pattern`: Match pattern strings in content (e.g., .parent.parent, suppressions)

**Key Feature - allow_removal**:
When `allow_removal: true`, only **ADDITIONS** of the pattern are blocked:
- Counts pattern in old_content vs new_content
- If new_count > old_count → BLOCK (addition detected)
- If new_count <= old_count → ALLOW (removal or no change)

This enables zero-tolerance for new violations while allowing cleanup of existing issues.

**Examples**:
1. Non-empty __init__.py:
   ```yaml
   - name: "non_empty_init"
     check_type: "file_content"
     file_match: "**/__init__.py"
     condition: "not_empty"
   ```

2. Forbidden path pattern (allow removals):
   ```yaml
   - name: "parent_parent"
     check_type: "content_pattern"
     pattern: '.parent.parent'
     allow_removal: true  # Only block ADDITIONS
   ```

3. Code suppressions with exemptions:
   ```yaml
   - name: "code_suppression"
     check_type: "content_pattern"
     patterns:
       - '# noqa'
       - '# type: ignore'
     allow_removal: true  # Allow cleanup
     exemptions:
       - path_patterns:
           - "**/module_setup.py"
           - "scripts/**/*.py"
         allowed_patterns:
           - '# noqa: E402'  # E402 = import not at top (path discovery)
   ```

### exemptions.yaml

Lists files exempt from **ALL** pattern checks.

**Purpose**: Exclude files that legitimately contain forbidden patterns (e.g., pattern definitions in error messages).

**Structure**:
```yaml
pattern_check_exemptions:
  - "scripts/automation/hooks.py"
  - "scripts/automation/validators.py"
  - "scripts/config/patterns/*.yaml"
```

**Usage**: Files listed here skip all fast pattern validation in `CodeQualityValidator`.

## Implementation

### Loading Patterns

Patterns are loaded via cached functions in `scripts/automation/validators.py`:

```python
from scripts.automation.validators import (
    load_python_patterns,  # Load python_fast.yaml
    load_bash_patterns,    # Load bash_commands.yaml
    load_exemptions,       # Load exemptions.yaml
)

# Functions are @lru_cache decorated - loaded once per process
patterns = load_python_patterns()
```

### Using Patterns

**Bash Command Validation** (`CommandValidator`):
```python
deny_patterns = load_bash_patterns()
for pattern_config in deny_patterns:
    pattern = pattern_config.get("pattern", "")
    message = pattern_config.get("message", "")
    if re.search(pattern, command):
        return HookResult.deny(f"{message} (pattern: {pattern})")
```

**Python Code Validation** (`validate_python_patterns`):
```python
patterns = load_python_patterns()
for pattern_config in patterns:
    is_violation, error_msg = check_pattern_violation(
        file_path,
        old_content,  # Required for allow_removal logic
        new_content,
        pattern_config,
    )
    if is_violation:
        return False, error_msg
```

### Pattern Matching Engine

The `check_pattern_violation()` function in `validators.py` handles:
- File path matching (glob patterns converted to regex)
- Old/new content comparison (for `allow_removal`)
- Exemption checking (path patterns + allowed patterns)
- Multiple pattern strings (e.g., all suppression comment types)

## Validation Flow

1. **Bash Command**: `CommandValidator` → load_bash_patterns() → regex match
2. **Python Edit/Write**:
   - `CodeQualityValidator` → load_exemptions() → check if exempt
   - If not exempt → `validate_python_full()`
     - `validate_python_patterns()` → load_python_patterns() → check each pattern
     - `validate_python_diff_llm()` → LLM audit against patterns_core.txt

## Benefits

- ✅ **Single source of truth**: All patterns in YAML, not scattered in Python code
- ✅ **Easy maintenance**: Edit YAML without code changes
- ✅ **Consistent behavior**: Same logic across all validators
- ✅ **Smart cleanup**: `allow_removal` permits removing violations while blocking new ones
- ✅ **Flexible exemptions**: Path patterns + pattern-specific allowed lists
- ✅ **Fast execution**: Cached loading, pattern checks before LLM
- ✅ **Self-documenting**: YAML structure shows intent clearly

## Adding New Patterns

### Add Bash Pattern

Edit `bash_commands.yaml`:
```yaml
deny_patterns:
  - pattern: '\bnew_command\b'
    message: "Use approved wrapper instead"
```

### Add Python Pattern

Edit `python_fast.yaml`:
```yaml
patterns:
  - name: "my_pattern"
    check_type: "content_pattern"
    pattern: 'forbidden_string'
    allow_removal: false  # Block if present in new content
    error_template: |
      ❌ YOUR ERROR MESSAGE
```

### Add Exemption

Edit `exemptions.yaml`:
```yaml
pattern_check_exemptions:
  - "path/to/exempt/file.py"
```

Changes take effect immediately - no code changes or restarts required (hooks reload on each invocation).

## Testing

The pattern system is self-testing - any violations during development will be caught by the hooks themselves.

To verify patterns load correctly, use the YAML validators in your development workflow.
