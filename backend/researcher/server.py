import os
import logging
import asyncio
from datetime import datetime, UTC
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio
#from agents.extensionsbackend.models.litellm_model import LitellmModel

# Suppress LiteLLM warnings about optional dependencies
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

# Import from our modules
from context import get_agent_instructions, DEFAULT_RESEARCH_PROMPT
from backend.mcp_servers import researcher_mcp_server_params
from tools import ingest_knowledge_base_document

# Load environment
load_dotenv(override=True, dotenv_path=find_dotenv())

app = FastAPI(title="MLBDraftOracle Knowledge Base Researcher Service")


# Request model
class ResearchRequest(BaseModel):
    topic: Optional[str] = None  

async def run_research_agent() -> str:
    query = DEFAULT_RESEARCH_PROMPT

    # Create and run the agent with MCP server
    with trace("Researcher"):
        async with MCPServerStdio(params=researcher_mcp_server_params[0]) as mcp_server:
            agent = Agent(
                name="MLBDraftOracle Researcher",
                instructions=get_agent_instructions(),
                model="gpt-41-mini",
                tools=[ingest_knowledge_base_document],
                mcp_servers=[mcp_server],
            )

            result = await Runner.run(agent, input=query, max_turns=50)

    return result.final_output


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
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
