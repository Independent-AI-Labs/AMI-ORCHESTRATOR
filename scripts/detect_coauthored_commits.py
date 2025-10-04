#!/usr/bin/env python3
"""Detect and optionally remove Co-Authored-By from commits across all submodules."""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_coauthored_commits(repo_path: Path) -> list[str]:
    """Get commits with Co-Authored-By in a repository."""
    try:
        result = subprocess.run(
            ["git", "log", "--all", "--grep=Co-Authored-By", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")
        return []
    except Exception as e:
        print(f"Error checking {repo_path}: {e}")
        return []


def remove_coauthored_from_repo(repo_path: Path) -> bool:
    """Remove Co-Authored-By lines from all commits in a repository."""
    print(f"Rewriting history in {repo_path}...")

    # Use git filter-branch to rewrite commit messages
    # This removes lines containing "Co-Authored-By:" and emoji/Claude Code links
    script = """
import sys
import re

message = sys.stdin.buffer.read().decode('utf-8', errors='replace')

# Split into lines for easier processing
lines = message.split('\\n')
filtered_lines = []

for line in lines:
    # Skip lines containing any of these patterns (case insensitive)
    line_lower = line.lower()
    if any(pattern in line_lower for pattern in [
        'co-authored-by',
        'claude code',
        'anthropic.com',
        'anthropic.ai',
        'claude.com',
        'claude.ai',
    ]):
        continue

    # Skip lines that are just emoji/symbols with no real content
    if re.match(r'^[\\s🤖✨🎯🎨]*$', line):
        continue

    filtered_lines.append(line)

# Rejoin lines
message = '\\n'.join(filtered_lines)

# Clean up multiple consecutive blank lines
message = re.sub(r'\\n\\n\\n+', '\\n\\n', message)

# Clean up trailing whitespace
message = message.rstrip() + '\\n'

sys.stdout.buffer.write(message.encode('utf-8'))
"""

    try:
        # Find the actual .git directory (handle submodule gitdir pointers)
        git_path = repo_path / ".git"
        if git_path.is_file():
            # Submodule - read gitdir pointer
            gitdir_content = git_path.read_text().strip()
            if gitdir_content.startswith("gitdir: "):
                git_dir = repo_path / gitdir_content[8:]  # Remove "gitdir: " prefix
            else:
                print(f"Invalid gitdir file in {repo_path}")
                return False
        else:
            git_dir = git_path

        # Write the filter script
        filter_script = git_dir / "filter-msg.py"
        filter_script.write_text(script)

        # Use absolute path for filter script (filter-branch changes cwd)
        filter_script_abs = filter_script.absolute()

        # Run git filter-branch
        result = subprocess.run(
            ["git", "filter-branch", "-f", "--msg-filter", f"python3 {filter_script_abs}", "--", "--all"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "FILTER_BRANCH_SQUELCH_WARNING": "1"},
        )

        # Clean up
        filter_script.unlink()

        if result.returncode != 0:
            print(f"Error rewriting history: {result.stderr}")
            return False

        print(f"Successfully rewrote history in {repo_path}")
        return True

    except Exception as e:
        print(f"Error removing Co-Authored-By from {repo_path}: {e}")
        return False


def force_push_repo(repo_path: Path) -> bool:
    """Force push repository after rewriting history."""
    print(f"Force pushing {repo_path}...")

    try:
        # Get current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()

        if not branch:
            print(f"Not on a branch in {repo_path}, skipping push")
            return True

        # Force push (use --force after history rewrite, not --force-with-lease)
        result = subprocess.run(
            ["git", "push", "--force", "origin", branch],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=1200,  # 20 minute timeout for hooks
        )

        if result.returncode != 0:
            print(f"Error pushing {repo_path}: {result.stderr}")
            return False

        print(f"Successfully pushed {repo_path}")
        return True

    except subprocess.TimeoutExpired:
        print(f"Push timed out for {repo_path}")
        return False
    except Exception as e:
        print(f"Error pushing {repo_path}: {e}")
        return False


def backup_git_directories(repo_root: Path) -> Path:
    """Backup root .git directory (includes all submodules in .git/modules/)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = repo_root / f".git-backup-{timestamp}"
    backup_dir.mkdir()

    print("=" * 60)
    print("BACKING UP .git DIRECTORIES")
    print("=" * 60)
    print()

    # Backup root .git
    print(f"Backing up root .git to {backup_dir}...")
    shutil.copytree(repo_root / ".git", backup_dir / "root.git")

    print(f"\nBackup complete: {backup_dir}")
    print()
    return backup_dir


def restore_git_backups(repo_root: Path, backup_dir: Path) -> None:
    """Restore root .git directory from backup (includes all submodules)."""
    print()
    print("=" * 60)
    print("RESTORING FROM BACKUP")
    print("=" * 60)
    print()

    # Restore root .git (includes all submodules in .git/modules/)
    print("Restoring root .git...")
    if (repo_root / ".git").exists():
        shutil.rmtree(repo_root / ".git")
    shutil.copytree(backup_dir / "root.git", repo_root / ".git")

    print("\nRestore complete")


def delete_backup(backup_dir: Path) -> None:
    """Delete backup directory."""
    print()
    print(f"Deleting backup: {backup_dir}")
    shutil.rmtree(backup_dir)
    print("Backup deleted")


def rewrite_history_phase(repo_root: Path, modules: list[str]) -> bool:
    """Rewrite git history in all repos."""
    print("=" * 60)
    print("REWRITING GIT HISTORY - THIS IS DESTRUCTIVE")
    print("=" * 60)
    print()

    for module in modules:
        module_path = repo_root / module
        if not module_path.exists() or not (module_path / ".git").exists():
            continue
        if not remove_coauthored_from_repo(module_path):
            print(f"Failed to rewrite {module}, aborting")
            return False

    if not remove_coauthored_from_repo(repo_root):
        print("Failed to rewrite root repo, aborting")
        return False

    return True


def commit_changes_phase(repo_root: Path, modules: list[str]) -> None:
    """Stage and commit changes in all repos."""
    print()
    print("=" * 60)
    print("STAGING AND COMMITTING IN ALL REPOSITORIES")
    print("=" * 60)
    print()

    for module in modules:
        module_path = repo_root / module
        if not module_path.exists() or not (module_path / ".git").exists():
            continue

        print(f"Staging changes in {module}...")
        subprocess.run(["git", "add", "-A"], cwd=module_path, check=True)

        result = subprocess.run(
            ["git", "commit", "-m", "chore: remove Co-Authored-By from commit messages"],
            cwd=module_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=1200,
        )
        print(f"Committed changes in {module}" if result.returncode == 0 else f"No changes to commit in {module}")


def push_all_phase(repo_root: Path, modules: list[str]) -> bool:
    """Force push all repos."""
    print()
    print("=" * 60)
    print("FORCE PUSHING ALL REPOSITORIES")
    print("=" * 60)
    print()

    for module in modules:
        module_path = repo_root / module
        if not module_path.exists() or not (module_path / ".git").exists():
            continue
        if not force_push_repo(module_path):
            print(f"Failed to push {module}")
            return False

    print()
    print("Staging changes in root repository...")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)

    result = subprocess.run(
        ["git", "commit", "-m", "chore: remove Co-Authored-By and update submodule pointers"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=1200,
    )
    print("Committed changes in root repository" if result.returncode == 0 else "No changes to commit in root repository")

    if not force_push_repo(repo_root):
        print("Failed to push root repo")
        return False

    return True


def fix_all_repos(repo_root: Path, modules: list[str]) -> int:
    """Fix Co-Authored-By in all repos."""
    # Step 0: Backup .git directories
    backup_dir = backup_git_directories(repo_root)

    try:
        # Rewrite history
        if not rewrite_history_phase(repo_root, modules):
            print("\nHistory rewrite failed, restoring from backup...")
            restore_git_backups(repo_root, backup_dir)
            return 1

        # Commit changes
        commit_changes_phase(repo_root, modules)

        # Push all repos
        if not push_all_phase(repo_root, modules):
            print("\nPush failed, restoring from backup...")
            restore_git_backups(repo_root, backup_dir)
            return 1

        # Success - delete backup
        print()
        print("=" * 60)
        print("HISTORY REWRITE COMPLETE")
        print("=" * 60)
        delete_backup(backup_dir)

        return 0

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Restoring from backup...")
        restore_git_backups(repo_root, backup_dir)
        return 1


def detect_all_repos(repo_root: Path, modules: list[str]) -> int:
    """Detect Co-Authored-By in all repos."""
    print("Scanning for Co-Authored-By commits...")
    print("=" * 40)
    print()

    total_found = 0

    # Check root repo
    print("Checking root repository...")
    commits = get_coauthored_commits(repo_root)
    if commits:
        for commit in commits[:20]:
            print(commit)
        count = len(commits)
        print(f"Found {count} commits with Co-Authored-By in root")
        total_found += count
    print()

    # Check all submodules
    for module in modules:
        module_path = repo_root / module
        if not module_path.exists() or not (module_path / ".git").exists():
            continue

        print(f"Checking {module}...")
        commits = get_coauthored_commits(module_path)
        if commits:
            for commit in commits[:20]:
                print(commit)
            count = len(commits)
            print(f"Found {count} commits with Co-Authored-By in {module}")
            total_found += count
        print()

    print("=" * 40)
    print(f"Total commits with Co-Authored-By: {total_found}")

    if total_found > 0:
        print()
        print("Run with --fix to remove Co-Authored-By lines and force push")
        return 1
    print("No Co-Authored-By commits found!")
    return 0


def fix_single_module(repo_root: Path, module: str | None) -> int:
    """Fix Co-Authored-By in a single module (or root if module is None)."""
    if module:
        module_path = repo_root / module
        if not module_path.exists():
            print(f"Error: Module {module} does not exist")
            return 1
        if not (module_path / ".git").exists():
            print(f"Error: Module {module} is not a git repository")
            return 1
        target_path = module_path
        target_name = module
    else:
        target_path = repo_root
        target_name = "root"

    # Backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = repo_root / f".git-backup-{target_name}-{timestamp}"
    backup_dir.mkdir()

    print("=" * 60)
    print(f"BACKING UP {target_name}")
    print("=" * 60)
    print()

    if module:
        # Backup submodule's .git directory in .git/modules/
        git_path = target_path / ".git"
        if git_path.is_file():
            gitdir_content = git_path.read_text().strip()
            if gitdir_content.startswith("gitdir: "):
                # Path is relative to the submodule directory
                actual_git_dir = target_path / gitdir_content[8:]
                actual_git_dir = actual_git_dir.resolve()
                print(f"Backing up {actual_git_dir} to {backup_dir}...")
                shutil.copytree(actual_git_dir, backup_dir / "module.git")
            else:
                print(f"Invalid gitdir file in {target_path}")
                return 1
        else:
            print(f"Backing up {git_path} to {backup_dir}...")
            shutil.copytree(git_path, backup_dir / "module.git")
    else:
        # Backup root .git
        print(f"Backing up root .git to {backup_dir}...")
        shutil.copytree(repo_root / ".git", backup_dir / "root.git")

    print(f"\nBackup complete: {backup_dir}")
    print()

    # Rewrite history
    print("=" * 60)
    print(f"REWRITING HISTORY IN {target_name}")
    print("=" * 60)
    print()

    if not remove_coauthored_from_repo(target_path):
        print(f"\nHistory rewrite failed for {target_name}")
        print(f"Backup preserved at: {backup_dir}")
        print(f"To restore: rm -rf {target_path / '.git'} && cp -r {backup_dir / 'module.git' if module else backup_dir / 'root.git'} {target_path / '.git'}")
        return 1

    print()
    print("=" * 60)
    print(f"HISTORY REWRITE COMPLETE FOR {target_name}")
    print("=" * 60)
    print()
    print(f"Backup preserved at: {backup_dir}")
    print("To restore if needed:")
    if module:
        print(f"  rm -rf {repo_root}/.git/modules/{module}")
        print(f"  cp -r {backup_dir}/module.git {repo_root}/.git/modules/{module}")
    else:
        print(f"  rm -rf {repo_root}/.git")
        print(f"  cp -r {backup_dir}/root.git {repo_root}/.git")
    print()
    print("To push changes:")
    print(f"  cd {target_path}")
    print("  git push --force origin main")
    print()
    print("To delete backup after successful push:")
    print(f"  rm -rf {backup_dir}")

    return 0


def main() -> int:
    """Scan all repositories for Co-Authored-By commits."""
    parser = argparse.ArgumentParser(description="Detect and optionally remove Co-Authored-By from commits")
    parser.add_argument("--fix", action="store_true", help="Remove Co-Authored-By lines from commits (no push)")
    parser.add_argument("--module", type=str, help="Specific module to fix (base, browser, etc.) or omit for root")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    modules = ["base", "browser", "compliance", "domains", "files", "nodes", "streams", "ux"]

    if args.fix:
        if args.module:
            return fix_single_module(repo_root, args.module)
        return fix_single_module(repo_root, None)
    return detect_all_repos(repo_root, modules)


if __name__ == "__main__":
    sys.exit(main())
