from fastapi import HTTPException
from pydantic import BaseModel as PydanticBaseModel
from backend.models.draft import Draft
from backend.models.draft_history import DraftHistory
from backend.models.teams import Team
from fastapi import APIRouter
import logging
import json
import boto3
import os

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize Lambda client
lambda_client = boto3.client('lambda', region_name=os.getenv('AWS_REGION', 'us-east-2'))


class DraftTaskStatus(PydanticBaseModel):
    status: str  # "processing", "completed", "error", "not_found"
    message: str
    current_round: int = None
    current_pick: int = None
    error: str = None
    player_id: int = None
    player_name: str = None


@router.post("/drafts/{draft_id}/teams/{team_name}/round/{round}/pick/{pick}/select-player-async")
async def select_player_async(
    draft_id: str, 
    team_name: str, 
    round: int, 
    pick: int
):
    """
    Start player selection asynchronously by invoking the worker Lambda.
    Returns immediately, actual drafting happens in a separate Lambda invocation.
    
    This approach:
    1. Returns 200 immediately
    2. Invokes mlb-draft-oracle-worker Lambda asynchronously
    3. Worker Lambda runs the MCP agents without time limits
    
    Use /drafts/{draft_id}/round/{round}/pick/{pick}/status to check completion.
    """
    logger.info(f"[select_player_async] Received request for {team_name} at R{round} P{pick}")
    
    try:
        # Validate draft exists
        draft = await Draft.get(draft_id.lower())
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        # Validate the team should be drafting at this pick
        try:
            expected_team = draft.get_team_for_pick(round, pick)
            if expected_team.name.lower() != team_name.lower():
                error_msg = f"Invalid draft order: {team_name} cannot draft at Round {round}, Pick {pick}. Expected: {expected_team.name}"
                logger.error(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
        except ValueError as e:
            logger.error(f"Invalid pick validation: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        
        team = next((t for t in draft.teams.teams if t.name.lower() == team_name.lower()), None)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found in draft")
        
        if draft.is_complete:
            raise HTTPException(status_code=400, detail="Draft is complete")
        
        logger.info(f"[select_player_async] Validation passed, invoking worker Lambda")
        
        # Prepare payload for worker Lambda
        payload = {
            "action": "execute_draft_pick",
            "draft_id": draft_id,
            "team_name": team_name,
            "round": round,
            "pick": pick
        }
        
        # Get Lambda function name from environment or use default
        worker_function_name = os.getenv('WORKER_LAMBDA_NAME', 'mlb-draft-oracle-worker')
        
        # Invoke worker Lambda asynchronously (Event invocation type)
        try:
            response = lambda_client.invoke(
                FunctionName=worker_function_name,
                InvocationType='Event',  # Asynchronous invocation
                Payload=json.dumps(payload)
            )
            
            logger.info(f"[select_player_async] Worker Lambda invoked: {response['StatusCode']}")
            
        except Exception as invoke_error:
            logger.error(f"[select_player_async] Failed to invoke worker Lambda: {invoke_error}")
            
            # Fallback: If we can't invoke worker, log error but still return accepted
            # The status endpoint will show "processing" indefinitely
            logger.warning(f"[select_player_async] Worker invocation failed, draft may not complete")
        
        logger.info(f"[select_player_async] Returning immediately")
        
        return {
            "status": "accepted",
            "message": f"Draft selection started for {team_name}",
            "draft_id": draft_id,
            "team": team_name,
            "round": round,
            "pick": pick,
            "note": "Poll /drafts/{draft_id}/round/{round}/pick/{pick}/status to check completion"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[select_player_async] Error starting async draft: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error starting draft: {str(e)}")


@router.get("/drafts/{draft_id}/round/{round}/pick/{pick}/status")
async def get_draft_pick_status(draft_id: str, round: int, pick: int):
    """
    Check the status of a draft pick by looking at the draft history.
    Returns completed status if the pick has been made.
    """
    try:
        history = await DraftHistory.get(draft_id.lower())
        pick_item = next(
            (item for item in history.items if item.round == round and item.pick == pick),
            None
        )
        
        if not pick_item:
            return DraftTaskStatus(
                status="not_found",
                message="Draft pick not found"
            )
        
        if pick_item.selection:
            return DraftTaskStatus(
                status="completed",
                message=f"Drafted {pick_item.selection}",
                current_round=round,
                current_pick=pick,
                player_name=pick_item.selection
            )
        else:
            return DraftTaskStatus(
                status="processing",
                message=f"Pick in progress for {pick_item.team}",
                current_round=round,
                current_pick=pick
            )
            
    except Exception as e:
        logger.error(f"Error checking draft pick status: {e}", exc_info=True)
        return DraftTaskStatus(
            status="error",
            message="Error checking status",
            error=str(e)
        )


@router.delete("/drafts/{draft_id}/tasks/cleanup")
async def cleanup_draft_tasks(draft_id: str):
    """
    Cleanup endpoint (for compatibility).
    With the new async approach, cleanup happens automatically in the MCP server.
    """
    return {"message": "Cleanup not needed with new async approach"}