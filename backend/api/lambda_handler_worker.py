"""
Worker Lambda handler - handles long-running draft picks.
This function is invoked asynchronously by the main API Lambda.
"""
import json
import logging
import asyncio
from backend.models.draft import Draft
from backend.models.teams import Team

logger = logging.getLogger()
logger.setLevel(logging.INFO)


async def execute_draft_pick(draft_id: str, team_name: str, round: int, pick: int):
    """
    Execute a draft pick by calling team.select_player().
    This is where the MCP agents (Researcher and Drafter) get triggered.
    """
    try:
        logger.info(f"[Worker] Starting draft execution for {team_name} at R{round} P{pick}")
        
        # Load the draft
        draft = await Draft.get(draft_id.lower())
        if not draft:
            logger.error(f"[Worker] Draft {draft_id} not found")
            return {
                "success": False,
                "error": f"Draft {draft_id} not found"
            }
        
        # Get the team
        team = next((t for t in draft.teams.teams if t.name.lower() == team_name.lower()), None)
        if not team:
            logger.error(f"[Worker] Team {team_name} not found")
            return {
                "success": False,
                "error": f"Team {team_name} not found"
            }
        
        logger.info(f"[Worker] Calling team.select_player() - THIS TRIGGERS MCP AGENTS")
        
        # THIS IS THE CRITICAL CALL - It triggers the Researcher and Drafter MCP agents
        result = await team.select_player(draft, round, pick)
        
        logger.info(f"[Worker] ✓ Draft pick completed for {team_name}")
        
        return {
            "success": True,
            "result": str(result),
            "draft_id": draft_id,
            "team_name": team_name,
            "round": round,
            "pick": pick
        }
        
    except Exception as e:
        logger.error(f"[Worker] Error executing draft pick: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def handler(event, context):
    """
    Lambda handler for worker function.
    
    Expected event format:
    {
        "action": "execute_draft_pick",
        "draft_id": "...",
        "team_name": "...",
        "round": 3,
        "pick": 5
    }
    """
    try:
        logger.info(f"[Worker] Received event: {json.dumps(event)}")
        
        # Parse event
        action = event.get('action')
        
        if action == 'execute_draft_pick':
            draft_id = event.get('draft_id')
            team_name = event.get('team_name')
            round_num = event.get('round')
            pick_num = event.get('pick')
            
            logger.info(f"[Worker] Executing draft pick: {team_name} R{round_num} P{pick_num}")
            
            # Run the async function
            result = asyncio.run(
                execute_draft_pick(draft_id, team_name, round_num, pick_num)
            )
            
            logger.info(f"[Worker] Result: {result}")
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        else:
            logger.error(f"[Worker] Unknown action: {action}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
            
    except Exception as e:
        logger.error(f"[Worker] Error in handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }