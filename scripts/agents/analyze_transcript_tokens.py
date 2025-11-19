#!/usr/bin/env bash
""":'
exec "$(dirname "$0")/../scripts/ami-run" "$0" "$@"
"""

"""Analyze token counts for all transcript files to determine context window requirements.

This script scans all Claude Code transcript files and calculates token counts
to help determine if full transcripts can fit within the 200K token context limit
for the completion moderator.
"""

import statistics  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import TypedDict  # noqa: E402


def _ensure_repo_on_path() -> Path:
    """Add orchestrator root to sys.path and return it."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists() and (current / "base").exists():
            sys.path.insert(0, str(current))
            return current
        current = current.parent
    raise RuntimeError("Unable to locate AMI orchestrator root")


_ensure_repo_on_path()

# Import after adding repo to path
import tiktoken  # noqa: E402

from scripts.agents.transcript import format_messages_for_prompt, get_last_n_messages  # noqa: E402

# Token count thresholds for analysis
TOKEN_THRESHOLD_200K = 200_000
TOKEN_THRESHOLD_100K = 100_000
TOKEN_THRESHOLD_50K = 50_000
TOKEN_THRESHOLD_25K = 25_000


class TranscriptAnalysis(TypedDict):
    """Result of analyzing a single transcript file."""

    name: str
    tokens: int
    messages: int


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken (GPT-4 tokenizer).

    Args:
        text: Text to count tokens for

    Returns:
        Token count

    Raises:
        Exception: If tokenization fails
    """
    encoding = tiktoken.encoding_for_model("gpt-4")
    return len(encoding.encode(text))


def analyze_transcript(transcript_path: Path) -> TranscriptAnalysis:
    """Analyze a single transcript file.

    Args:
        transcript_path: Path to transcript JSONL file

    Returns:
        Analysis result with token counts and metadata

    Raises:
        Exception: If transcript parsing or tokenization fails
    """
    # Count total lines in transcript
    line_count = len(transcript_path.read_text().splitlines())

    # Get all messages from transcript
    messages = get_last_n_messages(transcript_path, line_count) if line_count > 0 else []

    if not messages:
        return TranscriptAnalysis(
            name=transcript_path.name,
            tokens=0,
            messages=0,
        )

    # Format as prompt
    formatted_text = format_messages_for_prompt(messages)

    # Count tokens
    token_count = count_tokens(formatted_text)

    return TranscriptAnalysis(
        name=transcript_path.name,
        tokens=token_count,
        messages=len(messages),
    )


def main() -> int:
    """Analyze all transcripts and output statistics.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Find transcript directory
    transcript_dir = Path.home() / ".claude" / "projects" / "-home-ami-Projects-AMI-ORCHESTRATOR"

    if not transcript_dir.exists():
        return 1

    # Find all transcript files
    transcript_files = list(transcript_dir.glob("*.jsonl"))
    transcript_files = [f for f in transcript_files if not f.name.endswith(".scanner_state")]

    if not transcript_files:
        return 1

    # Analyze each transcript
    results: list[TranscriptAnalysis] = []
    failed_count = 0

    for idx, transcript_path in enumerate(transcript_files, 1):
        try:
            result = analyze_transcript(transcript_path)
            results.append(result)
            if idx % 100 == 0:
                pass
        except Exception:
            failed_count += 1

    if not results:
        return 1

    if failed_count > 0:
        pass

    # Calculate statistics
    token_counts = [r["tokens"] for r in results]

    min(token_counts)
    max_tokens = max(token_counts)
    statistics.mean(token_counts)
    statistics.median(token_counts)

    # Distribution
    sum(1 for t in token_counts if t > TOKEN_THRESHOLD_200K)
    sum(1 for t in token_counts if t > TOKEN_THRESHOLD_100K)
    sum(1 for t in token_counts if t > TOKEN_THRESHOLD_50K)
    sum(1 for t in token_counts if t > TOKEN_THRESHOLD_25K)

    # Top 10 largest
    sorted_results = sorted(results, key=lambda r: r["tokens"], reverse=True)
    top_10 = sorted_results[:10]

    # Output statistics
    for _i, result in enumerate(top_10, 1):
        result["name"][:50]
        result["tokens"]
        result["messages"]

    # Context window analysis
    if max_tokens <= TOKEN_THRESHOLD_200K:
        pass
    else:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
