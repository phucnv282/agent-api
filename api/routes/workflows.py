"""API routes for workflows."""

import json
from enum import Enum
from logging import getLogger
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, root_validator

from workflows import WorkflowType, get_available_workflows, get_workflow

logger = getLogger(__name__)

######################################################
## Routes for the Workflow Interface
######################################################

workflows_router = APIRouter(prefix="/workflows", tags=["Workflows"])


@workflows_router.get("", response_model=List[str])
async def list_workflows():
    """
    Returns a list of all available workflow IDs.

    Returns:
        List[str]: List of workflow identifiers
    """
    return get_available_workflows()


######################################################
## Base Models for Workflow Requests
######################################################

class WorkflowRunRequest(BaseModel):
    """Base request model for running any workflow."""
    
    user_id: Optional[str] = Field(
        None,
        description="User ID for tracking and permissions",
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for workflow tracking",
    )
    parameters: Dict[str, Any] = Field(
        {},
        description="Workflow-specific parameters needed for execution",
    )


class WorkflowRunResponse(BaseModel):
    """Response model for workflow run results."""
    
    status: str = Field(..., description="Status of the operation")
    data: Any = Field(..., description="Workflow execution result data")


######################################################
## Workflow-Specific Request Validators
######################################################

class GitCloneParameters(BaseModel):
    """Parameters for Git repository cloning workflow."""
    
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


def validate_git_repository_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate parameters for the Git repository workflow.
    
    Args:
        parameters: The parameters to validate
        
    Returns:
        Validated parameters dictionary
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        validated = GitCloneParameters(**parameters)
        return validated.dict()
    except Exception as e:
        logger.error(f"Invalid parameters for Git repository workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameters for Git repository workflow: {str(e)}"
        )


# Add more validator functions for other workflow types as needed


######################################################
## General Workflow Execution Endpoint
######################################################

@workflows_router.post(
    "/{workflow_id}/runs",
    response_model=WorkflowRunResponse,
    summary="Run a workflow",
    description="Execute a workflow with the specified parameters.",
)
async def run_workflow(workflow_id: str, request: WorkflowRunRequest):
    """
    Execute a workflow with the provided parameters.
    
    Args:
        workflow_id: ID of the workflow to run
        request: Parameters for the workflow execution
        
    Returns:
        Result of the workflow execution
    """
    try:
        # Convert string workflow_id to enum
        try:
            workflow_type = WorkflowType(workflow_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_id}' not found"
            )
        
        # Get the workflow instance using the selector
        workflow = get_workflow(
            workflow_id=workflow_type,
            user_id=request.user_id,
            session_id=request.session_id,
        )
    except ValueError as e:
        logger.error(f"Error getting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    try:
        # Validate and prepare parameters based on the workflow type
        params = {}
        
        if workflow_type == WorkflowType.GIT_REPOSITORY:
            validated_params = validate_git_repository_parameters(request.parameters)
            params = validated_params
        else:
            # Future workflow types can be handled here
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported workflow type: {workflow_id}"
            )
        
        # Run the workflow with the validated parameters
        result = workflow.run(**params)
        
        # Process the result content
        if result and result.content:
            # With response_model, the content will be a properly structured object
            # We just need to convert it to a dict for the API response
            if hasattr(result.content, "model_dump"):
                # If it's a Pydantic model (v2+)
                response_data = result.content.model_dump()
            elif hasattr(result.content, "dict"):
                # If it's a Pydantic model (v1)
                response_data = result.content.dict()
            else:
                # Direct conversion
                response_data = result.content
                
            return {
                "status": "success",
                "data": response_data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Workflow returned empty result"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error running workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error executing workflow: {str(e)}"
        )


######################################################
## Example Usage
######################################################

# Example for Git Repository Workflow:
# POST /workflows/git_repository/runs
# {
#     "parameters": {
#         "repo_url": "https://github.com/username/repo.git",
#         "branch": "main",
#         "depth": 1
#     },
#     "user_id": "user-123",
#     "session_id": "session-456"
# }
#
# For future workflows, add their parameters in the "parameters" field
