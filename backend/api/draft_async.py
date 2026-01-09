from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel as PydanticBaseModel
from backend.models.draft import Draft
from backend.models.draft_history import DraftHistory
from backend.models.teams import Team
from fastapi import APIRouter
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# Store for tracking async draft tasks
draft_tasks = {}

class DraftTaskStatus(PydanticBaseModel):
    status: str  # "processing", "completed", "error"
    message: str
    current_round: int = None
    current_pick: int = None
    error: str = None

@router.post("/drafts/{draft_id}/teams/{team_name}/round/{round}/pick/{pick}/select-player-async")
async def select_player_async(
    draft_id: str, 
    team_name: str, 
    round: int, 
    pick: int,
    background_tasks: BackgroundTasks
):
    """Start player selection asynchronously"""
    logger.info(f"Starting async draft for {team_name} at R{round} P{pick}")
    
    # Create task ID
    task_id = f"{draft_id}-{round}-{pick}"
    
    # Initialize task status
    draft_tasks[task_id] = DraftTaskStatus(
        status="processing",
        message=f"Drafting for {team_name}...",
        current_round=round,
        current_pick=pick
    )
    
    # Start background task
    background_tasks.add_task(
        process_draft_pick,
        draft_id,
        team_name,
        round,
        pick,
        task_id
    )
    
    return {
        "status": "accepted",
        "message": f"Draft selection started for {team_name}",
        "task_id": task_id,
        "draft_id": draft_id,
        "round": round,
        "pick": pick
    }

@router.get("/drafts/{draft_id}/round/{round}/pick/{pick}/status")
async def get_draft_pick_status(draft_id: str, round: int, pick: int):
    """Check the status of a draft pick"""
    task_id = f"{draft_id}-{round}-{pick}"
    
    if task_id not in draft_tasks:
        # If task not found, check if pick has been completed
        try:
            history = await DraftHistory.get(draft_id.lower())
            pick_item = next(
                (item for item in history.items if item.round == round and item.pick == pick),
                None
            )
            
            if pick_item and pick_item.selection:
                return DraftTaskStatus(
                    status="completed",
                    message=f"Drafted {pick_item.selection}",
                    current_round=round,
                    current_pick=pick
                )
        except Exception:
            pass
        
        return DraftTaskStatus(
            status="not_found",
            message="Draft pick not found or not started"
        )
    
    return draft_tasks[task_id]

async def process_draft_pick(
    draft_id: str,
    team_name: str,
    round: int,
    pick: int,
    task_id: str
):
    """Background task to process a draft pick"""
    try:
        logger.info(f"Processing draft pick: {task_id}")
        
        # Load draft
        draft = await Draft.get(draft_id.lower())
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        # Validate team
        expected_team = draft.get_team_for_pick(round, pick)
        if expected_team.name.lower() != team_name.lower():
            raise ValueError(
                f"Invalid draft order: {team_name} cannot draft at R{round} P{pick}. "
                f"Expected: {expected_team.name}"
            )
        
        team = next(
            (t for t in draft.teams.teams if t.name.lower() == team_name.lower()),
            None
        )
        if not team:
            raise ValueError(f"Team {team_name} not found")
        
        # Update status
        draft_tasks[task_id] = DraftTaskStatus(
            status="processing",
            message=f"{team_name} is selecting...",
            current_round=round,
            current_pick=pick
        )
        
        # Execute the draft pick
        await team.select_player(draft, round, pick)
        
        # Get the drafted player from history
        history = await DraftHistory.get(draft_id.lower())
        pick_item = next(
            (item for item in history.items if item.round == round and item.pick == pick),
            None
        )
        
        # Update to completed
        draft_tasks[task_id] = DraftTaskStatus(
            status="completed",
            message=f"Drafted {pick_item.selection if pick_item else 'player'}",
            current_round=round,
            current_pick=pick
        )
        
        logger.info(f"Successfully completed draft pick: {task_id}")
        
    except Exception as e:
        logger.error(f"Error processing draft pick {task_id}: {e}", exc_info=True)
        draft_tasks[task_id] = DraftTaskStatus(
            status="error",
            message="Draft pick failed",
            current_round=round,
            current_pick=pick,
            error=str(e)
        )

@router.delete("/drafts/{draft_id}/tasks/cleanup")
async def cleanup_draft_tasks(draft_id: str):
    """Clean up completed/errored tasks for a draft"""
    removed = 0
    for task_id in list(draft_tasks.keys()):
        if task_id.startswith(draft_id) and draft_tasks[task_id].status in ["completed", "error"]:
            del draft_tasks[task_id]
            removed += 1
    
    return {"message": f"Cleaned up {removed} tasks"}