from enum import Enum
from typing import List, Optional, Type

from agno.workflow import Workflow
from workflows.github_release import GitHubReleaseWorkflow


class WorkflowType(Enum):
    GITHUB_RELEASE = "github_release"


def get_available_workflows() -> List[str]:
    """Returns a list of all available workflow IDs."""
    return [workflow.value for workflow in WorkflowType]


def get_workflow_class(
    workflow_id: Optional[WorkflowType] = None,
) -> Type[Workflow]:
    """
    Returns the requested workflow class.

    Args:
        workflow_id: The ID of the workflow to get

    Returns:
        The workflow class requested

    Raises:
        ValueError: If the workflow_id is not found
    """
    if workflow_id == WorkflowType.GITHUB_RELEASE:
        return GitHubReleaseWorkflow

    raise ValueError(f"Workflow: {workflow_id} not found")


def get_workflow_instance(
    workflow_id: Optional[WorkflowType] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Workflow:
    """
    Returns an instance of the requested workflow.

    Args:
        workflow_id: The ID of the workflow to get
        user_id: Optional user ID for the workflow
        session_id: Optional session ID for the workflow

    Returns:
        An instance of the requested workflow

    Raises:
        ValueError: If the workflow_id is not found
    """
    workflow_class = get_workflow_class(workflow_id)
    return workflow_class()
