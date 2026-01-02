import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from backend.models.draft import Draft
from backend.models.teams import Team
from backend.models.draft_history import DraftHistory
from backend.models.draft_selection_data import DraftSelectionData
from backend.models.player_pool import PlayerPool
from backend.templates.templates import drafter_instructions
from mcp.server.fastmcp import FastMCP
from typing import List



db_url = "postgresql://rootuser:RogerFedererNumber1@mlb-draft-oracle-database.cn46mqoccdqx.us-east-2.rds.amazonaws.com:5432/postgres"

try:
    backend_models_AVAILABLE = True
    print("All backend.models imported successfully")
except Exception as e:
    print(f"Warning: Could not import backend.models: {e}")
    backend_models_AVAILABLE = False
    
mcp = FastMCP(
    name="draft_server",
    instructions=f"""You are a fantasy baseball team in a fantasy baseball draft. You are drafting a player with goal to fill  
    out all the positions on your team roster with best players that align to your team's draft strategy.  Do not draft players for 
    postions on your roster that have already been filled with a player.  Draft only one player per round.
    If the 'draft_specific_player' call fails, retry the call for a different player.
    Keep trying to call synchronously the 'draft_specific_player' tool function call with a different player till a successful call is made.
    Ensure only one successful call is made per round. Do NOT prompt the user with questions.
"""
    )

@mcp.tool()
async def draft_specific_player(draft_id, team_name, player_name, round_num, pick_num, rationale) -> DraftSelectionData | str:
    try:
        """Draft a player for a team in the draft.

        Args:
            draft_id: The id of the draft
            team_name: The name of the team drafting a player
            player_name: The name of player of draft
            round: The current draft round
            pick: The current pick number
            rationale: The rationale for the player selection and fit with the team's strategy
        """
        if not backend_models_AVAILABLE:
            return f"Error: Database backend.models not available. Cannot draft player {player_name}."
        
        draft = await Draft.get(draft_id)
        if draft == None:
            raise ValueError(f"Draft {draft_id} does not exist.")
        
        # Ensure player_pool is initialized
        if draft.player_pool is None:
            draft.player_pool = await PlayerPool.get(id=None)
        
        available_players = draft.get_undrafted_players()
        selected_player = next((p for p in available_players if p.name == player_name), None)
        if not selected_player:
            print(f"Player {player_name} not found in available players.")
            return { "result": f"Player {player_name} not found in available players."}
        
        #selected_player = Player.from_dict(player_dict)
        team = Team.get(team_name)
        round_num = int(round_num)
        pick_num = int(pick_num)
        await draft.draft_player(
            team=team,
            round=round_num,
            pick=pick_num,
            selected_player=selected_player,
            rationale=rationale
        )
        return DraftSelectionData(player_id=selected_player.id, player_name=selected_player.name, reason=rationale)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error in draft_specific_player: {e}"
        

@mcp.resource("draft://player_pool/{id}")
async def read_draft_player_pool_resource(id: str) -> str:
    if not backend_models_AVAILABLE:
        return "Error: Database backend.models not available."
    draft = await Draft.get(id.lower())
    return draft.get_draft_player_pool()

@mcp.resource("draft://player_pool/{id}/available")
async def read_draft_player_pool_available_resource(id: str) -> str:
    if not backend_models_AVAILABLE:
        return "Error: Database backend.models not available."
    draft = await Draft.get(id.lower())
    return draft.get_undrafted_players()

@mcp.resource("draft://team_roster/{id}/{team_name}")
async def read_draft_team_roster_resource(id: str, team_name: str) -> str:
    if not backend_models_AVAILABLE:
        return "Error: Database backend.models not available."
    print("here")
    draft = await Draft.get(id.lower())
    print("Found draft.")
    return draft.get_team_roster(team_name)

@mcp.resource("draft://draft_order/{id}/round/{round}")
async def get_draft_order(id: str, round: int) -> List[Team]:
    if not backend_models_AVAILABLE:
        return []
    draft = await Draft.get(id.lower())
    return draft.get_draft_order(round)


@mcp.resource("draft://history/{id}")
async def read_draft_history_resource(id: str) -> str:
    if not backend_models_AVAILABLE:
        return "Error: Database backend.models not available."
    draft = await Draft.get(id.lower())
    return await DraftHistory.get(draft.id)
    
if __name__ == "__main__":
    print("Starting MCP draft server...")
    mcp.run(transport='stdio')