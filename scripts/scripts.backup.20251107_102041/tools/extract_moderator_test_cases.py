#!/usr/bin/env python3
"""Extract real transcript contexts for moderator e2e tests.

Uses production prepare_moderator_context() to verify EXACT context
that would be sent to completion moderator from real conversation segments.
"""

import json
import logging
import sys
from pathlib import Path


def _ensure_repo_on_path() -> Path:
    """Find repo root and add to sys.path."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists() and (current / "base").exists():
            sys.path.insert(0, str(current))
            return current
        current = current.parent
    raise RuntimeError("Unable to locate AMI orchestrator root")


_ensure_repo_on_path()

from scripts.automation.hooks import prepare_moderator_context

logger = logging.getLogger(__name__)

# Maximum number of test cases to extract
MAX_TEST_CASES = 5


def find_recent_transcripts(transcript_dir: Path, max_cases: int = 200) -> list[Path]:
    """Find newest transcript files to extract test cases from.

    Args:
        transcript_dir: Directory containing transcript JSONL files
        max_cases: Maximum number of transcripts to search

    Returns:
        List of newest transcript paths to search

    Raises:
        FileNotFoundError: If transcript_dir doesn't exist
        OSError: If file operations fail
    """
    if not transcript_dir.exists():
        raise FileNotFoundError(f"Transcript directory not found: {transcript_dir}")

    # Get NEWEST transcripts by modification time (reverse=True gives newest first)
    try:
        all_transcripts = sorted(transcript_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError as e:
        logger.error("Failed to list transcripts: %s", e)
        raise

    return all_transcripts[:max_cases]


def find_work_done_marker(lines: list[str]) -> int | None:
    """Find last WORK DONE marker in transcript lines.

    Args:
        lines: List of JSONL transcript lines

    Returns:
        Index of last WORK DONE message, or None if not found
    """
    for i in range(len(lines) - 1, -1, -1):
        try:
            msg = json.loads(lines[i])
            # Only check assistant messages (stop hook feedback is type=user and quotes "WORK DONE")
            if msg.get("type") != "assistant":
                continue
            content = msg.get("message", {}).get("content", "")
            if isinstance(content, str) and "WORK DONE" in content:
                return i
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text" and "WORK DONE" in item.get("text", ""):
                        return i
        except json.JSONDecodeError:
            continue
    return None


def process_transcript(transcript_path: Path, output_dir: Path, case_number: int) -> tuple[bool, str | None, int]:
    """Process single transcript and extract test case.

    Args:
        transcript_path: Path to transcript file
        output_dir: Directory to save extracted cases
        case_number: Test case number for naming

    Returns:
        Tuple of (success, context_or_none, context_length)
    """
    logger.info("Processing: %s", transcript_path.name)

    # Read transcript
    try:
        with transcript_path.open(encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        logger.error("  Failed to read transcript: %s", e)
        return False, None, 0

    # Find WORK DONE marker
    work_done_idx = find_work_done_marker(lines)
    if work_done_idx is None:
        logger.info("  - No WORK DONE marker found, skipping")
        return True, None, 0

    # Truncate transcript
    truncated_lines = lines[: work_done_idx + 1]
    if not truncated_lines:
        logger.info("  - Empty transcript after truncation, skipping")
        return True, None, 0

    # Save and verify extraction
    temp_file = output_dir / f"temp_{transcript_path.stem}.jsonl"
    try:
        with temp_file.open("w", encoding="utf-8") as f:
            f.writelines(truncated_lines)

        context = prepare_moderator_context(temp_file)
        if not context:
            logger.info("  - No context extractable by moderator function, skipping")
            temp_file.unlink(missing_ok=True)
            return True, None, 0

        # Rename to final name
        output_file = output_dir / f"real_case_{case_number}_{transcript_path.stem[:12]}.jsonl"
        temp_file.rename(output_file)

        logger.info("  ✓ Saved: %s", output_file.name)
        logger.info("  - Lines: %d", len(truncated_lines))
        logger.info("  - Context size: %d chars", len(context))
        return True, context, len(context)

    except Exception as e:
        logger.info("  - Failed to extract context: %s", e)
        temp_file.unlink(missing_ok=True)
        return True, None, 0


def main() -> int:
    """Main entry point.

    Returns:
        0 on success, 1 on failure
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    transcript_dir = Path.home() / ".claude/projects/-home-ami-Projects-AMI-ORCHESTRATOR"
    output_dir = Path("tests/integration/fixtures/transcripts")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error("Failed to create output directory %s: %s", output_dir, e)
        return 1

    logger.info("Searching for recent transcripts in %s", transcript_dir)

    try:
        transcripts = find_recent_transcripts(transcript_dir, max_cases=200)
    except (FileNotFoundError, OSError) as e:
        logger.error("Failed to find transcripts: %s", e)
        return 1

    logger.info("Found %d recent transcripts", len(transcripts))

    extracted = 0
    for transcript_path in transcripts:
        success, context, _ = process_transcript(transcript_path, output_dir, extracted)
        if not success:
            return 1
        if context:
            extracted += 1
            if extracted >= MAX_TEST_CASES:
                break

    logger.info("✓ Extracted %d real transcript contexts to %s", extracted, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
