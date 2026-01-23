#!/usr/bin/env python3
import sys
import os
import json
import asyncio
import uuid
from typing import Dict
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True, dotenv_path=find_dotenv())

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Storage for search tasks
search_tasks: Dict[str, dict] = {}

mcp = FastMCP(
    name="brave_search_wrapper",
    instructions="Wrapper for Brave Search that returns immediately with task IDs"
)


@mcp.tool()
async def brave_search_async(query: str) -> str:
    """
    Search the web using Brave Search.
    Returns immediately with a task ID.
    
    Args:
        query: The search query
    
    Returns:
        JSON with task_id for checking status later
    """
    task_id = f"search_{uuid.uuid4().hex[:8]}"
    
    search_tasks[task_id] = {
        "status": "processing",
        "message": f"Searching for: {query}",
        "query": query
    }
    
    logger.info(f"Task {task_id}: Starting search for '{query}'")
    
    # Start background search
    asyncio.create_task(_process_search_in_background(task_id, query))
    
    return json.dumps({
        "status": "accepted",
        "task_id": task_id,
        "message": f"Search started for: {query}"
    })


async def _process_search_in_background(task_id: str, query: str):
    """Background task to actually perform the search"""
    try:
        import httpx
        
        brave_api_key = os.getenv("BRAVE_API_KEY")
        if not brave_api_key:
            search_tasks[task_id] = {
                "status": "error",
                "error": "BRAVE_API_KEY not set"
            }
            return
        
        search_tasks[task_id]["status"] = "searching"
        
        # Make actual Brave Search API call
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": brave_api_key
                },
                params={"q": query, "count": 5},
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("web", {}).get("results", [])
                
                # Format results
                formatted_results = []
                for i, result in enumerate(results[:5], 1):
                    formatted_results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "description": result.get("description", "")
                    })
                
                search_tasks[task_id] = {
                    "status": "completed",
                    "message": f"Found {len(formatted_results)} results",
                    "query": query,
                    "results": formatted_results
                }
                
                logger.info(f"Task {task_id}: ✓ Search completed with {len(formatted_results)} results")
            else:
                search_tasks[task_id] = {
                    "status": "error",
                    "error": f"Search failed with status {response.status_code}"
                }
        
    except Exception as e:
        logger.error(f"Task {task_id}: Error - {e}", exc_info=True)
        search_tasks[task_id] = {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
async def check_search_status(task_id: str) -> str:
    """
    Check the status of a search task.
    
    Args:
        task_id: The task ID returned from brave_search_async
    
    Returns:
        JSON with current status and results if completed
    """
    if task_id not in search_tasks:
        return json.dumps({
            "status": "not_found",
            "error": f"Task {task_id} not found"
        })
    
    return json.dumps(search_tasks[task_id])


if __name__ == "__main__":
    logger.info("Starting Brave Search Wrapper MCP server...")
    mcp.run(transport='stdio')