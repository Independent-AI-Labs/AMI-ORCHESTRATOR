#!/usr/bin/env python3
"""Fix broken documentation links automatically.

Fixes:
1. Updates submodule links to use GitHub URLs
2. Removes broken links to non-existent files
3. Fixes anchor references
"""

import re
import sys
from pathlib import Path

# Bootstrap sys.path
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))

from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

# GitHub organization base URL
GITHUB_ORG = "https://github.com/Independent-AI-Labs"

# Submodule to GitHub repo mapping
SUBMODULE_REPOS = {
    "compliance": "AMI-COMPLIANCE",
    "learning": "AMI-LEARNING",
    "browser": "AMI-BROWSER",
    "files": "AMI-FILES",
    "nodes": "AMI-NODES",
    "domains": "AMI-DOMAINS",
    "streams": "AMI-STREAMS",
    "ux": "AMI-UX",
    "base": "AMI-BASE",
}

# Known broken links to remove
BROKEN_PATHS_TO_REMOVE = {
    "docs/openami/overview/executive-summary.md",
    "docs/openami/architecture/system-architecture.md",
    "../guides/README.md",
    "../../README.md#mcp-integration",
    "../../README.md#quick-start",
    "../../LICENSE",
    "../openami/architecture/system-architecture.md",
    "./GUIDE-FRAMEWORK.md#real-world-applications",
}

# Anchor fixes
ANCHOR_FIXES = {
    "README.md#mcp-integration": "README.md",
    "README.md#quick-start": "README.md",
}


def convert_submodule_to_github(url: str) -> str | None:
    """Convert submodule path to GitHub URL.

    Args:
        url: Relative path URL

    Returns:
        GitHub URL or None if not a submodule path
    """
    # Handle ../../ style paths
    path_parts = [p for p in url.split("/") if p and p != ".."]

    if not path_parts:
        return None

    # Check if first part is a submodule
    submodule = path_parts[0]
    if submodule not in SUBMODULE_REPOS:
        return None

    # Build GitHub URL
    repo_name = SUBMODULE_REPOS[submodule]
    file_path = "/".join(path_parts[1:]) if len(path_parts) > 1 else ""

    if file_path:
        return f"{GITHUB_ORG}/{repo_name}/blob/main/{file_path}"
    return f"{GITHUB_ORG}/{repo_name}"


def fix_link(url: str) -> str | None:
    """Fix a single link URL.

    Args:
        url: Original URL

    Returns:
        Fixed URL or None to remove the link
    """
    # Skip external URLs
    if url.startswith(("http://", "https://")):
        return url

    # Skip anchors
    if url.startswith("#"):
        return url

    # Skip images
    if url.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
        return url

    # Check if should be removed
    for broken in BROKEN_PATHS_TO_REMOVE:
        if broken in url:
            return None

    # Fix anchors
    for broken_anchor, fixed in ANCHOR_FIXES.items():
        if broken_anchor in url:
            url = url.replace(broken_anchor, fixed)

    # Try to convert to GitHub URL
    github_url = convert_submodule_to_github(url)
    if github_url:
        return github_url

    # Return as-is
    return url


def process_file(file_path: Path) -> bool:
    """Process a single markdown file.

    Args:
        file_path: Path to markdown file

    Returns:
        True if file was modified
    """
    content = file_path.read_text()
    original_content = content

    # Pattern to match markdown links
    link_pattern = re.compile(r"(\[([^\]]+)\]\(([^\)]+)\))")

    def replace_link(match: re.Match[str]) -> str:
        full_match: str = match.group(1)
        text: str = match.group(2)
        url: str = match.group(3)

        fixed_url = fix_link(url)

        if fixed_url is None:
            # Remove the link, keep just the text
            return text
        if fixed_url != url:
            # Update the URL
            return f"[{text}]({fixed_url})"
        # Keep as-is
        return full_match

    content = link_pattern.sub(replace_link, content)

    if content != original_content:
        file_path.write_text(content)
        return True

    return False


def main() -> int:
    """Main entry point.

    Returns:
        Exit code
    """
    print("Fixing documentation links...")
    print()

    docs_dir = ORCHESTRATOR_ROOT / "docs"
    md_files = list(ORCHESTRATOR_ROOT.glob("*.md")) + list(docs_dir.glob("**/*.md"))

    # Skip archived docs
    md_files = [f for f in md_files if "archive" not in f.parts]

    modified = []
    for md_file in md_files:
        if process_file(md_file):
            modified.append(str(md_file.relative_to(ORCHESTRATOR_ROOT)))

    if modified:
        print(f"✓ Fixed links in {len(modified)} files:")
        for file_path in sorted(modified):
            print(f"  - {file_path}")
        return 0

    print("No files needed fixing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
