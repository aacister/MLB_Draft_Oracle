import os
import logging
from datetime import datetime, UTC
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from agents import Agent, Runner, trace
#from agents.extensions.models.litellm_model import LitellmModel

# Suppress LiteLLM warnings about optional dependencies
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

# Import from our modules
from context import get_agent_instructions, DEFAULT_RESEARCH_PROMPT
from mcp_servers import create_playwright_mcp_server
from tools import ingest_knowledge_base_document
from backend.models.player_pool import PlayerPool

# Load environment
load_dotenv(override=True)

app = FastAPI(title="MLBDraftOracle Knowledge Base Researcher Service")


# Request model
class ResearchRequest(BaseModel):
    topic: Optional[str] = None  # Optional - if not provided, agent picks a topic

async def run_research_agent() -> str:
    query = DEFAULT_RESEARCH_PROMPT

    # Please override these variables with the region you are using
    # Other choices: us-west-2 (for OpenAI OSS models) and eu-central-1
    #REGION = "us-east-2"
    #os.environ["AWS_REGION_NAME"] = REGION  # LiteLLM's preferred variable
    #os.environ["AWS_REGION"] = REGION  # Boto3 standard
    #os.environ["AWS_DEFAULT_REGION"] = REGION  # Fallback

    # Please override this variable with the model you are using
    # Other choices: bedrock/eu.amazon.nova-lite-v1:0 for EU and bedrock/us.amazon.nova-lite-v1:0 for US
    # bedrock/openai.gpt-oss-120b-1:0 for OpenAI OSS models
    # bedrock/converse/us.anthropic.claude-sonnet-4-20250514-v1:0 for Claude Sonnet 4
    #MODEL = "bedrock/us.amazon.nova-lite-v1:0"
    #model = LitellmModel(model=MODEL)

    # Create and run the agent with MCP server
    with trace("Researcher"):
        async with create_playwright_mcp_server(timeout_seconds=60) as playwright_mcp:
            agent = Agent(
                name="MLBDraftOracle Researcher",
                instructions=get_agent_instructions(),
                model="gpt-4o-mini",
                tools=[ingest_knowledge_base_document],
                mcp_servers=[playwright_mcp],
            )

            result = await Runner.run(agent, input=query, max_turns=15)

    return result.final_output


async def get_players_in_pool() -> str: 
    player_pool = await PlayerPool.get(id=None)
    players_in_pool = ','.join(player.name for player in player_pool.players)
    return players_in_pool


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "MLB Draft Oracle Knowledge Base Researcher",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/research")
async def research() -> str:
    """
    Generate investment research and advice.

    The agent will:
    1. Browse current websites for data
    2. Analyze the information found
    3. Store the analysis in the knowledge base

    """
    try:
        response = await run_research_agent()
        return response
    except Exception as e:
        print(f"Error in research endpoint: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/health")
async def health():
    """Detailed health check."""
    # Debug container detection
    container_indicators = {
        "dockerenv": os.path.exists("/.dockerenv"),
        "containerenv": os.path.exists("/run/.containerenv"),
        "aws_execution_env": os.environ.get("AWS_EXECUTION_ENV", ""),
        "ecs_container_metadata": os.environ.get("ECS_CONTAINER_METADATA_URI", ""),
        "kubernetes_service": os.environ.get("KUBERNETES_SERVICE_HOST", ""),
    }

    return {
        "service": "MLBDraftOracle Researcher",
        "status": "healthy",
        "mlbdraftoracle_ingest_api_configured": bool(os.getenv("MLBDRAFTORACLE_API_ENDPOINT") and os.getenv("MLBDRAFTORACLE_API_KEY")),
        "timestamp": datetime.now(UTC).isoformat(),
        "debug_container": container_indicators,
        #"aws_region": os.environ.get("AWS_DEFAULT_REGION", "not set"),
        #"bedrock_model": "bedrock/amazon.nova-pro-v1:0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
