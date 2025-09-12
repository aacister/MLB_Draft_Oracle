from mcp.server.fastmcp import FastMCP
from models.teams import Team
from typing import Optional
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

mcp = FastMCP("teams_server")

@mcp.resource("teams://strategy/{name}")
async def read_strategy_resource(name: str) -> str:
    team = Team.get(name.lower())
    return team.get_strategy()

@mcp.resource("team://neededPositions//{name}")
async def read_needed_positions_resource(name: str) -> str:
    team = Team.get(name.lower())
    positionsSet = team.get_needed_positions()
    return ", ".join(str(position) for position in positionsSet)

@mcp.resource("team://roster/{name}")
async def read_account_resource(name: str) -> str:
    team = team.get(name.lower())
    return await team.reportRoster()

if __name__ == "__main__":
    mcp.run(transport='stdio')