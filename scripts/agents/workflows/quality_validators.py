"""Quality validators for code changes and Python-specific checks."""

from pathlib import Path

from scripts.agents.validation.llm_validators import validate_diff_llm
from scripts.agents.validation.validation_utils import load_exemptions
from scripts.agents.workflows.core import HookInput, HookResult, HookValidator


class CoreQualityValidator(HookValidator):
    """Validates code changes for cross-language quality patterns using LLM-based audit."""

    def _extract_old_new_code(self, hook_input: HookInput) -> tuple[str, str]:
        """Extract old and new code with FULL file context for proper validation.

        For Edit operations, reads the complete file and applies the transformation
        to provide full context to validators. This prevents false positives when
        validators need to check patterns like deferred imports that require knowing
        the complete file structure.

        Args:
            hook_input: Hook input containing file edits

        Returns:
            Tuple of (full_old_content, full_new_content) with complete file context
        """
        if hook_input.tool_input is None:
            return "", ""

        file_path = hook_input.tool_input.get("file_path", "")
        file_path_obj = Path(file_path)

        if hook_input.tool_name == "Edit":
            # Read FULL current file content for proper context
            if not file_path_obj.exists():
                return "", ""

            full_old_content = file_path_obj.read_text()
            old_string = hook_input.tool_input.get("old_string", "")
            new_string = hook_input.tool_input.get("new_string", "")

            # Apply edit to get FULL new content
            if old_string in full_old_content:
                full_new_content = full_old_content.replace(old_string, new_string, 1)
            else:
                # Edit will fail anyway, but return fragments so validator can see what was attempted
                return old_string, new_string

            return full_old_content, full_new_content

        # Write operation - already has full content
        old_content = file_path_obj.read_text() if file_path_obj.exists() else ""
        new_content = hook_input.tool_input.get("content", "")
        return old_content, new_content

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate code quality using cross-language patterns.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        # Early exit for invalid inputs
        if hook_input.tool_name not in ("Edit", "Write") or hook_input.tool_input is None:
            return HookResult.allow()

        # Extract file path
        file_path = hook_input.tool_input.get("file_path", "")

        # Extract old/new code
        old_code, new_code = self._extract_old_new_code(hook_input)

        # Load exemptions from YAML
        exemptions = load_exemptions()

        # Check if file is exempt from pattern checks
        # Support both endswith (extensions) and contains (path patterns)
        is_pattern_exempt = any(file_path.endswith(exempt) or exempt in file_path for exempt in exemptions)

        # Skip validation for exempt files
        if is_pattern_exempt:
            return HookResult.allow()

        # Use shared validation logic with patterns_core.txt
        is_valid, reason = validate_diff_llm(
            file_path=file_path,
            old_content=old_code,
            new_content=new_code,
            session_id=hook_input.session_id,
            patterns_file="patterns_core.txt",
        )

        if is_valid:
            return HookResult.allow()
        return HookResult.deny(
            f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            f"Hook: PreToolUse ({hook_input.tool_name})\n"
            f"Validator: CoreQualityValidator\n\n"
            f"{reason}"
        )


class PythonQualityValidator(HookValidator):
    """Validates Python code changes for Python-specific quality patterns using LLM-based audit."""

    def _extract_old_new_code(self, hook_input: HookInput) -> tuple[str, str]:
        """Extract old and new code with FULL file context for proper validation.

        For Edit operations, reads the complete file and applies the transformation
        to provide full context to validators. This prevents false positives when
        validators need to check patterns like deferred imports that require knowing
        the complete file structure.

        Args:
            hook_input: Hook input containing file edits

        Returns:
            Tuple of (full_old_content, full_new_content) with complete file context
        """
        if hook_input.tool_input is None:
            return "", ""

        file_path = hook_input.tool_input.get("file_path", "")
        file_path_obj = Path(file_path)

        if hook_input.tool_name == "Edit":
            # Read FULL current file content for proper context
            if not file_path_obj.exists():
                return "", ""

            full_old_content = file_path_obj.read_text()
            old_string = hook_input.tool_input.get("old_string", "")
            new_string = hook_input.tool_input.get("new_string", "")

            # Apply edit to get FULL new content
            if old_string in full_old_content:
                full_new_content = full_old_content.replace(old_string, new_string, 1)
            else:
                # Edit will fail anyway, but return fragments so validator can see what was attempted
                return old_string, new_string

            return full_old_content, full_new_content

        # Write operation - already has full content
        old_content = file_path_obj.read_text() if file_path_obj.exists() else ""
        new_content = hook_input.tool_input.get("content", "")
        return old_content, new_content

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate Python code quality using Python-specific patterns.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        # Early exit for non-Python edits or invalid inputs
        if hook_input.tool_name not in ("Edit", "Write") or hook_input.tool_input is None or not hook_input.tool_input.get("file_path", "").endswith(".py"):
            return HookResult.allow()

        # Extract file path
        file_path = hook_input.tool_input.get("file_path", "")

        # Extract old/new code
        old_code, new_code = self._extract_old_new_code(hook_input)

        # Load exemptions from YAML
        exemptions = load_exemptions()

        # Check if file is exempt from pattern checks
        # Support both endswith (extensions) and contains (path patterns)
        is_pattern_exempt = any(file_path.endswith(exempt) or exempt in file_path for exempt in exemptions)

        # Skip validation for exempt files
        if is_pattern_exempt:
            return HookResult.allow()

        # Use shared validation logic with patterns_python.txt
        is_valid, reason = validate_diff_llm(
            file_path=file_path,
            old_content=old_code,
            new_content=new_code,
            session_id=hook_input.session_id,
            patterns_file="patterns_python.txt",
        )

        if is_valid:
            return HookResult.allow()
        return HookResult.deny(
            f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            f"Hook: PreToolUse ({hook_input.tool_name})\n"
            f"Validator: PythonQualityValidator\n\n"
            f"{reason}"
        )


class ShebangValidator(HookValidator):
    """Validates Python file shebangs for security and correctness."""

    def validate(self, hook_input: HookInput) -> HookResult:
        """Validate shebangs in Python files.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        # Only check Python files on Edit/Write
        if hook_input.tool_name not in ("Edit", "Write") or hook_input.tool_input is None:
            return HookResult.allow()

        file_path_str = hook_input.tool_input.get("file_path", "")
        if not file_path_str.endswith(".py"):
            return HookResult.allow()

        file_path = Path(file_path_str)

        # Get new content
        if hook_input.tool_name == "Write":
            new_content = hook_input.tool_input.get("content", "")
        else:  # Edit
            # For edits, check if shebang is being modified
            old_string = hook_input.tool_input.get("old_string", "")
            new_string = hook_input.tool_input.get("new_string", "")

            # Only check if shebang lines are involved
            if not (old_string.startswith("#!") or new_string.startswith("#!")):
                return HookResult.allow()

            # Read current file and apply edit to get new content
            if file_path.exists():
                current = file_path.read_text()
                new_content = current.replace(old_string, new_string, 1)
            else:
                new_content = new_string

        # Check first 200 bytes for shebang
        first_lines = new_content[:200].encode()

        # Security patterns (fail immediately)
        security_issues = [
            (b"sudo", "Contains sudo (security risk)"),
            (b"/usr/bin/python", "System python path (out-of-sandbox)"),
            (b"/usr/local/bin/python", "System python path (out-of-sandbox)"),
        ]

        for pattern, description in security_issues:
            if pattern in first_lines:
                return HookResult.deny(
                    f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                    f"Hook: PreToolUse ({hook_input.tool_name})\n"
                    f"Validator: ShebangValidator\n\n"
                    f"SECURITY: {description} in {file_path_str}"
                )

        # Incorrect patterns
        incorrect_patterns = [
            (b"#!/usr/bin/env python3", "Direct python3 shebang"),
            (b"#!/usr/bin/env python", "Direct python shebang"),
            (b"#!/usr/bin/python", "Direct python shebang"),
            (b'.venv/bin/python"', "Direct .venv python"),
        ]

        for pattern, description in incorrect_patterns:
            if pattern in first_lines and b"ami-run" not in first_lines:
                return HookResult.deny(
                    f"🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
                    f"Hook: PreToolUse ({hook_input.tool_name})\n"
                    f"Validator: ShebangValidator\n\n"
                    f"Shebang issue: {description} in {file_path_str}. Use ami-run wrapper instead."
                )

        return HookResult.allow()
