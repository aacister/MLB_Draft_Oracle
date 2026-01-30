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

from dotenv import load_dotenv, find_dotenv
load_dotenv(override=True, dotenv_path=find_dotenv())

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
    
    models_AVAILABLE = True
    logger.info(f"Backend models imported successfully in {time.time() - start_time:.2f}s")
except Exception as e:
    logger.error(f"Failed to import backend models: {e}", exc_info=True)
    models_AVAILABLE = False
    raise

mcp = FastMCP(
    name="draft_server",
    instructions=drafter_instructions()
)


@mcp.tool()
async def draft_specific_player(draft_id, team_name, player_name, round_num, pick_num, rationale) -> str:
    """
    Draft a player for a team (synchronous - waits for completion).
    
    This is the CRITICAL function that updates the draft history in PostgreSQL.
    When this completes successfully, the status endpoint should return "completed".
    """
    if not models_AVAILABLE:
        error_msg = "Database models not available"
        logger.error(f"[draft_specific_player] {error_msg}")
        return json.dumps({"status": "error", "error": error_msg})
    
    logger.info(f"[draft_specific_player] ===== STARTING =====")
    logger.info(f"[draft_specific_player] Draft: {draft_id}")
    logger.info(f"[draft_specific_player] Team: {team_name}")
    logger.info(f"[draft_specific_player] Player: {player_name}")
    logger.info(f"[draft_specific_player] Round: {round_num}, Pick: {pick_num}")
    logger.info(f"[draft_specific_player] Rationale: {rationale}")
    
    try:
        # Load draft
        logger.info(f"[draft_specific_player] Loading draft from PostgreSQL...")
        draft = await Draft.get(draft_id)
        if not draft:
            error_msg = f"Draft {draft_id} not found"
            logger.error(f"[draft_specific_player] {error_msg}")
            return json.dumps({"status": "error", "error": error_msg})
        
        logger.info(f"[draft_specific_player] ✓ Draft loaded")
        
        # Ensure player_pool
        if draft.player_pool is None:
            logger.info(f"[draft_specific_player] Loading player pool...")
            draft.player_pool = await PlayerPool.get(id=None)
            logger.info(f"[draft_specific_player] ✓ Player pool loaded")
        
        # Get available players
        available_players = draft.get_undrafted_players()
        logger.info(f"[draft_specific_player] Available players: {len(available_players)}")
        
        # Find the player
        selected_player = next((p for p in available_players if p.name == player_name), None)
        
        if not selected_player:
            error_msg = f"Player '{player_name}' not found in available players"
            logger.error(f"[draft_specific_player] {error_msg}")
            
            # Get ALL available player names
            available_names = [p.name for p in available_players]
            logger.error(f"[draft_specific_player] Total available players: {len(available_names)}")
            logger.error(f"[draft_specific_player] First 20 available: {available_names[:20]}")
            
            # Try to find similar names (helpful for debugging)
            from difflib import get_close_matches
            close_matches = get_close_matches(player_name, available_names, n=5, cutoff=0.6)
            
            if close_matches:
                suggestion = f"Did you mean one of these? {', '.join(close_matches[:3])}"
                error_msg = f"{error_msg}. {suggestion}"
                logger.error(f"[draft_specific_player] Close matches found: {close_matches}")
            else:
                error_msg = f"{error_msg}. No similar names found in pool."
            
            # Return error with helpful context
            return json.dumps({
                "status": "error", 
                "error": error_msg,
                "player_attempted": player_name,
                "suggestion": close_matches[0] if close_matches else None,
                "available_count": len(available_names)
            })
        
        logger.info(f"[draft_specific_player] ✓ Found player: {selected_player.name} (ID: {selected_player.id})")
        
        # Get team
        team = Team.get(team_name)
        logger.info(f"[draft_specific_player] ✓ Team loaded: {team.name}")
        
        # Actually draft the player - THIS UPDATES DRAFT HISTORY
        logger.info(f"[draft_specific_player] 🚀 Calling draft.draft_player()...")
        result = await draft.draft_player(
            team=team,
            round=int(round_num),
            pick=int(pick_num),
            selected_player=selected_player,
            rationale=rationale
        )
        
        logger.info(f"[draft_specific_player] ✓ draft.draft_player() completed")
        logger.info(f"[draft_specific_player] Result: {result}")
        
        # Verify draft history was updated
        logger.info(f"[draft_specific_player] Verifying draft history update...")
        history = await DraftHistory.get(draft_id.lower())
        pick_item = next(
            (item for item in history.items if item.round == int(round_num) and item.pick == int(pick_num)),
            None
        )
        
        if pick_item and pick_item.selection:
            logger.info(f"[draft_specific_player] ✓✓✓ VERIFIED: Draft history shows {pick_item.selection}")
        else:
            logger.error(f"[draft_specific_player] ✗✗✗ WARNING: Draft history NOT updated!")
        
        logger.info(f"[draft_specific_player] ===== SUCCESS =====")
        
        # Return success
        return json.dumps({
            "status": "completed",
            "player_id": selected_player.id,
            "player_name": selected_player.name,
            "round": int(round_num),
            "pick": int(pick_num),
            "rationale": rationale
        })
        
    except Exception as e:
        error_msg = f"Error drafting player: {str(e)}"
        logger.error(f"[draft_specific_player] ===== ERROR =====")
        logger.error(f"[draft_specific_player] {error_msg}", exc_info=True)
        return json.dumps({"status": "error", "error": error_msg})


@mcp.resource("draft://player_pool/{id}")
async def read_draft_player_pool_resource(id: str) -> str:
    """Get the full player pool for a draft (returns JSON string)"""
    if not models_AVAILABLE:
        return json.dumps({"error": "Database models not available"})
    
    try:
        logger.info(f"[read_draft_player_pool_resource] Reading player pool for draft {id}")
        draft = await Draft.get(id.lower())
        
        if not draft:
            logger.error(f"[read_draft_player_pool_resource] Draft {id} not found")
            return json.dumps({"error": f"Draft {id} not found"})
        
        player_pool_data = draft.get_draft_player_pool()
        
        # Ensure we return valid JSON
        if isinstance(player_pool_data, str):
            try:
                json.loads(player_pool_data)  # Validate
                logger.info(f"[read_draft_player_pool_resource] ✓ Returning player pool JSON string")
                return player_pool_data
            except json.JSONDecodeError:
                logger.error(f"[read_draft_player_pool_resource] Invalid JSON from get_draft_player_pool")
                return json.dumps({"error": "Invalid player pool data"})
        else:
            logger.info(f"[read_draft_player_pool_resource] ✓ Converting player pool to JSON")
            return json.dumps(player_pool_data)
            
    except Exception as e:
        logger.error(f"[read_draft_player_pool_resource] Error: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.resource("draft://player_pool/{id}/available")
async def read_draft_player_pool_available_resource(id: str) -> str:
    """Get available (undrafted) players for a draft (returns JSON string)"""
    if not models_AVAILABLE:
        return json.dumps({"error": "Database models not available"})
    
    try:
        logger.info(f"[read_draft_player_pool_available_resource] Reading available players for draft {id}")
        draft = await Draft.get(id.lower())
        
        if not draft:
            logger.error(f"[read_draft_player_pool_available_resource] Draft {id} not found")
            return json.dumps({"error": f"Draft {id} not found"})
        
        # Get player pool
        player_pool = draft.player_pool
        if not player_pool:
            logger.error(f"[read_draft_player_pool_available_resource] Draft {id} has no player pool")
            return json.dumps({"error": f"Draft {id} has no player pool"})
        
        logger.info(f"[read_draft_player_pool_available_resource] Player pool ID: {player_pool.id}")
        
        # Import Player model (adjust import based on your structure)
        from backend.models.player import Player  # or wherever your Player model is
        
        # Query all players for this player pool that aren't drafted
        available_players = await Player.filter(
            player_pool_id=player_pool.id,
            is_drafted=False
        ).all()
        
        logger.info(f"[read_draft_player_pool_available_resource] Found {len(available_players)} available players")
        
        # Convert to JSON
        players_data = []
        for p in available_players:
            player_dict = {
                "id": p.id,
                "name": p.name,
                "position": p.position,
                "team": p.team,
            }
            if hasattr(p, 'stats') and p.stats:
                player_dict["stats"] = p.stats
            players_data.append(player_dict)
        
        logger.info(f"[read_draft_player_pool_available_resource] ✓ Sample: {[p['name'] for p in players_data[:5]]}")
        
        return json.dumps(players_data)
                
    except Exception as e:
        logger.error(f"[read_draft_player_pool_available_resource] Error: {e}", exc_info=True)
        return json.dumps({"error": str(e)})

@mcp.resource("draft://team_roster/{id}/{team_name}")
async def read_draft_team_roster_resource(id: str, team_name: str) -> str:
    """Get the roster for a specific team in a draft (returns JSON string)"""
    if not models_AVAILABLE:
        return json.dumps({"error": "Database models not available"})
    
    try:
        logger.info(f"[read_draft_team_roster_resource] Reading roster for {team_name} in draft {id}")
        draft = await Draft.get(id.lower())
        
        if not draft:
            logger.error(f"[read_draft_team_roster_resource] Draft {id} not found")
            return json.dumps({"error": f"Draft {id} not found"})
        
        roster_data = draft.get_team_roster(team_name)
        
        # Ensure we return valid JSON
        if isinstance(roster_data, str):
            # If it's already a JSON string, validate it
            try:
                json.loads(roster_data)  # Validate
                logger.info(f"[read_draft_team_roster_resource] ✓ Returning roster JSON string")
                return roster_data
            except json.JSONDecodeError:
                logger.error(f"[read_draft_team_roster_resource] Invalid JSON from get_team_roster: {roster_data[:100]}")
                return json.dumps({"error": "Invalid roster data", "raw": str(roster_data)[:200]})
        else:
            # If it's a dict or list, convert to JSON
            logger.info(f"[read_draft_team_roster_resource] ✓ Converting roster to JSON")
            return json.dumps(roster_data)
            
    except Exception as e:
        logger.error(f"[read_draft_team_roster_resource] Error: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.resource("draft://draft_order/{id}/round/{round}")
async def get_draft_order(id: str, round: int) -> str:
    """Get the draft order for a specific round (returns JSON string)"""
    if not models_AVAILABLE:
        return json.dumps({"error": "Database models not available"})
    
    try:
        logger.info(f"[get_draft_order] Reading draft order for draft {id}, round {round}")
        draft = await Draft.get(id.lower())
        
        if not draft:
            logger.error(f"[get_draft_order] Draft {id} not found")
            return json.dumps({"error": f"Draft {id} not found"})
        
        draft_order = draft.get_draft_order(int(round))
        
        # Convert Team objects to JSON-serializable dicts
        if isinstance(draft_order, list):
            teams_data = [
                {
                    "name": t.name if hasattr(t, 'name') else str(t),
                    "strategy": t.strategy if hasattr(t, 'strategy') else None,
                }
                for t in draft_order
            ]
            logger.info(f"[get_draft_order] ✓ Returning {len(teams_data)} teams")
            return json.dumps(teams_data)
        else:
            return json.dumps(draft_order, default=str)
            
    except Exception as e:
        logger.error(f"[get_draft_order] Error: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.resource("draft://history/{id}")
async def read_draft_history_resource(id: str) -> str:
    """Get the draft history (returns JSON string)"""
    if not models_AVAILABLE:
        return json.dumps({"error": "Database models not available"})
    
    try:
        logger.info(f"[read_draft_history_resource] Reading history for draft {id}")
        history = await DraftHistory.get(id.lower())
        
        if not history:
            logger.error(f"[read_draft_history_resource] Draft history {id} not found")
            return json.dumps({"error": f"Draft history {id} not found"})
        
        # Convert DraftHistory to JSON
        if hasattr(history, 'to_dict'):
            history_data = history.to_dict()
        elif hasattr(history, '__dict__'):
            history_data = history.__dict__
        else:
            history_data = str(history)
        
        logger.info(f"[read_draft_history_resource] ✓ Returning draft history")
        return json.dumps(history_data, default=str)
        
    except Exception as e:
        logger.error(f"[read_draft_history_resource] Error: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    logger.info("Starting MCP draft server with PostgreSQL RDS...")
    mcp.run(transport='stdio')