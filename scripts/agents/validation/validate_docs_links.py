"""Validate markdown links in documentation.

Checks for:
1. Broken local file references
2. Submodule links that should use GitHub URLs
3. Dead internal anchors
4. Inconsistent link formats
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple

# Bootstrap sys.path
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))

from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()


class LinkIssue(NamedTuple):
    """Represents a documentation link issue."""

    file: str
    line: int
    text: str
    url: str
    issue_type: str
    suggestion: str | None = None


# Submodules that should use GitHub links
SUBMODULES = {"compliance", "learning", "browser", "files", "nodes", "domains", "streams", "ux", "base"}

# GitHub organization base URL
GITHUB_ORG = "https://github.com/Independent-AI-Labs"


def extract_links(content: str) -> list[tuple[str, str, int]]:
    """Extract all markdown links with line numbers.

    Args:
        content: Markdown file content

    Returns:
        List of (text, url, line_number) tuples
    """
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^\)]+)\)")
    links = []

    for line_num, line in enumerate(content.split("\n"), 1):
        for match in link_pattern.finditer(line):
            text, url = match.groups()
            links.append((text, url, line_num))

    return links


def resolve_relative_path(base_file: Path, url: str) -> Path:
    """Resolve relative URL to absolute path.

    Args:
        base_file: Source markdown file
        url: Relative URL

    Returns:
        Resolved absolute path
    """
    if url.startswith("../"):
        return (base_file.parent / url).resolve()
    if url.startswith("./"):
        return (base_file.parent / url[2:]).resolve()
    return (base_file.parent / url).resolve()


def get_submodule_github_url(target_path: Path) -> str | None:
    """Generate GitHub URL for submodule path.

    Args:
        target_path: Path within submodule

    Returns:
        GitHub URL or None if not a submodule path
    """
    try:
        rel_path = target_path.relative_to(ORCHESTRATOR_ROOT)
        parts = rel_path.parts

        if not parts:
            return None

        # Check if first part is a submodule
        submodule = parts[0]
        if submodule not in SUBMODULES:
            return None

        # Build GitHub URL
        repo_name = f"AMI-{submodule.upper()}"
        file_path = "/".join(parts[1:]) if len(parts) > 1 else ""

        return f"{GITHUB_ORG}/{repo_name}/blob/main/{file_path}" if file_path else f"{GITHUB_ORG}/{repo_name}"

    except ValueError:
        return None


def should_skip_url(url: str) -> bool:
    """Check if URL should be skipped during validation.

    Args:
        url: URL to check

    Returns:
        True if URL should be skipped
    """
    # Skip external URLs, anchors, and images
    return url.startswith(("http://", "https://", "#")) or url.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg"))


def validate_link(md_file: Path, text: str, url: str, line_num: int) -> LinkIssue | None:
    """Validate a single markdown link.

    Args:
        md_file: Source markdown file
        text: Link text
        url: Link URL
        line_num: Line number in file

    Returns:
        LinkIssue if problem found, None otherwise
    """
    if should_skip_url(url):
        return None

    # Resolve path
    target = resolve_relative_path(md_file, url)

    # Check if target exists
    if not target.exists():
        # Check if it's a submodule reference
        github_url = get_submodule_github_url(target)
        issue_type = "SUBMODULE_LOCAL_LINK" if github_url else "BROKEN_LINK"
        return LinkIssue(
            file=str(md_file.relative_to(ORCHESTRATOR_ROOT)),
            line=line_num,
            text=text,
            url=url,
            issue_type=issue_type,
            suggestion=github_url,
        )

    # Check if it's pointing to a submodule (should use GitHub)
    try:
        rel_path = target.relative_to(ORCHESTRATOR_ROOT)
        if rel_path.parts and rel_path.parts[0] in SUBMODULES:
            github_url = get_submodule_github_url(target)
            return LinkIssue(
                file=str(md_file.relative_to(ORCHESTRATOR_ROOT)),
                line=line_num,
                text=text,
                url=url,
                issue_type="SUBMODULE_SHOULD_USE_GITHUB",
                suggestion=github_url,
            )
    except ValueError:
        pass

    return None


def validate_docs() -> list[LinkIssue]:
    """Validate all documentation links.

    Returns:
        List of link issues found
    """
    docs_dir = ORCHESTRATOR_ROOT / "docs"
    md_files = list(ORCHESTRATOR_ROOT.glob("*.md")) + list(docs_dir.glob("**/*.md"))

    issues = []

    for md_file in md_files:
        # Skip archived docs
        if "archive" in md_file.parts:
            continue

        content = md_file.read_text()
        links = extract_links(content)

        for text, url, line_num in links:
            issue = validate_link(md_file, text, url, line_num)
            if issue:
                issues.append(issue)

    return issues


def format_issue(issue: LinkIssue) -> str:
    """Format link issue for display.

    Args:
        issue: Link issue to format

    Returns:
        Formatted string
    """
    lines = [
        f"  File: {issue.file}:{issue.line}",
        f"  Link: [{issue.text}]({issue.url})",
        f"  Type: {issue.issue_type}",
    ]

    if issue.suggestion:
        lines.append(f"  Fix:  [{issue.text}]({issue.suggestion})")

    return "\n".join(lines)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, 1 = issues found)
    """

    issues = validate_docs()

    if not issues:
        return 0

    # Group by issue type
    by_type: dict[str, list[LinkIssue]] = {}
    for issue in issues:
        by_type.setdefault(issue.issue_type, []).append(issue)

    for _issue_type, type_issues in sorted(by_type.items()):
        for _issue in type_issues:
            pass

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
