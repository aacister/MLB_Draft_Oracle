#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import json

import asyncio
from typing import Dict
import uuid

# ============================================================================
# CRITICAL: Python Path Setup MUST happen before ANY other imports
# ============================================================================
# Get the directory where this script is located
script_dir = Path(__file__).parent.absolute()
# Get the parent directory (should be /var/task in Lambda)
parent_dir = script_dir.parent.absolute()

# Add to Python path
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, os.getcwd())

# For Lambda specifically
if os.path.exists("/var/task"):
    sys.path.insert(0, "/var/task")

# Debug: Print Python path
print(f"Python path for draft_server: {sys.path[:5]}", file=sys.stderr, flush=True)
print(f"Script dir: {script_dir}", file=sys.stderr, flush=True)
print(f"Parent dir: {parent_dir}", file=sys.stderr, flush=True)
print(f"CWD: {os.getcwd()}", file=sys.stderr, flush=True)

# ============================================================================
# Now we can import other modules
# ============================================================================
import logging
import time

# Configure logging
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
    from backend.templates.templates import drafter_instructions
    from mcp.server.fastmcp import FastMCP
    from typing import List
    
    backendmodels_AVAILABLE = True
    logger.info(f"Backend models imported successfully in {time.time() - start_time:.2f}s")
except Exception as e:
    logger.error(f"Failed to import backend models: {e}", exc_info=True)
    backendmodels_AVAILABLE = False
    raise  # Re-raise to see the full error

load_dotenv(override=True, dotenv_path=find_dotenv())

logger = logging.getLogger(__name__)

try:
    models_AVAILABLE = True
    logger.info("All backend models imported successfully - Using PostgreSQL RDS")
except Exception as e:
    logger.error(f"Warning: Could not import backend models: {e}")
    models_AVAILABLE = False
    
mcp = FastMCP(
    name="draft_server",
    instructions=f"""You are a fantasy baseball team in a fantasy baseball draft. You are drafting a player with goal to fill  
    out all the positions on your team roster with best players that align to your team's draft strategy.  Do not draft players for 
    postions on your roster that have already been filled with a player.  Draft only one player per round.
    If the 'draft_specific_player' call fails, retry the call for a different player.
    Keep trying to call synchronously the 'draft_specific_player' tool function call with a different player till a successful call is made.
    Ensure only one successful call is made per round. Do NOT prompt the user with questions.
"""
    )
draft_tasks: Dict[str, dict] = {}

@mcp.tool()
async def draft_specific_player(draft_id, team_name, player_name, round_num, pick_num, rationale) -> str:
    """
    Draft a player for a team in the draft.
    Returns immediately with a task ID, actual drafting happens in background.
    """
    if not backendmodels_AVAILABLE:
        return json.dumps({
            "status": "error",
            "error": "Database models not available",
            "task_id": None
        })
    
    # Generate unique task ID
    task_id = f"draft_{uuid.uuid4().hex[:8]}"
    
    # Store initial status
    draft_tasks[task_id] = {
        "status": "processing",
        "message": f"Starting draft for {player_name}...",
        "player_name": player_name,
        "team_name": team_name,
        "draft_id": draft_id,
        "round": round_num,
        "pick": pick_num
    }
    
    logger.info(f"Task {task_id}: Initiating draft for {player_name}")
    
    # Start background task (non-blocking)
    asyncio.create_task(
        _process_draft_in_background(
            task_id, draft_id, team_name, player_name, 
            round_num, pick_num, rationale
        )
    )
    
    # Return immediately with task ID
    return json.dumps({
        "status": "accepted",
        "task_id": task_id,
        "message": f"Draft initiated for {player_name}",
        "player_name": player_name
    })


async def _process_draft_in_background(
    task_id: str, 
    draft_id: str, 
    team_name: str, 
    player_name: str, 
    round_num: str, 
    pick_num: str, 
    rationale: str
):
    """Background task to actually process the draft"""
    try:
        logger.info(f"Task {task_id}: Processing draft in background")
        
        # Update status
        draft_tasks[task_id]["status"] = "drafting"
        draft_tasks[task_id]["message"] = f"Drafting {player_name}..."
        
        draft = await Draft.get(draft_id)
        if draft == None:
            draft_tasks[task_id] = {
                "status": "error",
                "error": f"Draft {draft_id} does not exist",
                "player_id": None,
                "player_name": player_name
            }
            return
        
        # Ensure player_pool is initialized
        if draft.player_pool is None:
            draft.player_pool = await PlayerPool.get(id=None)
        
        available_players = draft.get_undrafted_players()
        selected_player = next((p for p in available_players if p.name == player_name), None)
        
        if not selected_player:
            logger.warning(f"Task {task_id}: Player {player_name} not found")
            draft_tasks[task_id] = {
                "status": "error",
                "error": f"Player {player_name} not found in available players",
                "player_id": None,
                "player_name": player_name
            }
            return
        
        team = Team.get(team_name)
        round_num = int(round_num)
        pick_num = int(pick_num)
        
        # Actually draft the player
        await draft.draft_player(
            team=team,
            round=round_num,
            pick=pick_num,
            selected_player=selected_player,
            rationale=rationale
        )
        
        logger.info(f"Task {task_id}: ✓ Successfully drafted {player_name}")
        
        # Update to completed status
        draft_tasks[task_id] = {
            "status": "completed",
            "message": f"Successfully drafted {player_name}",
            "player_id": selected_player.id,
            "player_name": selected_player.name,
            "reason": rationale
        }
        
    except Exception as e:
        logger.error(f"Task {task_id}: Error - {e}", exc_info=True)
        draft_tasks[task_id] = {
            "status": "error",
            "error": str(e),
            "player_id": None,
            "player_name": player_name
        }


@mcp.tool()
async def check_draft_status(task_id: str) -> str:
    """
    Check the status of a draft task.
    
    Args:
        task_id: The task ID returned from draft_specific_player
    
    Returns:
        JSON with current status of the draft task
    """
    if task_id not in draft_tasks:
        return json.dumps({
            "status": "not_found",
            "error": f"Task {task_id} not found"
        })
    
    return json.dumps(draft_tasks[task_id])
        

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
    logger.info("Starting MCP draft server with PostgreSQL RDS...")
    mcp.run(transport='stdio')