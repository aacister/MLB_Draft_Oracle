#!/usr/bin/env python3
import sys
import os
# Add the parent directory to Python path so we can import from models, templates, etc.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from typing import List

# Create a minimal MCP server without heavy model imports
mcp = FastMCP(
    name="minimal_draft_server",
    instructions="Minimal draft server for testing"
)

@mcp.tool()
async def draft_specific_player(draft_id, team_name, player_name, round_num, pick_num, rationale) -> str:
    """Draft a player for a team in the draft.

    Args:
        draft_id: The id of the draft
        team_name: The name of the team drafting a player
        player_name: The name of player of draft
        round: The current draft round
        pick: The current pick number
        rationale: The rationale for the player selection and fit with the team's strategy
    """
    return f"Minimal server: Would draft {player_name} for {team_name} in round {round_num}, pick {pick_num}. Reason: {rationale}"

@mcp.resource("draft://player_pool/{id}")
async def read_draft_player_pool_resource(id: str) -> str:
    return "Minimal server: Player pool data not available"

@mcp.resource("draft://player_pool/{id}/available")
async def read_draft_player_pool_available_resource(id: str) -> str:
    return "Minimal server: Available players not available"

@mcp.resource("draft://team_roster/{id}/{team_name}")
async def read_draft_team_roster_resource(id: str, team_name: str) -> str:
    return "Minimal server: Team roster not available"

@mcp.resource("draft://draft_order/{id}/round/{round}")
async def get_draft_order(id: str, round: int) -> List[str]:
    return ["Team1", "Team2", "Team3"]

@mcp.resource("draft://history/{id}")
async def read_draft_history_resource(id: str) -> str:
    return "Minimal server: Draft history not available"
    
if __name__ == "__main__":
    print("Starting minimal MCP draft server...", file=sys.stderr)
    print("Server is ready to accept connections", file=sys.stderr)
    try:
        mcp.run(transport='stdio')
    except Exception as e:
        print(f"Error in MCP server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
