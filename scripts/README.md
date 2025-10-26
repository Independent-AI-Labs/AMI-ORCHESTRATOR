# Scripts Directory

Automation scripts for the AMI Orchestrator project.

## Git Helper Scripts

### git_commit.sh
Safe git commit wrapper that stages all changes before committing.

```bash
scripts/git_commit.sh <module-path> <commit-message>
scripts/git_commit.sh <module-path> -F <file>
scripts/git_commit.sh <module-path> --amend
```

Examples:
```bash
scripts/git_commit.sh . "fix: update root"
scripts/git_commit.sh base "feat: add new feature"
scripts/git_commit.sh . -F /tmp/commit_msg.txt
```

### git_push.sh
Safe git push wrapper that runs tests before pushing.

```bash
scripts/git_push.sh <module-path> [remote] [branch]
```

Examples:
```bash
scripts/git_push.sh . origin main
scripts/git_push.sh base
```

### git_tag_all.sh
Tags all submodules and root repository with the same version tag, then pushes all tags to remote.

**Note:** This excludes external third-party submodules like `cli-agents/gemini-cli`.

```bash
bash scripts/git_tag_all.sh <version-tag> [message]
```

Examples:
```bash
bash scripts/git_tag_all.sh v1.0.0
bash scripts/git_tag_all.sh v2.1.3 "Release version 2.1.3 with bug fixes"
```

The script will:
1. Validate the tag follows semver format (vX.Y.Z)
2. Create annotated tags in all submodules
3. Tag the root repository
4. Push all tags to their respective remotes
5. Report summary of success/failures

### git_delete_tag_all.sh
Deletes a tag from all submodules and root repository (both local and remote).

**Warning:** This permanently deletes tags from remote repositories.

```bash
bash scripts/git_delete_tag_all.sh <version-tag>
```

Examples:
```bash
bash scripts/git_delete_tag_all.sh v1.0.0-test
bash scripts/git_delete_tag_all.sh v2.0.0-alpha
```

The script will:
1. Delete the tag locally from all submodules and root
2. Delete the tag from all remote repositories
3. Report summary of deletions

## Other Scripts

### ami-run.sh
Universal launcher for Python scripts using the correct virtual environment.

### ami-uv
Wrapper for uv package manager operations.

### ami-agent
Agent CLI wrapper for automation tasks.

### backup_to_gdrive.py
Automated backup utility for Google Drive.

### export_git_history.py
Export git history and statistics.

### toggle_root_protection.sh
Manage branch protection settings for the root repository.
