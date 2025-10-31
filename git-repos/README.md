# Git Repository Server

This directory contains bare git repositories for local/remote development.

## Structure

- `repos/` - Bare git repositories

## Usage

```bash
# Create a new repository
ami-repo create <repo-name>

# List all repositories
ami-repo list

# Clone a repository
ami-repo clone <repo-name> [destination]

# Get repository URL
ami-repo url <repo-name>

# Delete a repository
ami-repo delete <repo-name>
```

## SSH Access

To access these repositories via SSH, configure your SSH server to allow access
to this directory and use URLs like:

```
ssh://user@host/path/to/git-repos/repos/repo-name.git
```

For local access, use file:// URLs:

```
file:///path/to/git-repos/repos/repo-name.git
```
