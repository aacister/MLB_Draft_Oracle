#!/usr/bin/env python3
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

from backend.mcp_servers.brave_search_wrapper import brave_search_async, check_search_status

def handler(event, context):
    """Lambda handler for brave search MCP server"""
    try:
        method = event.get('method')
        params = event.get('params', {})
        request_id = event.get('id', 1)
        
        if method == 'tools/list':
            tools = [
                {
                    "name": "brave_search_async",
                    "description": "Search the web using Brave Search (async)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                },
                {
                    "name": "check_search_status",
                    "description": "Check status of a search task",
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
            
            if tool_name == 'brave_search_async':
                result = asyncio.run(brave_search_async(**arguments))
            elif tool_name == 'check_search_status':
                result = asyncio.run(check_search_status(**arguments))
            else:
                return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}, "id": request_id}
            
            return {"jsonrpc": "2.0", "result": result, "id": request_id}
        
        else:
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Unknown method: {method}"}, "id": request_id}
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": event.get('id', 1)}