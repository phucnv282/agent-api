"""Workflow selector module to get the appropriate workflow instance."""

from enum import Enum
from typing import List, Optional

from workflows.git_workflow import GitRepositoryWorkflow


class WorkflowType(Enum):
    """Enum representing the available workflow types."""
    
    GIT_REPOSITORY = "git_repository"


def get_available_workflows() -> List[str]:
    """Returns a list of all available workflow IDs."""
    return [workflow.value for workflow in WorkflowType]


def get_workflow(
    workflow_id: WorkflowType,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    """Get a workflow instance based on the workflow ID.
    
    Args:
        workflow_id: The ID of the workflow to get
        user_id: Optional user ID for the workflow
        session_id: Optional session ID for the workflow
        debug_mode: Whether to enable debug mode
        
    Returns:
        A workflow instance
        
    Raises:
        ValueError: If the workflow ID is not found
    """
    if workflow_id == WorkflowType.GIT_REPOSITORY:
        # Configure workflow with provided parameters
        return GitRepositoryWorkflow(
            session_id=session_id or "git-repository-workflow",
            debug_mode=debug_mode,
        )

    raise ValueError(f"Workflow: {workflow_id} not found")
