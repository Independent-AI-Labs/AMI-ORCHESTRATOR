#!/usr/bin/env python3
"""Analyze token counts for all transcript files to determine context window requirements.

This script scans all Claude Code transcript files and calculates token counts
to help determine if full transcripts can fit within the 200K token context limit
for the completion moderator.
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path
from typing import TypedDict


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

import tiktoken

# Token count thresholds for analysis
TOKEN_THRESHOLD_200K = 200_000
TOKEN_THRESHOLD_100K = 100_000
TOKEN_THRESHOLD_50K = 50_000
TOKEN_THRESHOLD_25K = 25_000

from scripts.automation.transcript import format_messages_for_prompt, get_last_n_messages


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
        print(f"Error: Transcript directory not found: {transcript_dir}")
        return 1

    # Find all transcript files
    transcript_files = list(transcript_dir.glob("*.jsonl"))
    transcript_files = [f for f in transcript_files if not f.name.endswith(".scanner_state")]

    if not transcript_files:
        print("Error: No transcript files found")
        return 1

    print(f"Analyzing {len(transcript_files)} transcript files...")
    print()

    # Analyze each transcript
    results: list[TranscriptAnalysis] = []
    failed_count = 0

    for idx, transcript_path in enumerate(transcript_files, 1):
        try:
            result = analyze_transcript(transcript_path)
            results.append(result)
            if idx % 100 == 0:
                print(f"  Processed {idx}/{len(transcript_files)} files...")
        except Exception as e:
            failed_count += 1
            print(f"  Error: {transcript_path.name}: {str(e)[:80]}")

    if not results:
        print(f"\nError: All {len(transcript_files)} transcripts failed analysis")
        return 1

    print(f"  Successfully analyzed: {len(results)}/{len(transcript_files)} files")
    if failed_count > 0:
        print(f"  Failed: {failed_count} files")
    print()

    # Calculate statistics
    token_counts = [r["tokens"] for r in results]

    min_tokens = min(token_counts)
    max_tokens = max(token_counts)
    avg_tokens = statistics.mean(token_counts)
    median_tokens = statistics.median(token_counts)

    # Distribution
    over_200k = sum(1 for t in token_counts if t > TOKEN_THRESHOLD_200K)
    over_100k = sum(1 for t in token_counts if t > TOKEN_THRESHOLD_100K)
    over_50k = sum(1 for t in token_counts if t > TOKEN_THRESHOLD_50K)
    over_25k = sum(1 for t in token_counts if t > TOKEN_THRESHOLD_25K)

    # Top 10 largest
    sorted_results = sorted(results, key=lambda r: r["tokens"], reverse=True)
    top_10 = sorted_results[:10]

    # Output statistics
    print("=" * 80)
    print("TRANSCRIPT TOKEN ANALYSIS")
    print("=" * 80)
    print()
    print(f"Total transcripts analyzed: {len(results)}")
    print()
    print("TOKEN STATISTICS:")
    print(f"  Minimum:  {min_tokens:>10,} tokens")
    print(f"  Maximum:  {max_tokens:>10,} tokens")
    print(f"  Average:  {avg_tokens:>10,.0f} tokens")
    print(f"  Median:   {median_tokens:>10,.0f} tokens")
    print()
    print("DISTRIBUTION:")
    print(f"  > 200K tokens: {over_200k:>5} transcripts ({over_200k / len(results) * 100:.1f}%)")
    print(f"  > 100K tokens: {over_100k:>5} transcripts ({over_100k / len(results) * 100:.1f}%)")
    print(f"  >  50K tokens: {over_50k:>5} transcripts ({over_50k / len(results) * 100:.1f}%)")
    print(f"  >  25K tokens: {over_25k:>5} transcripts ({over_25k / len(results) * 100:.1f}%)")
    print()
    print("TOP 10 LARGEST TRANSCRIPTS:")
    print()
    for i, result in enumerate(top_10, 1):
        name = result["name"][:50]
        tokens = result["tokens"]
        messages = result["messages"]
        print(f"  {i:>2}. {name:<50} {tokens:>10,} tokens ({messages:>4} msgs)")
    print()
    print("=" * 80)
    print()

    # Context window analysis
    if max_tokens <= TOKEN_THRESHOLD_200K:
        print("✅ RESULT: All transcripts fit within 200K token context window.")
        print()
    else:
        print(f"⚠️  RESULT: {over_200k} transcripts exceed 200K token context window.")
        print(f"   Largest transcript: {max_tokens:,} tokens")
        print()
        print("   RECOMMENDATIONS:")
        print("   1. Implement transcript truncation for large sessions")
        print("   2. Use sliding window (last N user messages)")
        print("   3. Summarize older messages and keep recent ones")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
