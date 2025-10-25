#!/usr/bin/env python3
"""Export git history grouped by submodule for a given timeframe."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))
from base.scripts.env.paths import find_orchestrator_root

_temp_root = find_orchestrator_root()
if _temp_root is None:
    raise RuntimeError("Unable to locate AMI orchestrator root")
REPO_ROOT: Path = _temp_root

SUBMODULES = [
    "base",
    "browser",
    "compliance",
    "domains",
    "files",
    "nodes",
    "streams",
    "ux",
]

# Constants for git log parsing
MIN_COMMIT_PARTS = 4
MIN_NUMSTAT_PARTS = 2


@dataclass
class Commit:
    """Represents a git commit."""

    hash: str
    date: str
    author: str
    message: str
    files_changed: int
    insertions: int
    deletions: int


def parse_date(date_str: str) -> datetime:
    """Parse date string in DD.MM.YYYY format."""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Expected DD.MM.YYYY") from e


def format_date(dt: datetime) -> str:
    """Format datetime as DD.MM.YYYY."""
    return dt.strftime("%d.%m.%Y")


def parse_numstat(lines: list[str], start_index: int) -> tuple[int, int, int, int]:
    """Parse numstat lines and return (new_index, files_changed, insertions, deletions)."""
    i = start_index
    files_changed = 0
    insertions = 0
    deletions = 0

    while i < len(lines) and lines[i] and "|" not in lines[i]:
        parts = lines[i].split("\t")
        if len(parts) >= MIN_NUMSTAT_PARTS:
            files_changed += 1
            add = parts[0]
            delete = parts[1]
            if add != "-":
                insertions += int(add)
            if delete != "-":
                deletions += int(delete)
        i += 1

    return i, files_changed, insertions, deletions


def get_git_log(repo_path: Path, since: str, until: str) -> list[Commit]:
    """Get git log for a repository between two dates."""
    cmd = [
        "git",
        "-C",
        str(repo_path),
        "log",
        f"--since={since}",
        f"--until={until}",
        "--format=%H|%ai|%an|%s",
        "--numstat",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return []

    commits = []
    lines = result.stdout.strip().split("\n")
    i = 0

    while i < len(lines):
        # Skip empty lines
        if not lines[i]:
            i += 1
            continue

        # Parse commit line (contains |)
        if "|" not in lines[i]:
            i += 1
            continue

        parts = lines[i].split("|", 3)
        if len(parts) < MIN_COMMIT_PARTS:
            i += 1
            continue

        commit_hash, date, author, message = parts
        date = date.split()[0]  # Extract just the date part
        i += 1

        # Skip blank line after commit if present
        if i < len(lines) and not lines[i]:
            i += 1

        # Parse numstat lines (no | in them)
        i, files_changed, insertions, deletions = parse_numstat(lines, i)

        commits.append(
            Commit(
                hash=commit_hash[:8],
                date=date,
                author=author,
                message=message,
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions,
            )
        )

    return commits


def format_commits_markdown(commits: list[Commit]) -> str:
    """Format commits as markdown."""
    if not commits:
        return "_No commits in this period_\n"

    lines = []
    for commit in commits:
        stats = f"+{commit.insertions}/-{commit.deletions}" if commit.insertions or commit.deletions else ""
        stat_str = f" ({commit.files_changed} files, {stats})" if commit.files_changed else ""
        lines.append(f"- **{commit.hash}** ({commit.date}) {commit.message}{stat_str}")
        lines.append(f"  _by {commit.author}_")
        lines.append("")

    return "\n".join(lines)


def generate_report(since: str, until: str) -> str:
    """Generate complete git history report."""
    since_dt = parse_date(since)
    until_dt = parse_date(until)

    # Validate date order
    if since_dt > until_dt:
        raise ValueError(f"Start date {since} is after end date {until}")

    lines = [
        "# Git History Report",
        "",
        f"**Period:** {since} to {until}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]

    # Main repository
    lines.append("## Main Repository (AMI-ORCHESTRATOR)")
    lines.append("")
    main_commits = get_git_log(REPO_ROOT, since, until)
    lines.append(format_commits_markdown(main_commits))
    lines.append("---")
    lines.append("")

    # Submodules
    for submodule in SUBMODULES:
        submodule_path = REPO_ROOT / submodule
        if not submodule_path.exists():
            continue

        lines.append(f"## {submodule.upper()}")
        lines.append("")

        commits = get_git_log(submodule_path, since, until)
        lines.append(format_commits_markdown(commits))
        lines.append("---")
        lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")

    total_commits = len(main_commits)
    total_files = sum(c.files_changed for c in main_commits)
    total_insertions = sum(c.insertions for c in main_commits)
    total_deletions = sum(c.deletions for c in main_commits)

    lines.append("**Main Repository:**")
    lines.append(f"- Commits: {total_commits}")
    lines.append(f"- Files changed: {total_files}")
    lines.append(f"- Lines added: +{total_insertions}")
    lines.append(f"- Lines removed: -{total_deletions}")
    lines.append("")

    for submodule in SUBMODULES:
        submodule_path = REPO_ROOT / submodule
        if not submodule_path.exists():
            continue

        commits = get_git_log(submodule_path, since, until)
        if commits:
            sub_files = sum(c.files_changed for c in commits)
            sub_insertions = sum(c.insertions for c in commits)
            sub_deletions = sum(c.deletions for c in commits)

            lines.append(f"**{submodule.upper()}:**")
            lines.append(f"- Commits: {len(commits)}")
            lines.append(f"- Files changed: {sub_files}")
            lines.append(f"- Lines added: +{sub_insertions}")
            lines.append(f"- Lines removed: -{sub_deletions}")
            lines.append("")

    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "start_date",
        help="Start date in DD.MM.YYYY format",
    )
    parser.add_argument(
        "end_date",
        help="End date in DD.MM.YYYY format",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: docs/progress/START-END/report.md)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Main entry point."""
    args = parse_args(argv)

    try:
        # Validate dates
        parse_date(args.start_date)
        parse_date(args.end_date)

        # Generate report
        report = generate_report(args.start_date, args.end_date)

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            dirname = f"{args.start_date}-{args.end_date}"
            output_path = REPO_ROOT / "docs" / "progress" / dirname / "report.md"

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write report
        output_path.write_text(report, encoding="utf-8")

        print(f"Git history report saved to: {output_path}")
        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
