"""Response validators for completion markers and communication rules."""

from pathlib import Path
from typing import Any

import yaml

from scripts.agents.config import get_config
from scripts.agents.validation.core import HookResult as ValidationHookResult
from scripts.agents.validation.response_basic_utils import check_api_limit_messages, check_prohibited_patterns, get_last_assistant_message
from scripts.agents.validation.response_utils import (
    check_early_allow_conditions,
)
from scripts.agents.workflows.completion_validator import CompletionValidator
from scripts.agents.workflows.core import HookInput, HookResult, HookValidator  # Import for tests to patch


def _load_completion_markers() -> list[str]:
    """Load completion markers from YAML config.

    Returns:
        List of completion markers
    """
    config = get_config()
    patterns_dir = config.root / "scripts/config/patterns"
    patterns_file = patterns_dir / "completion_markers.yaml"

    if not patterns_file.exists():
        # Return default markers if config doesn't exist
        return ["WORK DONE", "FEEDBACK:"]

    with patterns_file.open() as f:
        data: dict[str, Any] = yaml.safe_load(f)

    completion_markers = data.get("completion_markers", ["WORK DONE", "FEEDBACK:"])
    if completion_markers is None:
        return ["WORK DONE", "FEEDBACK:"]
    if not isinstance(completion_markers, list):
        raise ValueError(f"completion_markers must be a list, got {type(completion_markers)}")
    # Ensure all items in the list are strings
    if not all(isinstance(item, str) for item in completion_markers):
        raise ValueError(f"All items in completion_markers must be strings, got {completion_markers}")
    return completion_markers


class ResponseScanner(HookValidator):
    """Scans responses for communication violations and completion markers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.COMPLETION_MARKERS = _load_completion_markers()
        self._completion_validator = CompletionValidator()

    def validate(self, hook_input: HookInput) -> HookResult:
        """Scan last assistant message.

        Args:
            hook_input: Hook input

        Returns:
            Validation result
        """
        # Check early allow conditions first
        early_result = self._check_early_conditions(hook_input)
        if early_result:
            return early_result

        transcript_path = hook_input.transcript_path
        last_message = get_last_assistant_message(transcript_path) if transcript_path is not None else ""

        # Check for completion markers
        completion_result = self._check_completion_markers(hook_input, transcript_path, last_message)
        if completion_result:
            return completion_result

        # Check for prohibited patterns
        prohibited_result = self._check_prohibited_patterns(last_message)
        if prohibited_result:
            return prohibited_result

        # Check for API limit messages
        api_limit_result = self._check_api_limit_messages(last_message)
        if api_limit_result:
            return api_limit_result

        # No completion markers found, block stop
        return self._get_no_completion_marker_result()

    def _check_early_conditions(self, hook_input: HookInput) -> HookResult | None:
        """Check if early allow conditions are met."""
        should_allow, early_result = check_early_allow_conditions(hook_input)
        if should_allow:
            if early_result is not None and isinstance(early_result, ValidationHookResult):
                # Check the decision attribute of HookResult instead of status
                if early_result.decision == "allow":
                    return HookResult.allow()
                return HookResult.block("Early conditions validation failed - blocking request")
            return early_result if early_result is not None else HookResult.allow()
        return None

    def _check_completion_markers(self, hook_input: HookInput, transcript_path: Path | None, last_message: str) -> HookResult | None:
        """Check if completion markers are present."""
        has_completion_marker = any(marker in last_message for marker in self.COMPLETION_MARKERS)

        if has_completion_marker and transcript_path is not None:
            # Completion marker found - let moderator validate everything
            return self._validate_completion(hook_input.session_id, transcript_path, last_message)
        if has_completion_marker:
            # transcript_path is None, allow the completion to proceed
            return HookResult.allow()
        return None

    def _check_prohibited_patterns(self, last_message: str) -> HookResult | None:
        """Check for prohibited patterns in the message."""
        prohibited_result = check_prohibited_patterns(last_message)
        if not prohibited_result:
            return None

        # Since check_prohibited_patterns returns HookResult (aliased as ValidationHookResult),
        # we can directly check its decision
        if prohibited_result.decision == "allow":
            return HookResult.allow()
        return HookResult.block("Prohibited patterns detected - blocking request")

    def _check_api_limit_messages(self, last_message: str) -> HookResult | None:
        """Check for API limit messages."""
        is_api_limit, api_limit_result = check_api_limit_messages(last_message)
        if is_api_limit:
            if api_limit_result is not None:
                # Since api_limit_result is HookResult, check its decision
                if api_limit_result.decision == "allow":
                    return HookResult.allow()
                return HookResult.block("API limit message detected - blocking request")
            return HookResult.allow()
        return None

    def _get_no_completion_marker_result(self) -> HookResult:
        """Return the result when no completion marker is found."""
        return HookResult.block(
            "🚨 QUALITY VIOLATION - ADDITIONAL TOKENS INCURRED FOR MODERATION\n\n"
            "Hook: Stop\n"
            "Validator: ResponseScanner\n\n"
            "COMPLETION MARKER REQUIRED.\n\n"
            "- Add 'WORK DONE' when task is complete\n"
            "- Add 'FEEDBACK: <reason>' if blocked or need user input\n\n"
            "Never stop without explicitly signaling completion status."
        )

    def _validate_completion(self, session_id: str, transcript_path: Path, last_message: str) -> HookResult:
        """Validate completion marker using internal logic with instance logger.

        Args:
            session_id: Session ID for logging
            transcript_path: Path to transcript file
            last_message: Last assistant message text

        Returns:
            Validation result (ALLOW if work complete, BLOCK if not)
        """
        return self._completion_validator.validate_completion(session_id, transcript_path, last_message, self.logger)
