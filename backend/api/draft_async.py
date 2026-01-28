
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
    Start player selection asynchronously by invoking this Lambda function itself.
    
    Returns immediately with status "accepted", then invokes the same Lambda
    asynchronously to execute the draft pick. Frontend should poll /status
    endpoint to check completion.
    
    This approach:
    1. Returns 200 immediately (before 29s API Gateway timeout)
    2. Invokes itself asynchronously to execute the draft
    3. Async invocation has 15 min timeout (plenty for draft execution)
    
    Use /drafts/{draft_id}/round/{round}/pick/{pick}/status to check completion.
    """
    logger.info(f"[select_player_async] Received request for {team_name} at R{round} P{pick}")
    
    try:
        # Validate draft exists
        draft = await Draft.get(draft_id.lower())
        if not draft:
            logger.error(f"[select_player_async] Draft {draft_id} not found")
            raise HTTPException(status_code=404, detail="Draft not found")
        
        # Validate the team should be drafting at this pick
        try:
            expected_team = draft.get_team_for_pick(round, pick)
            if expected_team.name.lower() != team_name.lower():
                error_msg = f"Invalid draft order: {team_name} cannot draft at Round {round}, Pick {pick}. Expected: {expected_team.name}"
                logger.error(f"[select_player_async] {error_msg}")
                raise HTTPException(status_code=400, detail=error_msg)
        except ValueError as e:
            logger.error(f"[select_player_async] Invalid pick validation: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        
        team = next((t for t in draft.teams.teams if t.name.lower() == team_name.lower()), None)
        if not team:
            logger.error(f"[select_player_async] Team {team_name} not found in draft")
            raise HTTPException(status_code=404, detail="Team not found in draft")
        
        if draft.is_complete:
            logger.error(f"[select_player_async] Draft is already complete")
            raise HTTPException(status_code=400, detail="Draft is complete")
        
        logger.info(f"[select_player_async] ✓ Validation passed, preparing to invoke Lambda")
        
        # Prepare payload for async invocation
        payload = {
            "action": "execute_draft_pick",
            "draft_id": draft_id,
            "team_name": team_name,
            "round": round,
            "pick": pick
        }
        
        # Get this Lambda's function name from environment
        function_name = os.getenv('WORKER_LAMBDA_FUNCTION_NAME')
        
        if not function_name:
            error_msg = "WORKER_LAMBDA_FUNCTION_NAME not set in environment"
            logger.error(f"[select_player_async] {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        logger.info(f"[select_player_async] 🚀 Invoking Lambda: {function_name}")
        logger.info(f"[select_player_async] Payload: {json.dumps(payload)}")
        
        # Invoke this same Lambda function asynchronously
        try:
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='Event',  # Asynchronous invocation
                Payload=json.dumps(payload)
            )
            
            status_code = response.get('StatusCode', 0)
            logger.info(f"[select_player_async] ✓ Lambda invoked successfully")
            logger.info(f"[select_player_async] Response StatusCode: {status_code}")
            
            if status_code not in [200, 202]:
                error_msg = f"Lambda invocation returned unexpected status: {status_code}"
                logger.error(f"[select_player_async] {error_msg}")
                raise Exception(error_msg)
            
        except Exception as invoke_error:
            logger.error(f"[select_player_async] ✗ Failed to invoke Lambda: {invoke_error}", exc_info=True)
            
            # Check if it's a permissions error
            if 'AccessDeniedException' in str(invoke_error):
                logger.error(f"[select_player_async] PERMISSION ERROR: Lambda cannot invoke itself")
                logger.error(f"[select_player_async] Add permission: aws lambda add-permission --function-name {function_name} --statement-id AllowSelfInvoke --action lambda:InvokeFunction --principal lambda.amazonaws.com")
            
            # Re-raise the error so frontend knows it failed
            raise HTTPException(
                status_code=500,
                detail=f"Failed to invoke Lambda: {str(invoke_error)}"
            )
        
        logger.info(f"[select_player_async] ✓ Returning 'accepted' response to frontend")
        
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
        logger.error(f"[select_player_async] ✗ Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error starting draft: {str(e)}")


@router.get("/drafts/{draft_id}/round/{round}/pick/{pick}/status")
async def get_draft_pick_status(draft_id: str, round: int, pick: int):
    """
    Check the status of a draft pick by looking at the draft history.
    Returns completed status if the pick has been made.
    """
    logger.info(f"[get_draft_pick_status] Checking status for draft {draft_id}, R{round} P{pick}")
    
    try:
        history = await DraftHistory.get(draft_id.lower())
        
        if not history:
            logger.warning(f"[get_draft_pick_status] Draft history not found for {draft_id}")
            return DraftTaskStatus(
                status="not_found",
                message="Draft history not found"
            )
        
        pick_item = next(
            (item for item in history.items if item.round == round and item.pick == pick),
            None
        )
        
        if not pick_item:
            logger.warning(f"[get_draft_pick_status] Pick R{round} P{pick} not found in history")
            return DraftTaskStatus(
                status="not_found",
                message="Draft pick not found"
            )
        
        if pick_item.selection:
            logger.info(f"[get_draft_pick_status] ✓ Pick completed: {pick_item.selection}")
            return DraftTaskStatus(
                status="completed",
                message=f"Drafted {pick_item.selection}",
                current_round=round,
                current_pick=pick,
                player_name=pick_item.selection
            )
        else:
            logger.debug(f"[get_draft_pick_status] Pick still processing for {pick_item.team}")
            return DraftTaskStatus(
                status="processing",
                message=f"Pick in progress for {pick_item.team}",
                current_round=round,
                current_pick=pick
            )
            
    except Exception as e:
        logger.error(f"[get_draft_pick_status] Error checking status: {e}", exc_info=True)
        return DraftTaskStatus(
            status="error",
            message="Error checking status",
            error=str(e)
        )


@router.delete("/drafts/{draft_id}/tasks/cleanup")
async def cleanup_draft_tasks(draft_id: str):
    """
    Cleanup endpoint (for compatibility).
    With the async invocation approach, cleanup happens automatically.
    """
    logger.info(f"[cleanup_draft_tasks] Cleanup requested for draft {draft_id}")
    return {"message": "Cleanup not needed with async invocation approach"}