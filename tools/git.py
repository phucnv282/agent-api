"""Git tool for cloning repositories, including private ones."""

import json
import os
from os import getenv
from pathlib import Path
from tempfile import mkdtemp
from typing import Optional

import git
from agno.tools import Toolkit
from agno.utils.log import log_debug, logger


class GitCloneProgress(git.RemoteProgress):
    """Progress handler for Git clone operations."""

    def update(self, op_code, cur_count, max_count=None, message=""):
        """Update git clone progress."""
        if op_code == 5:
            log_debug("Git clone: Starting copy")
        if op_code == 10:
            log_debug("Git clone: Copy complete")


class GitTools(Toolkit):
    """Git toolkit for cloning repositories."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        clone_repo: bool = True,
        **kwargs,
    ):
        """Initialize the Git toolkit.

        Args:
            access_token: GitHub personal access token for private repositories.
                If not provided, will try to get it from GITHUB_ACCESS_TOKEN environment variable.
            clone_repo: Whether to enable the clone_repository function.
            kwargs: Additional keyword arguments to pass to the Toolkit constructor.
        """
        super().__init__(name="git", **kwargs)

        # GitHub token for private repository access
        self.access_token = access_token or getenv("GITHUB_ACCESS_TOKEN")

        # Register enabled functions
        if clone_repo:
            self.register(self.clone_repository)

    def clone_repository(
        self,
        repo_url: str,
        target_dir: Optional[str] = None,
        branch: Optional[str] = None,
        depth: Optional[int] = None,
    ) -> str:
        """Clone a Git repository to a local directory.

        Args:
            repo_url: URL of the repository to clone (e.g., 'https://github.com/username/repo.git')
            target_dir: Directory to clone the repository to. If not specified, a temporary directory will be used.
            branch: Branch to checkout after cloning. If not specified, the default branch will be used.
            depth: Create a shallow clone with the specified depth. If not specified, a full clone is performed.

        Returns:
            A JSON-formatted string containing information about the cloned repository.
        """
        log_debug(f"Cloning repository: {repo_url}")

        try:
            # Process the repo URL for authentication if needed
            original_url = repo_url  # Store original URL for error reporting
            if self.access_token and "github.com" in repo_url and ("private" in repo_url.lower() or getenv("USE_AUTH_FOR_ALL_REPOS", "false").lower() == "true"):
                # Handle various URL formats
                if repo_url.startswith("https://"):
                    # Format: https://github.com/user/repo.git
                    # Convert to: https://token@github.com/user/repo.git
                    repo_url = repo_url.replace("https://", f"https://{self.access_token}@")
                elif repo_url.startswith("git@"):
                    # Format: git@github.com:user/repo.git
                    # Convert to: https://token@github.com/user/repo.git
                    user_repo = repo_url.split(':', 1)[1]
                    repo_url = f"https://{self.access_token}@github.com/{user_repo}"

            # Create target directory if not specified
            if not target_dir:
                target_dir = mkdtemp(prefix="git_clone_")
            else:
                target_dir = str(Path(target_dir).expanduser().resolve())
                os.makedirs(target_dir, exist_ok=True)

            # Prepare clone options
            clone_kwargs = {
                "url": repo_url,
                "to_path": target_dir,
                "progress": GitCloneProgress(),
            }

            # Add shallow clone if depth is specified
            if depth is not None and depth > 0:
                clone_kwargs["depth"] = depth

            # Add branch if specified
            if branch is not None and branch.strip():
                clone_kwargs["branch"] = branch.strip()

            # Clone the repository
            repo = git.Repo.clone_from(**clone_kwargs)

            # Get repository info
            try:
                default_branch = repo.active_branch.name
            except Exception:
                # Detached HEAD state (could happen with depth=1)
                default_branch = "unknown"

            try:
                remote_url = next(repo.remote().urls)
                # Remove token from URL if it exists
                if self.access_token and self.access_token in remote_url:
                    remote_url = remote_url.replace(f"{self.access_token}@", "")
            except Exception:
                remote_url = repo_url

            # Create response with repository details
            repo_info = {
                "repository": {
                    "url": remote_url,
                    "default_branch": default_branch,
                    "current_branch": repo.active_branch.name if not repo.head.is_detached else "DETACHED_HEAD",
                    "commit": repo.head.commit.hexsha,
                    "commit_message": repo.head.commit.message.strip(),
                },
                "local": {
                    "path": target_dir,
                    "git_dir": str(Path(repo.git_dir).relative_to(target_dir)),
                },
                "success": True,
            }

            return json.dumps(repo_info, indent=2)

        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            # Make sure to provide detailed error info
            error_info = {
                "success": False,
                "error": str(e),
                "repository": repo_url,
            }
            
            if target_dir:
                error_info["target_dir"] = target_dir
                
            # Ensure we return valid JSON even when git command fails
            return json.dumps(error_info, indent=2)
