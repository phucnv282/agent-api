"""Please install dependencies using:
pip install agno gitpython
"""

import os
from typing import Iterator, AsyncIterator, Optional

import git
from agno.agent import RunResponse
from agno.utils.log import logger
from agno.workflow import Workflow


class GitHubReleaseWorkflow(Workflow):
    description: str = (
        "Clone a GitHub repository to a local directory."
    )

    def clone_repository(self, github_url: str, target_dir: Optional[str] = None, 
                       username: Optional[str] = None, token: Optional[str] = None) -> str:
        """Clone a GitHub repository to a local directory.

        Args:
            github_url (str): URL of the GitHub repository to clone
            target_dir (Optional[str]): Target directory for cloning. If None, a temp directory is used.
            username (Optional[str]): GitHub username for private repository authentication
            token (Optional[str]): GitHub personal access token for private repository authentication

        Returns:
            str: Path to the cloned repository directory
        """
        # Check environment variables for credentials if not provided directly
        username = username or os.environ.get('GITHUB_USERNAME')
        token = token or os.environ.get('GITHUB_TOKEN')
        
        # Prepare authenticated URL if credentials are provided
        clone_url = github_url
        if username and token and clone_url.startswith("https://"):
            # Parse GitHub URL to insert auth credentials
            parts = clone_url.split("//")
            if len(parts) == 2:
                clone_url = f"{parts[0]}//{username}:{token}@{parts[1]}"
                # Don't log the URL with credentials for security
                logger.info(f"Using authenticated URL for cloning")
            else:
                logger.warning(f"Could not parse URL for authentication: {github_url}")
        
        # Extract repo name from URL for creating a default target directory
        repo_name = github_url.split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        # Use provided target_dir or create one based on repo name
        if target_dir is None:
            current_dir = os.getcwd()
            target_dir = os.path.join(current_dir, "cloned_repos", repo_name)

        # Create target directory if it doesn't exist
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)

        # Clone the repository
        logger.info(f"Cloning repository to {target_dir}...")
        try:
            if os.path.exists(target_dir):
                # If directory exists, try to update it
                try:
                    repo = git.Repo(target_dir)
                    origin = repo.remotes.origin
                    
                    # Set credentials for pull if needed
                    if username and token:
                        with repo.git.custom_environment(GIT_USERNAME=username, GIT_PASSWORD=token):
                            origin.pull()
                    else:
                        origin.pull()
                    
                    return target_dir
                except Exception as e:
                    logger.warning(f"Failed to update existing repository: {e}")
                    # If updating fails, remove and clone fresh
                    import shutil
                    shutil.rmtree(target_dir, ignore_errors=True)
                    
            # Clone fresh repository
            git.Repo.clone_from(clone_url, target_dir)
            return target_dir
        except Exception as e:
            error_msg = f"Failed to clone repository: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)



    def run(self, github_url: str, target_dir: Optional[str] = None,
            username: Optional[str] = None, token: Optional[str] = None) -> Iterator[RunResponse]:
        """Clone a GitHub repository to a local directory.

        Args:
            github_url (str): URL of the GitHub repository to clone
            target_dir (Optional[str]): Target directory for cloning. If None, a temp directory is used.
            username (Optional[str]): GitHub username for private repository authentication
            token (Optional[str]): GitHub personal access token for private repository authentication

        Yields:
            Iterator[RunResponse]: Iterator of run responses
        """
        # Clone the repository
        logger.info(f"Cloning GitHub repository: {github_url}")
        yield RunResponse(
            run_id=self.run_id,
            content=f"Starting repository clone for {github_url}..."
        )
        
        try:
            # Clone the repository
            repo_dir = self.clone_repository(github_url, target_dir, username, token)
            yield RunResponse(
                run_id=self.run_id,
                content=f"Repository cloned successfully to {repo_dir}."
            )
        except Exception as e:
            yield RunResponse(
                run_id=self.run_id,
                content=f"Error during repository cloning: {str(e)}"
            )

    async def arun(self, github_url: str, target_dir: Optional[str] = None,
               username: Optional[str] = None, token: Optional[str] = None) -> AsyncIterator[RunResponse]:
        """Asynchronous version of the run method.

        Args:
            github_url (str): URL of the GitHub repository to clone
            target_dir (Optional[str]): Target directory for cloning. If None, a temp directory is used.
            username (Optional[str]): GitHub username for private repository authentication
            token (Optional[str]): GitHub personal access token for private repository authentication

        Returns:
            AsyncIterator[RunResponse]: Async iterator of run responses.
        """
        # Clone the repository
        logger.info(f"Cloning GitHub repository: {github_url}")
        yield RunResponse(
            run_id=self.run_id,
            content=f"Starting repository clone for {github_url}..."
        )
        
        try:
            # Clone the repository
            repo_dir = self.clone_repository(github_url, target_dir, username, token)
            yield RunResponse(
                run_id=self.run_id,
                content=f"Repository cloned successfully to {repo_dir}."
            )
        except Exception as e:
            yield RunResponse(
                run_id=self.run_id,
                content=f"Error during repository cloning: {str(e)}"
            )