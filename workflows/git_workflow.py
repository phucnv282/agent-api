"""Git repository workflow module for cloning repositories using GitTools."""

import json
from typing import Dict, Optional, Union

from agno.agent import Agent, RunResponse
from agno.workflow import Workflow
from pydantic import BaseModel, Field

from tools import GitTools


class RepositoryRequest(BaseModel):
    """Input model for the repository cloning workflow."""

    repo_url: str = Field(
        ...,
        description="URL of the repository to clone (e.g., 'https://github.com/username/repo.git')",
    )
    target_dir: Optional[str] = Field(
        None,
        description="Directory to clone the repository to. If not specified, a temporary directory will be used.",
    )
    branch: Optional[str] = Field(
        None,
        description="Branch to checkout after cloning. If not specified, the default branch will be used.",
    )
    depth: Optional[int] = Field(
        None,
        description="Create a shallow clone with the specified depth. If not specified, a full clone is performed.",
    )


class RepositoryLocal(BaseModel):
    """Local repository information."""

    path: str = Field(..., description="Local path to the cloned repository")
    git_dir: str = Field(..., description="Relative path to the Git directory")


class RepositoryInfo(BaseModel):
    """Repository information model."""

    url: str = Field(..., description="URL of the repository")
    default_branch: str = Field(..., description="Default branch of the repository")
    current_branch: str = Field(..., description="Current checked out branch")
    commit: str = Field(..., description="Current commit hash")
    commit_message: str = Field(..., description="Current commit message")


class RepositoryResponse(BaseModel):
    """Response model for the repository cloning workflow."""

    success: bool = Field(..., description="Whether the operation was successful")
    repository: Optional[RepositoryInfo] = Field(None, description="Repository information")
    local: Optional[RepositoryLocal] = Field(None, description="Local repository information")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class GitRepositoryWorkflow(Workflow):
    """Workflow for cloning Git repositories using GitTools."""

    description: str = "Clone a Git repository, including private GitHub repositories."

    # Define the agent that will use the GitTools
    git_agent: Agent = Agent(
        description="Clone a Git repository, including private GitHub repositories.",
        tools=[GitTools()],
        instructions=[
            "You will be provided with repository details to clone.",
            "Use the git.clone_repository tool to clone the repository.",
            "The output needs to follow the RepositoryResponse format exactly.",
            "Return ONLY the raw JSON data from the tool without adding any extra content.",
        ],
        response_model=RepositoryResponse,  # Use the defined model as the expected response format
    )

    def run(
        self,
        repo_url: str,
        target_dir: Optional[str] = None,
        branch: Optional[str] = None,
        depth: Optional[int] = None,
    ) -> RunResponse:
        """Run the Git repository cloning workflow.

        Args:
            repo_url: URL of the repository to clone
            target_dir: Directory to clone the repository to (optional)
            branch: Branch to checkout (optional)
            depth: Create a shallow clone with specified depth (optional)

        Returns:
            RunResponse: Result of the repository cloning operation
        """
        # Prepare the input for the agent
        clone_params = {
            "repo_url": repo_url,
        }
        
        # Add optional parameters if provided
        if target_dir:
            clone_params["target_dir"] = target_dir
        if branch:
            clone_params["branch"] = branch
        if depth is not None:
            clone_params["depth"] = depth

        # Call the git agent to clone the repository
        try:
            # The response will automatically be converted to RepositoryResponse format
            # because we defined the response_model in the agent
            clone_result = self.git_agent.run(
                f"Clone repository: {repo_url} with parameters: {json.dumps(clone_params)}"
            )
            return clone_result
        except Exception as e:
            # Create a properly structured error response
            error_response = RepositoryResponse(
                success=False,
                error=f"Workflow error: {str(e)}",
                repository=None,
                local=None
            )
            return RunResponse(content=error_response)
