"""
Lambda handler for MCP Draft Server
Provides draft_specific_player tool as a Lambda function
"""

import json
import logging
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_tool_call_async(tool_name: str, arguments: dict) -> dict:
    """Handle tool calls - executes the actual draft logic"""
    
    if tool_name == "draft_specific_player":
        from backend.models.draft import Draft
        from backend.models.teams import Team
        from backend.models.draft_history import DraftHistory
        from backend.models.player_pool import PlayerPool
        
        logger.info(f"[draft_specific_player] ===== STARTING =====")
        logger.info(f"[draft_specific_player] Arguments: {arguments}")
        
        try:
            draft_id = arguments["draft_id"]
            team_name = arguments["team_name"]
            player_name = arguments["player_name"]
            round_num = int(arguments["round_num"])
            pick_num = int(arguments["pick_num"])
            rationale = arguments.get("rationale", "")
            
            # Load draft
            logger.info(f"[draft_specific_player] Loading draft {draft_id}")
            draft = await Draft.get(draft_id.lower())
            
            if not draft:
                error_msg = f"Draft {draft_id} not found"
                logger.error(f"[draft_specific_player] {error_msg}")
                return {"status": "error", "error": error_msg}
            
            # Ensure player pool
            if draft.player_pool is None:
                logger.info(f"[draft_specific_player] Loading player pool")
                draft.player_pool = await PlayerPool.get(id=None)
            
            # Get available players
            available_players = draft.get_undrafted_players()
            logger.info(f"[draft_specific_player] {len(available_players)} available players")
            
            # Find the player
            selected_player = next(
                (p for p in available_players if p.name.lower() == player_name.lower()), 
                None
            )
            
            if not selected_player:
                error_msg = f"Player {player_name} not found in available players"
                logger.error(f"[draft_specific_player] {error_msg}")
                
                # Try fuzzy matching
                from difflib import get_close_matches
                player_names = [p.name for p in available_players]
                close_matches = get_close_matches(player_name, player_names, n=3, cutoff=0.6)
                
                if close_matches:
                    error_msg += f". Did you mean: {', '.join(close_matches)}?"
                
                return {"status": "error", "error": error_msg}
            
            logger.info(f"[draft_specific_player] ✓ Found player: {selected_player.name}")
            
            # Get team
            team = Team.get(team_name)
            logger.info(f"[draft_specific_player] ✓ Team loaded: {team.name}")
            
            # Draft the player
            logger.info(f"[draft_specific_player] 🚀 Calling draft.draft_player()")
            result = await draft.draft_player(
                team=team,
                round=round_num,
                pick=pick_num,
                selected_player=selected_player,
                rationale=rationale
            )
            
            logger.info(f"[draft_specific_player] ✓ draft.draft_player() completed")
            
            # Verify draft history was updated
            history = await DraftHistory.get(draft_id.lower())
            pick_item = next(
                (item for item in history.items 
                 if item.round == round_num and item.pick == pick_num),
                None
            )
            
            if pick_item and pick_item.selection:
                logger.info(f"[draft_specific_player] ✓✓✓ VERIFIED: {pick_item.selection}")
            else:
                logger.error(f"[draft_specific_player] ✗ Draft history NOT updated")
            
            logger.info(f"[draft_specific_player] ===== SUCCESS =====")
            
            return {
                "status": "completed",
                "player_id": selected_player.id,
                "player_name": selected_player.name,
                "round": round_num,
                "pick": pick_num,
                "rationale": rationale
            }
            
        except Exception as e:
            error_msg = f"Error drafting player: {str(e)}"
            logger.error(f"[draft_specific_player] ===== ERROR =====")
            logger.error(f"[draft_specific_player] {error_msg}", exc_info=True)
            return {"status": "error", "error": error_msg}
    
    else:
        return {"status": "error", "error": f"Unknown tool: {tool_name}"}


def handler(event, context):
    """
    Lambda handler for MCP Draft Server
    
    Receives tool call requests from mlb-draft-oracle-worker and executes them.
    
    Event format:
    {
        "action": "call_tool",
        "tool_name": "draft_specific_player",
        "arguments": {
            "draft_id": "...",
            "team_name": "...",
            "player_name": "...",
            "round_num": 1,
            "pick_num": 1,
            "rationale": "..."
        }
    }
    """
    logger.info(f"[MCP Draft Lambda] Received event: {json.dumps(event, default=str)[:500]}")
    
    try:
        action = event.get("action")
        
        if action == "call_tool":
            tool_name = event.get("tool_name")
            arguments = event.get("arguments", {})
            
            logger.info(f"[MCP Draft Lambda] Calling tool: {tool_name}")
            
            # Run async function
            result = asyncio.run(handle_tool_call_async(tool_name, arguments))
            
            logger.info(f"[MCP Draft Lambda] Tool result: {result.get('status')}")
            
            return {
                "statusCode": 200,
                "body": json.dumps(result)
            }
        
        elif action == "list_tools":
            # Return available tools
            tools = [
                {
                    "name": "draft_specific_player",
                    "description": "Draft a specific player for a team",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "draft_id": {"type": "string"},
                            "team_name": {"type": "string"},
                            "player_name": {"type": "string"},
                            "round_num": {"type": "integer"},
                            "pick_num": {"type": "integer"},
                            "rationale": {"type": "string"}
                        },
                        "required": ["draft_id", "team_name", "player_name", "round_num", "pick_num"]
                    }
                }
            ]
            
            return {
                "statusCode": 200,
                "body": json.dumps({"tools": tools})
            }
        
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Unknown action: {action}"})
            }
    
    except Exception as e:
        logger.error(f"[MCP Draft Lambda] Error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }