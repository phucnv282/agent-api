from enum import Enum
from logging import getLogger
from typing import AsyncGenerator, Dict, List, Optional, Any

from agno.utils.pprint import pprint_run_response
from agno.workflow import RunResponse, Workflow
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from workflows.selector import WorkflowType, get_workflow_instance, get_available_workflows

logger = getLogger(__name__)

######################################################
## Routes for the Workflow Interface
######################################################

workflows_router = APIRouter(prefix="/workflows", tags=["Workflows"])


class Model(str, Enum):
    gpt_4_1 = "gpt-4.1"
    o4_mini = "o4-mini"


@workflows_router.get("", response_model=List[str])
async def list_workflows():
    """
    Returns a list of all available workflow IDs.

    Returns:
        List[str]: List of workflow identifiers
    """
    return get_available_workflows()


async def workflow_response_streamer(workflow: Workflow, params: Dict[str, Any]) -> AsyncGenerator:
    """
    Stream workflow responses chunk by chunk.

    Args:
        workflow: The workflow instance to run
        params: Parameters to pass to the workflow

    Yields:
        Text chunks from the workflow response
    """
    async for chunk in workflow.arun(**params):
        yield chunk.content


class RunWorkflowRequest(BaseModel):
    """Request model for running a workflow"""
    
    parameters: Dict[str, Any] = {}
    stream: bool = True
    model: Model = Model.gpt_4_1
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@workflows_router.post("/{workflow_id}/runs", status_code=status.HTTP_200_OK)
async def create_workflow_run(workflow_id: WorkflowType, body: RunWorkflowRequest):
    """
    Runs a specific workflow with the provided parameters and returns the response.

    Args:
        workflow_id: The ID of the workflow to run
        body: Request parameters including specific workflow parameters

    Returns:
        Either a streaming response or the complete workflow response
    """
    logger.debug(f"RunWorkflowRequest: {body}")

    try:
        workflow: Workflow = get_workflow_instance(
            workflow_id=workflow_id,
            user_id=body.user_id,
            session_id=body.session_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if body.stream:
        return StreamingResponse(
            workflow_response_streamer(workflow, body.parameters),
            media_type="text/event-stream",
        )
    else:
        response_generator = workflow.run(**body.parameters)
        responses = list(response_generator)
        if responses:
            return responses[-1].content
        return ""
