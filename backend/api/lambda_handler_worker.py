from mangum import Mangum
from backend.api.main import app
import logging
import os
import json
import asyncio

logger = logging.getLogger()
logger.setLevel(logging.INFO)


async def execute_draft_pick_async(draft_id, team_name, round_num, pick_num):
    """
    Execute a draft pick asynchronously (called when Lambda invokes itself).
    
    This is the actual draft execution logic that runs when the Lambda
    invokes itself asynchronously.
    """
    from backend.models.draft import Draft
    from backend.models.teams import Team
    
    logger.info(f"[Worker] ===== EXECUTE DRAFT PICK =====")
    logger.info(f"[Worker] Draft: {draft_id}, Team: {team_name}, R{round_num} P{pick_num}")
    
    try:
        # Load draft
        logger.info(f"[Worker] Loading draft from PostgreSQL...")
        draft = await Draft.get(draft_id.lower())
        
        if not draft:
            error_msg = f"Draft {draft_id} not found"
            logger.error(f"[Worker] {error_msg}")
            return {"success": False, "error": error_msg}
        
        logger.info(f"[Worker] ✓ Draft loaded")
        
        # Get team
        team = Team.get(team_name)
        if not team:
            error_msg = f"Team {team_name} not found"
            logger.error(f"[Worker] {error_msg}")
            return {"success": False, "error": error_msg}
        
        logger.info(f"[Worker] ✓ Team loaded: {team.name}")
        logger.info(f"[Worker] Calling team.select_player() - THIS TRIGGERS MCP AGENTS")
        
        # Execute draft pick (this calls MCP agents)
        result = await team.select_player(draft, round_num, pick_num)
        
        logger.info(f"[Worker] ✓ Draft pick completed")
        logger.info(f"[Worker] Result: {result}")
        logger.info(f"[Worker] ===== SUCCESS =====")
        
        return {
            "success": True,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"[Worker] ===== ERROR =====")
        logger.error(f"[Worker] Error: {e}", exc_info=True)
        
        # Return error with detailed message for frontend
        error_message = str(e)
        if "DRAFT FAILED" in error_message:
            # This is a draft failure - include full details
            return {
                "success": False,
                "error": error_message,
                "error_type": "draft_failure",
                "message": "All draft attempts failed. Please try again or contact support."
            }
        else:
            # Generic error
            return {
                "success": False,
                "error": error_message,
                "error_type": "unknown",
                "message": "An error occurred during the draft."
            }


def handler(event, context):
    """
    Unified Lambda handler that supports both:
    1. HTTP requests (via API Gateway) - handled by Mangum/FastAPI
    2. Direct invocations (for async draft execution)
    
    This allows a single Lambda to:
    - Receive HTTP requests from frontend → Route to FastAPI endpoints
    - Invoke itself asynchronously → Execute draft picks without timeout
    """
    
    logger.info(f"[Handler] ===== REQUEST RECEIVED =====")
    logger.info(f"[Handler] Event keys: {list(event.keys())}")
    
    try:
        # ====================================================================
        # CASE 1: Direct Lambda Invocation (async draft execution)
        # ====================================================================
        if "action" in event and event["action"] == "execute_draft_pick":
            logger.info(f"[Handler] Direct invocation: execute_draft_pick")
            
            draft_id = event.get("draft_id")
            team_name = event.get("team_name")
            round_num = event.get("round")
            pick_num = event.get("pick")
            
            logger.info(f"[Handler] Executing draft: {team_name} at R{round_num} P{pick_num}")
            
            # Run async function synchronously
            result = asyncio.run(
                execute_draft_pick_async(draft_id, team_name, round_num, pick_num)
            )
            
            logger.info(f"[Handler] Draft execution completed: {result.get('success')}")
            return result
        
        # ====================================================================
        # CASE 2: API Gateway HTTP Request
        # ====================================================================
        elif "requestContext" in event:
            logger.info(f"[Handler] HTTP request via API Gateway")
            
            method = event.get('httpMethod', 'UNKNOWN')
            path = event.get('path', 'UNKNOWN')
            logger.info(f"[Handler] {method} {path}")
            
            # Handle OPTIONS requests directly for CORS preflight
            if method == 'OPTIONS':
                logger.info(f"[Handler] Handling OPTIONS preflight")
                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT',
                        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                        'Access-Control-Max-Age': '86400'
                    },
                    'body': ''
                }
            
            # Verify DB_URL is available
            db_url = os.getenv('DB_URL')
            if not db_url:
                logger.error("[Handler] DB_URL not set - PostgreSQL RDS connection required")
                return {
                    'statusCode': 500,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({
                        "error": "Database configuration error",
                        "message": "DB_URL not configured"
                    })
                }
            
            logger.info("[Handler] PostgreSQL RDS connection configured via DB_URL")
            
            # Use Mangum to handle the HTTP request with FastAPI
            logger.info("[Handler] Routing to FastAPI via Mangum...")
            asgi_handler = Mangum(app, lifespan="off")
            response = asgi_handler(event, context)
            
            # Ensure CORS headers are in response
            if 'headers' not in response:
                response['headers'] = {}
            
            response['headers']['Access-Control-Allow-Origin'] = '*'
            response['headers']['Access-Control-Allow-Methods'] = 'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT'
            response['headers']['Access-Control-Allow-Headers'] = 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            
            logger.info(f"[Handler] Response status: {response.get('statusCode')}")
            return response
        
        # ====================================================================
        # CASE 3: Unknown event format
        # ====================================================================
        else:
            logger.error(f"[Handler] Unknown event format")
            logger.error(f"[Handler] Event: {json.dumps(event, default=str)[:1000]}")
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Invalid event format',
                    'received_keys': list(event.keys())
                })
            }
        
    except Exception as e:
        logger.error(f"[Handler] ===== UNHANDLED ERROR =====")
        logger.error(f"[Handler] Error: {e}", exc_info=True)
        
        # Return appropriate error response based on event type
        if "requestContext" in event:
            # HTTP request - return HTTP error
            return {
                'statusCode': 500,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Internal Server Error',
                    'message': str(e)
                })
            }
        else:
            # Direct invocation - return error dict
            return {
                'success': False,
                'error': str(e)
            }