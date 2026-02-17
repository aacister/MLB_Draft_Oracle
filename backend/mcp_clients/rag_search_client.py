import boto3
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ✨ Use Lambda's boto3 session directly - no subprocess needed!
def get_rag_search_tools_direct():
    """
    Get RAG search tools that run directly in Lambda context.
    This avoids subprocess credential issues.
    """
    
    # Use Lambda's built-in boto3 session
    s3 = boto3.client('s3')
    bucket = 'mlbdraftoracle-memory-425865275846'
    
    def search_draft_context_impl(query: str, top_k: int = 3) -> str:
        """Search draft context using vector search"""
        try:
            from backend.data.rag.vector_indexer import search_vectors
            
            # This now works because we're in Lambda context
            results = search_vectors(query, top_k=top_k)
            
            if not results:
                return json.dumps({
                    "status": "no_results",
                    "message": "No relevant draft context found.",
                    "query": query,
                    "results": []
                })
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get("content"),
                    "relevance_score": round(result.get("similarity_score", 0), 3),
                    "draft_id": result.get("draft_id"),
                    "type": result.get("type"),
                    "metadata": result.get("metadata", {})
                })
            
            return json.dumps({
                "status": "success",
                "query": query,
                "results_count": len(formatted_results),
                "results": formatted_results
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error in search_draft_context: {e}", exc_info=True)
            return json.dumps({
                "status": "error",
                "error": str(e),
                "query": query
            })
    
    def get_team_roster_status_impl(team_name: str, draft_id: str) -> str:
        """Get team roster status from S3"""
        try:
            s3_key = f"source_data/historical_drafts/{draft_id}_current.json"
            logger.info(f"Loading roster from s3://{bucket}/{s3_key}")
            
            obj = s3.get_object(Bucket=bucket, Key=s3_key)
            draft_data = json.loads(obj['Body'].read())
            
            teams = draft_data.get('teams', [])
            team_data = next((t for t in teams if t.get('name', '').lower() == team_name.lower()), None)
            
            if not team_data:
                return json.dumps({
                    "status": "team_not_found",
                    "message": f"Team '{team_name}' not found in draft",
                    "available_teams": [t.get('name') for t in teams]
                })
            
            return json.dumps({
                "status": "success",
                "team_name": team_name,
                "strategy": team_data.get('strategy'),
                "filled_positions": team_data.get('filled_positions', []),
                "needed_positions": team_data.get('needed_positions', []),
                "roster_complete": team_data.get('roster_complete', False)
            }, indent=2)
            
        except s3.exceptions.NoSuchKey:
            # File doesn't exist yet - this is expected for new/first drafts
            logger.info(f"Draft file not found (expected for new drafts): {s3_key}")
            return json.dumps({
                "status": "not_found",
                "message": f"No historical data available for this draft yet. This is expected for new drafts.",
                "team_name": team_name,
                "draft_id": draft_id
            })
        except Exception as e:
            logger.error(f"Error in get_team_roster_status: {e}", exc_info=True)
            return json.dumps({
                "status": "error",
                "message": f"Error retrieving roster status",
                "error": str(e),
                "team_name": team_name,
                "draft_id": draft_id
            })
    
    # Return as FunctionTools
    from agents import FunctionTool
    
    def parse_args(args):
        """Parse args - handle both string and dict"""
        if isinstance(args, str):
            import json
            return json.loads(args)
        return args
    
    # Async wrapper functions
    async def search_draft_context_wrapper(ctx, args):
        parsed = parse_args(args)
        return search_draft_context_impl(parsed.get("query"), parsed.get("top_k", 3))
    
    async def get_team_roster_status_wrapper(ctx, args):
        parsed = parse_args(args)
        return get_team_roster_status_impl(parsed.get("team_name"), parsed.get("draft_id"))
    
    return [
        FunctionTool(
            name="search_draft_context",
            description="Search historical draft context for relevant information",
            params_json_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 3}
                },
                "required": ["query", "top_k"],
                "additionalProperties": False
            },
            on_invoke_tool=search_draft_context_wrapper
        ),
        FunctionTool(
            name="get_team_roster_status",
            description="Get current roster status for a specific team",
            params_json_schema={
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "draft_id": {"type": "string"}
                },
                "required": ["team_name", "draft_id"],
                "additionalProperties": False
            },
            on_invoke_tool=get_team_roster_status_wrapper
        )
    ]