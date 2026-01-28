#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import json
import asyncio
from typing import Dict
import uuid
import logging
import time

# ============================================================================
# CRITICAL: Python Path Setup MUST happen before ANY other imports
# ============================================================================
script_dir = Path(__file__).parent.absolute()
parent_dir = script_dir.parent.absolute()

sys.path.insert(0, str(parent_dir))
sys.path.insert(0, os.getcwd())

if os.path.exists("/var/task"):
    sys.path.insert(0, "/var/task")

print(f"Python path for draft_server: {sys.path[:5]}", file=sys.stderr, flush=True)
print(f"Script dir: {script_dir}", file=sys.stderr, flush=True)
print(f"Parent dir: {parent_dir}", file=sys.stderr, flush=True)
print(f"CWD: {os.getcwd()}", file=sys.stderr, flush=True)

# ============================================================================
# Now we can import other modules
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

start_time = time.time()

logger.info("=== MCP Draft Server Starting ===")
logger.info(f"Python path configured in {time.time() - start_time:.2f}s")

from dotenv import load_dotenv, find_dotenv
load_dotenv(override=True, dotenv_path=find_dotenv())
logger.info(f"Environment loaded in {time.time() - start_time:.2f}s")

# Import backend modules
try:
    from backend.models.draft import Draft
    from backend.models.teams import Team
    from backend.models.draft_history import DraftHistory
    from backend.models.draft_selection_data import DraftSelectionData
    from backend.models.player_pool import PlayerPool
    from backend.models.draft_task import DraftTask
    from backend.templates.templates import drafter_instructions
    from mcp.server.fastmcp import FastMCP
    from typing import List
    
    models_AVAILABLE = True
    logger.info(f"Backend models imported successfully in {time.time() - start_time:.2f}s")
except Exception as e:
    logger.error(f"Failed to import backend models: {e}", exc_info=True)
    models_AVAILABLE = False
    raise

load_dotenv(override=True, dotenv_path=find_dotenv())

mcp = FastMCP(
    name="draft_server",
    instructions=drafter_instructions()
)


@mcp.tool()
async def draft_specific_player(draft_id, team_name, player_name, round_num, pick_num, rationale) -> str:
    """
    Draft a player for a team (synchronous - waits for completion).
    """
    if not models_AVAILABLE:
        return json.dumps({"status": "error", "error": "Database models not available"})
    
    task_id = f"draft_{uuid.uuid4().hex[:8]}"
    
    try:
        # Create task in database
        task = DraftTask.create(
            task_id=task_id,
            draft_id=draft_id,
            team_name=team_name,
            player_name=player_name,
            round=int(round_num),
            pick=int(pick_num)
        )
        
        logger.info(f"✓ Task {task_id} created for {player_name}")
        
        # ✅ FIX: Run synchronously instead of background task
        task.update_status("drafting", f"Drafting {player_name}...")
        
        # Load draft
        draft = await Draft.get(draft_id)
        if not draft:
            task.mark_error(f"Draft {draft_id} not found")
            return json.dumps(task.model_dump(by_alias=True))
        
        # Ensure player_pool
        if draft.player_pool is None:
            draft.player_pool = await PlayerPool.get(id=None)
        
        available_players = draft.get_undrafted_players()
        selected_player = next((p for p in available_players if p.name == player_name), None)
        
        if not selected_player:
            task.mark_error(f"Player {player_name} not found")
            return json.dumps(task.model_dump(by_alias=True))
        
        team = Team.get(team_name)
        
        # Actually draft the player
        logger.info(f"Task {task_id}: Drafting {player_name}...")
        await draft.draft_player(
            team=team,
            round=int(round_num),
            pick=int(pick_num),
            selected_player=selected_player,
            rationale=rationale
        )
        
        logger.info(f"Task {task_id}: ✓ Successfully drafted {player_name}")
        
        # Mark as completed
        task.mark_completed(
            player_id=selected_player.id,
            player_name=selected_player.name,
            reason=rationale
        )
        
        logger.info(f"Task {task_id}: ✓ Marked as completed")
        
        return json.dumps(task.model_dump(by_alias=True))
        
    except Exception as e:
        logger.error(f"Task {task_id}: Error - {e}", exc_info=True)
        task = DraftTask.get(task_id)
        if task:
            task.mark_error(str(e))
            return json.dumps(task.model_dump(by_alias=True))
        return json.dumps({"status": "error", "error": str(e), "task_id": task_id})

@mcp.tool()
async def check_draft_status(task_id: str) -> str:
    """
    Check the status of a draft task.
    
    Args:
        task_id: The task ID returned from draft_specific_player
    
    Returns:
        JSON with current status of the draft task
    """
    logger.info(f"Checking status for task_id: {task_id}")
    
    # Load task from database
    task = DraftTask.get(task_id)
    
    if not task:
        logger.warning(f"Task {task_id} not found in database")
        return json.dumps({
            "status": "not_found",
            "error": f"Task {task_id} not found"
        })
    
    logger.info(f"Task {task_id} status: {task.status}")
    
    # Return task data as JSON
    return json.dumps(task.model_dump(by_alias=True))


@mcp.resource("draft://player_pool/{id}")
async def read_draft_player_pool_resource(id: str) -> str:
    if not models_AVAILABLE:
        return "Error: Database models not available."
    draft = await Draft.get(id.lower())
    return draft.get_draft_player_pool()


@mcp.resource("draft://player_pool/{id}/available")
async def read_draft_player_pool_available_resource(id: str) -> str:
    if not models_AVAILABLE:
        return "Error: Database models not available."
    draft = await Draft.get(id.lower())
    return draft.get_undrafted_players()


@mcp.resource("draft://team_roster/{id}/{team_name}")
async def read_draft_team_roster_resource(id: str, team_name: str) -> str:
    if not models_AVAILABLE:
        return "Error: Database models not available."
    logger.info(f"Reading team roster for {team_name} in draft {id} from PostgreSQL RDS")
    draft = await Draft.get(id.lower())
    return draft.get_team_roster(team_name)


@mcp.resource("draft://draft_order/{id}/round/{round}")
async def get_draft_order(id: str, round: int) -> List[Team]:
    if not models_AVAILABLE:
        return []
    draft = await Draft.get(id.lower())
    return draft.get_draft_order(round)


@mcp.resource("draft://history/{id}")
async def read_draft_history_resource(id: str) -> str:
    if not models_AVAILABLE:
        return "Error: Database models not available."
    draft = await Draft.get(id.lower())
    return await DraftHistory.get(draft.id)


if __name__ == "__main__":
    logger.info("Starting MCP draft server with PostgreSQL RDS task storage...")
    mcp.run(transport='stdio')