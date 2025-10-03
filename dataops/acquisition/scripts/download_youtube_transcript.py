#!/usr/bin/env python
"""Download YouTube video transcripts.

This script downloads transcripts from YouTube videos using the youtube-transcript-api.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._transcripts import FetchedTranscript, Transcript, TranscriptList
from youtube_transcript_api.formatters import Formatter, JSONFormatter, SRTFormatter, TextFormatter, WebVTTFormatter


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    if "youtube.com/watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    # Assume it's already a video ID
    return url


def select_transcript(transcript_list: TranscriptList, prefer_auto: bool = False) -> tuple[Transcript, str]:
    """Select appropriate transcript from available options.

    Args:
        transcript_list: List of available transcripts
        prefer_auto: If True, prefer auto-generated over manual transcripts

    Returns:
        Tuple of (transcript_object, transcript_type)
    """
    manual_transcripts = [t for t in transcript_list if not t.is_generated and t.language_code == "en"]
    auto_transcripts = [t for t in transcript_list if t.is_generated and t.language_code == "en"]

    if prefer_auto:
        if auto_transcripts:
            return auto_transcripts[0], "auto-generated"
        if manual_transcripts:
            return manual_transcripts[0], "manual"
    else:
        if manual_transcripts:
            return manual_transcripts[0], "manual"
        if auto_transcripts:
            return auto_transcripts[0], "auto-generated"

    msg = "No English transcripts available"
    raise RuntimeError(msg)


def format_transcript(transcript_data: FetchedTranscript, format_type: str) -> str:
    """Format transcript data.

    Args:
        transcript_data: Raw transcript data
        format_type: Output format (json, txt, vtt, srt)

    Returns:
        Formatted transcript string
    """
    formatters: dict[str, Formatter] = {
        "json": JSONFormatter(),
        "txt": TextFormatter(),
        "vtt": WebVTTFormatter(),
        "srt": SRTFormatter(),
    }

    formatter = formatters.get(format_type)
    if formatter is None:
        msg = f"Unknown format: {format_type}"
        raise ValueError(msg)

    return formatter.format_transcript(transcript_data)


def download_transcript(video_id: str, output_path: Path | None = None, format_type: str = "json", prefer_auto: bool = False) -> None:
    """Download transcript for a YouTube video.

    Tries to get manually created transcripts first, falls back to auto-generated if needed.

    Args:
        video_id: YouTube video ID
        output_path: Optional output file path. If None, prints to stdout.
        format_type: Output format (json, txt, vtt, srt)
        prefer_auto: If True, prefer auto-generated over manual transcripts
    """
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)

    transcript_obj, transcript_type = select_transcript(transcript_list, prefer_auto)
    transcript_data = transcript_obj.fetch()

    print(f"Using {transcript_type} transcript", file=sys.stderr)

    formatted = format_transcript(transcript_data, format_type)

    if output_path:
        output_path.write_text(formatted)
        print(f"Transcript saved to: {output_path}", file=sys.stderr)
    else:
        print(formatted)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Download YouTube video transcripts")
    parser.add_argument("url", help="YouTube URL or video ID")
    parser.add_argument("-o", "--output", type=Path, help="Output file path (default: stdout)")
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "txt", "vtt", "srt"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--prefer-auto",
        action="store_true",
        help="Prefer auto-generated transcripts over manual ones",
    )

    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url)
        download_transcript(video_id, args.output, args.format, args.prefer_auto)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
