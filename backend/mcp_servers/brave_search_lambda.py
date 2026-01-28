"""
Lambda handler for MCP Brave Search Server
Provides web search tools as a Lambda function
"""

import json
import logging
import os
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def brave_search(query: str, count: int = 10) -> dict:
    """Execute Brave search"""
    api_key = os.getenv("BRAVE_API_KEY")
    
    if not api_key:
        return {"error": "BRAVE_API_KEY not set"}
    
    try:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key
        }
        params = {
            "q": query,
            "count": count
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        logger.error(f"[brave_search] Error: {e}")
        return {"error": str(e)}


def handler(event, context):
    """
    Lambda handler for MCP Brave Search Server
    
    Event format:
    {
        "action": "call_tool",
        "tool_name": "brave_search",
        "arguments": {
            "query": "search query",
            "count": 10
        }
    }
    """
    logger.info(f"[MCP Brave Search Lambda] Received event")
    
    try:
        action = event.get("action")
        
        if action == "call_tool":
            tool_name = event.get("tool_name")
            arguments = event.get("arguments", {})
            
            if tool_name == "brave_search":
                query = arguments.get("query")
                count = arguments.get("count", 10)
                
                logger.info(f"[brave_search] Query: {query}")
                
                result = brave_search(query, count)
                
                return {
                    "statusCode": 200,
                    "body": json.dumps(result)
                }
            else:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": f"Unknown tool: {tool_name}"})
                }
        
        elif action == "list_tools":
            tools = [
                {
                    "name": "brave_search",
                    "description": "Search the web using Brave Search",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "count": {"type": "integer"}
                        },
                        "required": ["query"]
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
        logger.error(f"[MCP Brave Search Lambda] Error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }