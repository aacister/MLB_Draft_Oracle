"""
backend/mcp_servers/rag_search_server.py

MCP Server providing RAG search capabilities to draft agents.
Allows agents to search historical draft context for informed decisions.
"""

import sys
import os
from pathlib import Path
import json
import logging

# Add parent to path
script_dir = Path(__file__).parent.absolute()
parent_dir = script_dir.parent.absolute()
sys.path.insert(0, str(parent_dir))

if os.path.exists("/var/task"):
    sys.path.insert(0, "/var/task")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True, dotenv_path=find_dotenv())

# Initialize MCP server
mcp = FastMCP(
    name="rag_search_server",
    instructions="""You provide access to the MLB Draft Oracle's historical draft context through vector search.
    Use this to help teams understand:
    - Which positions they have already filled
    - Which positions they still need
    - What strategies have been successful in similar situations
    - Historical patterns from past drafts
    """
)


@mcp.tool()
async def search_draft_context(query: str, top_k: int = 3) -> str:
    """
    Search historical draft context for relevant information.
    
    Use this tool to:
    - Check which positions your team has already drafted
    - See what positions your team still needs
    - Learn from historical draft patterns
    - Understand successful strategies
    
    Args:
        query: Natural language query (e.g., "What positions has PowerHouse already filled?")
        top_k: Number of results to return (default: 3, max: 5)
    
    Returns:
        JSON string with relevant draft context and similarity scores
    
    Examples:
        - "What positions has my team already drafted?"
        - "Which positions does my team still need?"
        - "What did Power Hitting teams prioritize in round 1?"
        - "Show me catchers drafted in previous rounds"
    """
    
    logger.info(f"[search_draft_context] Query: {query}")
    
    try:
        from backend.data.rag.vector_indexer import search_vectors
        
        # Limit top_k
        top_k = min(max(1, top_k), 5)
        
        # Search vectors
        results = search_vectors(query, top_k=top_k)
        
        if not results:
            return json.dumps({
                "status": "no_results",
                "message": "No relevant draft context found. This may be a new draft with no history yet.",
                "query": query,
                "results": []
            })
        
        # Format results for agent consumption
        formatted_results = []
        
        for result in results:
            formatted_results.append({
                "content": result.get("content"),
                "relevance_score": round(result.get("similarity_score", 0), 3),
                "draft_id": result.get("draft_id"),
                "type": result.get("type"),
                "metadata": result.get("metadata", {})
            })
        
        logger.info(f"[search_draft_context] Found {len(formatted_results)} results")
        
        return json.dumps({
            "status": "success",
            "query": query,
            "results_count": len(formatted_results),
            "results": formatted_results
        }, indent=2)
        
    except Exception as e:
        logger.error(f"[search_draft_context] Error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": str(e),
            "query": query
        })


@mcp.tool()
async def get_team_roster_status(team_name: str, draft_id: str) -> str:
    """
    Get current roster status for a specific team.
    Shows filled positions and needed positions.
    
    Args:
        team_name: Name of the team (e.g., "PowerHouse")
        draft_id: Current draft ID
    
    Returns:
        JSON with filled_positions and needed_positions
    
    Example:
        get_team_roster_status("PowerHouse", "draft_2026-02-11")
    """
    
    logger.info(f"[get_team_roster_status] Team: {team_name}, Draft: {draft_id}")
    
    try:
        import boto3
        
        s3 = boto3.client('s3', region_name='us-east-2')
        bucket = os.environ.get('S3_MEMORY_BUCKET', 'mlbdraftoracle-memory-425865275846')
        
        # Load current draft state
        s3_key = f"source_data/historical_drafts/{draft_id}_current.json"
        
        try:
            obj = s3.get_object(Bucket=bucket, Key=s3_key)
            draft_data = json.loads(obj['Body'].read())
        except Exception as e:
            logger.warning(f"Could not load draft file: {e}")
            return json.dumps({
                "status": "not_found",
                "message": f"Draft file not found: {s3_key}",
                "team_name": team_name,
                "draft_id": draft_id
            })
        
        # Find team
        teams = draft_data.get('teams', [])
        team_data = next((t for t in teams if t.get('name') == team_name), None)
        
        if not team_data:
            return json.dumps({
                "status": "team_not_found",
                "message": f"Team '{team_name}' not found in draft",
                "available_teams": [t.get('name') for t in teams]
            })
        
        # Return roster status
        return json.dumps({
            "status": "success",
            "team_name": team_name,
            "strategy": team_data.get('strategy'),
            "filled_positions": team_data.get('filled_positions', []),
            "needed_positions": team_data.get('needed_positions', []),
            "roster_complete": team_data.get('roster_complete', False)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"[get_team_roster_status] Error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": str(e),
            "team_name": team_name,
            "draft_id": draft_id
        })


if __name__ == "__main__":
    logger.info("Starting RAG Search MCP server...")
    mcp.run(transport='stdio')












































































