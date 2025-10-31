"""Git repository operations."""

import os
import shutil
import subprocess
from pathlib import Path

from backend.git_server.results import RepoResult, RepositoryError


class GitRepoOps:
    """Repository management operations."""

    def __init__(self, base_path: Path, repos_path: Path):
        """Initialize repository operations.

        Args:
            base_path: Base git server directory
            repos_path: Repositories directory
        """
        self.base_path = base_path
        self.repos_path = repos_path

    def init_server(self) -> RepoResult:
        """Initialize git server directory structure."""
        readme_path = self.base_path / "README.md"
        if readme_path.exists():
            return RepoResult(
                success=True,
                message="Git server already initialized",
                data={"base_path": str(self.base_path), "repos_path": str(self.repos_path), "already_exists": True},
            )

        self.base_path.mkdir(parents=True, exist_ok=True)
        self.repos_path.mkdir(parents=True, exist_ok=True)

        readme_content = """# Git Repository Server

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
"""
        readme_path.write_text(readme_content)

        return RepoResult(
            success=True,
            message="Git server initialized successfully",
            data={"base_path": str(self.base_path), "repos_path": str(self.repos_path), "readme_path": str(readme_path)},
        )

    def create_repo(self, name: str, description: str | None = None) -> RepoResult:
        """Create a new bare git repository."""
        if not self.repos_path.exists():
            raise RepositoryError("Git server not initialized. Run 'ami-repo init' first.")

        repo_name = name if name.endswith(".git") else f"{name}.git"
        repo_path = self.repos_path / repo_name

        if repo_path.exists():
            raise RepositoryError(f"Repository '{repo_name}' already exists at {repo_path}")

        try:
            subprocess.run(
                ["git", "init", "--bare", str(repo_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RepositoryError(f"Failed to create repository: {e.stderr}") from e

        if description:
            desc_file = repo_path / "description"
            desc_file.write_text(description)

        daemon_export = repo_path / "git-daemon-export-ok"
        daemon_export.touch()

        return RepoResult(
            success=True,
            message="Repository created successfully",
            repo_path=repo_path,
            repo_name=repo_name,
            url=f"file://{repo_path}",
            data={"description": description} if description else None,
        )

    def list_repos(self, verbose: bool = False) -> RepoResult:
        """List all repositories."""
        if not self.repos_path.exists():
            raise RepositoryError("Git server not initialized. Run 'ami-repo init' first.")

        repos = sorted([d for d in self.repos_path.iterdir() if d.is_dir() and d.name.endswith(".git")])

        if not repos:
            return RepoResult(success=True, message="No repositories found", data={"repos": [], "repos_path": str(self.repos_path)})

        repo_list = []
        for repo in repos:
            repo_info = {"name": repo.name, "path": str(repo), "url": f"file://{repo}"}

            if verbose:
                desc_file = repo / "description"
                description = "No description"
                if desc_file.exists():
                    desc_text = desc_file.read_text().strip()
                    if desc_text and desc_text != "Unnamed repository; edit this file 'description' to name the repository.":
                        description = desc_text

                repo_info["description"] = description

                try:
                    result = subprocess.run(
                        ["git", "--git-dir", str(repo), "branch"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    branches = [line.strip().replace("* ", "") for line in result.stdout.strip().split("\n") if line.strip()]
                    branch_info = f"{len(branches)} branch(es)" if branches else "No branches"
                except subprocess.CalledProcessError:
                    branch_info = "Unknown"

                repo_info["branches"] = branch_info

            repo_list.append(repo_info)

        return RepoResult(
            success=True,
            message=f"Found {len(repo_list)} repositor{'y' if len(repo_list) == 1 else 'ies'}",
            data={"repos": repo_list, "repos_path": str(self.repos_path), "verbose": verbose},
        )

    def get_repo_url(self, name: str, protocol: str = "file") -> RepoResult:
        """Get repository URL."""
        if not self.repos_path.exists():
            raise RepositoryError("Git server not initialized. Run 'ami-repo init' first.")

        repo_name = name if name.endswith(".git") else f"{name}.git"
        repo_path = self.repos_path / repo_name

        if not repo_path.exists():
            raise RepositoryError(f"Repository '{repo_name}' not found")

        if protocol == "file":
            url = f"file://{repo_path}"
        elif protocol == "ssh":
            user = os.environ.get("USER", "user")
            host = os.environ.get("HOSTNAME", "localhost")
            url = f"ssh://{user}@{host}{repo_path}"
        else:
            raise RepositoryError(f"Unsupported protocol '{protocol}'. Use: file, ssh")

        return RepoResult(success=True, message="Repository URL retrieved", repo_name=repo_name, url=url, data={"protocol": protocol})

    def clone_repo(self, name: str, destination: Path | None = None) -> RepoResult:
        """Clone a repository."""
        if not self.repos_path.exists():
            raise RepositoryError("Git server not initialized. Run 'ami-repo init' first.")

        repo_name = name if name.endswith(".git") else f"{name}.git"
        repo_path = self.repos_path / repo_name

        if not repo_path.exists():
            raise RepositoryError(f"Repository '{repo_name}' not found")

        destination = Path.cwd() / name.replace(".git", "") if destination is None else Path(destination)

        if destination.exists():
            raise RepositoryError(f"Destination '{destination}' already exists")

        try:
            subprocess.run(
                ["git", "clone", f"file://{repo_path}", str(destination)],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RepositoryError(f"Failed to clone repository: {e}") from e

        return RepoResult(
            success=True, message="Repository cloned successfully", repo_name=repo_name, data={"destination": str(destination), "source": str(repo_path)}
        )

    def delete_repo(self, name: str, confirmed: bool = False) -> RepoResult:
        """Delete a repository.

        Args:
            name: Repository name
            confirmed: If False, returns result indicating confirmation needed
        """
        if not self.repos_path.exists():
            raise RepositoryError("Git server not initialized. Run 'ami-repo init' first.")

        repo_name = name if name.endswith(".git") else f"{name}.git"
        repo_path = self.repos_path / repo_name

        if not repo_path.exists():
            raise RepositoryError(f"Repository '{repo_name}' not found")

        if not confirmed:
            return RepoResult(
                success=False,
                message="Confirmation required",
                repo_name=repo_name,
                data={"requires_confirmation": True, "repo_path": str(repo_path)},
            )

        try:
            shutil.rmtree(repo_path)
        except OSError as e:
            raise RepositoryError(f"Failed to delete repository: {e}") from e

        return RepoResult(success=True, message="Repository deleted successfully", repo_name=repo_name, data={"deleted_path": str(repo_path)})

    def _get_repo_description(self, repo_path: Path) -> str | None:
        """Get repository description if available."""
        desc_file = repo_path / "description"
        if desc_file.exists():
            desc_text = desc_file.read_text().strip()
            if desc_text and desc_text != "Unnamed repository; edit this file 'description' to name the repository.":
                return desc_text
        return None

    def _get_repo_branches(self, repo_path: Path) -> list[str]:
        """Get repository branches."""
        try:
            result = subprocess.run(
                ["git", "--git-dir", str(repo_path), "branch", "-a"],
                capture_output=True,
                text=True,
                check=True,
            )
            branches = result.stdout.strip()
            if branches:
                return branches.split("\n")
        except subprocess.CalledProcessError:
            pass
        return []

    def _get_repo_tags(self, repo_path: Path) -> list[str]:
        """Get repository tags."""
        try:
            result = subprocess.run(
                ["git", "--git-dir", str(repo_path), "tag"],
                capture_output=True,
                text=True,
                check=True,
            )
            tags = result.stdout.strip()
            if tags:
                return tags.split("\n")
        except subprocess.CalledProcessError:
            pass
        return []

    def _get_repo_last_commit(self, repo_path: Path) -> dict[str, str] | None:
        """Get repository last commit information."""
        try:
            result = subprocess.run(
                ["git", "--git-dir", str(repo_path), "log", "-1", "--format=%H%n%an <%ae>%n%ai%n%s"],
                capture_output=True,
                text=True,
                check=True,
            )
            commit_info = result.stdout.strip().split("\n")
            commit_info_fields = 4
            if len(commit_info) >= commit_info_fields:
                return {"hash": commit_info[0], "author": commit_info[1], "date": commit_info[2], "message": commit_info[3]}
        except subprocess.CalledProcessError:
            pass
        return None

    def repo_info(self, name: str) -> RepoResult:
        """Show detailed repository information."""
        if not self.repos_path.exists():
            raise RepositoryError("Git server not initialized. Run 'ami-repo init' first.")

        repo_name = name if name.endswith(".git") else f"{name}.git"
        repo_path = self.repos_path / repo_name

        if not repo_path.exists():
            raise RepositoryError(f"Repository '{repo_name}' not found")

        info_data = {
            "name": repo_name,
            "path": str(repo_path),
            "url": f"file://{repo_path}",
            "description": self._get_repo_description(repo_path),
            "branches": self._get_repo_branches(repo_path),
            "tags": self._get_repo_tags(repo_path),
            "last_commit": self._get_repo_last_commit(repo_path),
        }

        return RepoResult(success=True, message="Repository information retrieved", repo_name=repo_name, repo_path=repo_path, data=info_data)
