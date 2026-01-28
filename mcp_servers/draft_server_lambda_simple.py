import sys
import os
import json
import logging
from pathlib import Path

script_dir = Path(__file__).parent.absolute()
parent_dir = script_dir.parent.absolute()
sys.path.insert(0, str(parent_dir))
if os.path.exists("/var/task"):
    sys.path.insert(0, "/var/task")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv, find_dotenv
load_dotenv(override=True, dotenv_path=find_dotenv())

from backend.mcp_servers.draft_server import (
    draft_specific_player,
    check_draft_status,
    read_draft_player_pool_resource,
    read_draft_player_pool_available_resource,
    read_draft_team_roster_resource,
    read_draft_history_resource
)

def handler(event, context):
    """Lambda handler for MCP draft server"""
    try:
        logger.info(f"Event: {json.dumps(event)}")
        
        method = event.get('method')
        params = event.get('params', {})
        request_id = event.get('id', 1)
        
        if method == 'tools/list':
            tools = [
                {
                    "name": "draft_specific_player",
                    "description": "Draft a player for a team (async)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "draft_id": {"type": "string"},
                            "team_name": {"type": "string"},
                            "player_name": {"type": "string"},
                            "round_num": {"type": "string"},
                            "pick_num": {"type": "string"},
                            "rationale": {"type": "string"}
                        },
                        "required": ["draft_id", "team_name", "player_name", "round_num", "pick_num", "rationale"]
                    }
                },
                {
                    "name": "check_draft_status",
                    "description": "Check status of a draft task",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"task_id": {"type": "string"}},
                        "required": ["task_id"]
                    }
                }
            ]
            return {"jsonrpc": "2.0", "result": {"tools": tools}, "id": request_id}
        
        elif method == 'tools/call':
            import asyncio
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            
            if tool_name == 'draft_specific_player':
                result = asyncio.run(draft_specific_player(**arguments))
            elif tool_name == 'check_draft_status':
                result = asyncio.run(check_draft_status(**arguments))
            else:
                return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}, "id": request_id}
            
            result_obj = json.loads(result) if isinstance(result, str) else result
            return {"jsonrpc": "2.0", "result": result_obj, "id": request_id}
        
        elif method == 'resources/read':
            import asyncio
            uri = params.get('uri')
            
            logger.info(f"Reading resource: {uri}")
            
            # Parse URI correctly
            # Format: draft://resource_type/draft_id[/additional_params]
            
            if '/available' in uri:
                # draft://player_pool/DRAFT_ID/available
                draft_id = uri.split('/')[2]
                logger.info(f"Reading available players for draft: {draft_id}")
                result = asyncio.run(read_draft_player_pool_available_resource(draft_id))
                
            elif uri.startswith('draft://player_pool/'):
                # draft://player_pool/DRAFT_ID
                draft_id = uri.split('/')[2]
                logger.info(f"Reading player pool for draft: {draft_id}")
                result = asyncio.run(read_draft_player_pool_resource(draft_id))
                
            elif uri.startswith('draft://team_roster/'):
                # draft://team_roster/DRAFT_ID/TEAM_NAME
                parts = uri.split('/')
                # parts[0] = "draft:"
                # parts[1] = ""
                # parts[2] = "team_roster"
                # parts[3] = draft_id
                # parts[4] = team_name
                
                if len(parts) < 5:
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32602,
                            "message": f"Invalid URI format: {uri}. Expected draft://team_roster/DRAFT_ID/TEAM_NAME"
                        },
                        "id": request_id
                    }
                
                draft_id = parts[3]
                team_name = parts[4]
                logger.info(f"Reading team roster for draft: {draft_id}, team: {team_name}")
                result = asyncio.run(read_draft_team_roster_resource(draft_id, team_name))
                
            elif uri.startswith('draft://history/'):
                # draft://history/DRAFT_ID
                draft_id = uri.split('/')[2]
                logger.info(f"Reading draft history for draft: {draft_id}")
                result = asyncio.run(read_draft_history_resource(draft_id))
                
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": f"Unknown resource: {uri}"
                    },
                    "id": request_id
                }
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "contents": [{"type": "text", "text": result}]
                },
                "id": request_id
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Unknown method: {method}"
                },
                "id": request_id
            }
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            },
            "id": event.get('id', 1)
        }