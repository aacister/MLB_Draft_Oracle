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

from backend.mcp_servers.knowledgebase_server import search_knowledgebase

def handler(event, context):
    """Lambda handler for knowledgebase MCP server"""
    try:
        method = event.get('method')
        params = event.get('params', {})
        request_id = event.get('id', 1)
        
        if method == 'tools/list':
            tools = [{
                "name": "search_knowledgebase",
                "description": "Search the MLB Draft Oracle knowledge base",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer", "default": 5}
                    },
                    "required": ["query"]
                }
            }]
            return {"jsonrpc": "2.0", "result": {"tools": tools}, "id": request_id}
        
        elif method == 'tools/call':
            import asyncio
            arguments = params.get('arguments', {})
            result = asyncio.run(search_knowledgebase(**arguments))
            return {"jsonrpc": "2.0", "result": result, "id": request_id}
        
        else:
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Unknown method: {method}"}, "id": request_id}
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": event.get('id', 1)}