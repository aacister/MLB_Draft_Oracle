
import os
import sys
import json
import logging
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✨ DEBUG: Log environment variables at startup
logger.info("=" * 80)
logger.info("RAG SEARCH SERVER STARTING - CREDENTIAL DEBUG")
logger.info("=" * 80)
logger.info(f"AWS_ACCESS_KEY_ID present: {bool(os.environ.get('AWS_ACCESS_KEY_ID'))}")
logger.info(f"AWS_SECRET_ACCESS_KEY present: {bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))}")
logger.info(f"AWS_SESSION_TOKEN present: {bool(os.environ.get('AWS_SESSION_TOKEN'))}")
logger.info(f"AWS_REGION: {os.environ.get('AWS_REGION', 'NOT SET')}")
logger.info(f"S3_MEMORY_BUCKET: {os.environ.get('S3_MEMORY_BUCKET', 'NOT SET')}")

# If credentials are missing, list all env vars (without values)
if not os.environ.get('AWS_ACCESS_KEY_ID'):
    logger.error("❌ AWS_ACCESS_KEY_ID is MISSING!")
    logger.info("Available env vars:")
    for key in sorted(os.environ.keys()):
        if 'AWS' in key or 'VECTOR' in key or 'DEPLOYMENT' in key:
            # Show key but not value for security
            logger.info(f"  - {key}: {'<set>' if os.environ.get(key) else '<empty>'}")

logger.info("=" * 80)

# ... rest of your rag_search_server.py code ...

from mcp.server import Server
import mcp.types as types

mcp = Server("rag-search")

@mcp.tool()
async def get_team_roster_status(team_name: str, draft_id: str) -> str:
    """
    Get current roster status for a specific team.
    Shows filled positions and needed positions.
    """
    
    logger.info(f"[get_team_roster_status] ===== STARTING =====")
    logger.info(f"[get_team_roster_status] Team: {team_name}, Draft: {draft_id}")
    
    # ✨ DEBUG: Check credentials INSIDE the function too
    logger.info(f"[get_team_roster_status] Checking credentials...")
    logger.info(f"  AWS_ACCESS_KEY_ID: {bool(os.environ.get('AWS_ACCESS_KEY_ID'))}")
    logger.info(f"  AWS_SECRET_ACCESS_KEY: {bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))}")
    logger.info(f"  AWS_SESSION_TOKEN: {bool(os.environ.get('AWS_SESSION_TOKEN'))}")
    
    try:
        import boto3
        
        bucket = os.environ.get('S3_MEMORY_BUCKET', 'mlbdraftoracle-memory-425865275846')
        region = os.environ.get('AWS_REGION', 'us-east-2')
        
        logger.info(f"[get_team_roster_status] Creating S3 client...")
        logger.info(f"[get_team_roster_status] Region: {region}")
        logger.info(f"[get_team_roster_status] Bucket: {bucket}")
        
        # Try to create S3 client with explicit credentials
        try:
            # ✨ DIAGNOSTIC: Try using credentials from environment explicitly
            aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
            aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
            
            if aws_access_key_id and aws_secret_access_key:
                logger.info("[get_team_roster_status] Using explicit credentials from environment")
                s3 = boto3.client(
                    's3',
                    region_name=region,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_session_token=aws_session_token  # None is OK if not present
                )
            else:
                logger.warning("[get_team_roster_status] Credentials missing, trying default boto3 client")
                s3 = boto3.client('s3', region_name=region)
                
        except Exception as boto_error:
            logger.error(f"[get_team_roster_status] Error creating S3 client: {boto_error}")
            raise
        
        # Load current draft state
        s3_key = f"source_data/historical_drafts/{draft_id}_current.json"
        logger.info(f"[get_team_roster_status] Attempting to get: s3://{bucket}/{s3_key}")
        
        try:
            obj = s3.get_object(Bucket=bucket, Key=s3_key)
            draft_data = json.loads(obj['Body'].read())
            logger.info(f"[get_team_roster_status] ✓ Successfully loaded draft data")
        except Exception as e:
            logger.error(f"[get_team_roster_status] S3 get_object failed: {e}")
            logger.error(f"[get_team_roster_status] Error type: {type(e).__name__}")
            return json.dumps({
                "status": "not_found",
                "message": f"Draft file not found: {s3_key}",
                "error": str(e),
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

# ... rest of server code ...

async def main():
    from mcp.server.stdio import stdio_server
    
    logger.info("Starting RAG Search MCP server...")
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(
            read_stream,
            write_stream,
            mcp.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())






































































