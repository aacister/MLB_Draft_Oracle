from fastapi import HTTPException
from pydantic import BaseModel as PydanticBaseModel
from backend.models.draft import Draft
from backend.models.draft_history import DraftHistory
from backend.models.player_pool import PlayerPool
from backend.data.sqlite.database import read_drafts
from backend.data.memory import save_draft_state, load_draft_state
#from backend.data.postgresql.main import read_postgres_drafts
import logging
from typing import List, Dict, Optional
from backend.models.draft_teams import DraftTeams
import json
from fastapi import APIRouter
import os

api_url = os.getenv("API_URL")
#if os.getenv("DEPLOYMENT_ENVIRONMENT") == 'DEV':
#    use_local_db = True
#else: 
#    use_local_db = False
use_local_db = True

router = APIRouter()

class PlayerResponse(PydanticBaseModel):
    id: int
    name: str
    team: str
    position: str
    stats: dict
    is_drafted: bool

class PlayerPoolResponse(PydanticBaseModel):
    id: str
    players: List[PlayerResponse]


class TeamResponse(PydanticBaseModel):
    name: str
    strategy: str
    roster: dict



class DraftHistoryItemResponse(PydanticBaseModel):
    round: int
    pick: int
    team: str
    selection: str
    rationale: str



class DraftResponse(PydanticBaseModel):
    draft_id: str
    name: str
    num_rounds: int
    teams: List[TeamResponse]
    player_pool: PlayerPoolResponse
    draft_history: List[DraftHistoryItemResponse]
    draft_order: List[str]
    is_complete: bool

class DraftsResponse(PydanticBaseModel):
    draft_id: str
    name: str
    num_rounds: int
    is_complete: bool


    

@router.get('/draft', response_model=DraftResponse)
async def get_draft():
    print("Current working directory:", os.getcwd())
    try:
        # Get Draft
        draft = await Draft.get(id=None)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        # Verify teams is initialized
        if not draft.teams:
            logging.error("Draft teams is None after initialization")
            raise HTTPException(status_code=500, detail="Failed to initialize draft teams")
        
        # Get PlayerPoolResponse
        if not draft.player_pool:
            player_pool = await PlayerPool.get(id=None)
        else:
            player_pool = draft.player_pool
        
        if not player_pool:
            raise HTTPException(status_code=404, detail="Player pool not found")
        
        player_pool_response = PlayerPoolResponse(
            id=player_pool.id,
            players=[
                PlayerResponse(
                    id=player.id,
                    name=player.name,
                    team=player.team,
                    position=player.position,
                    stats=player.stats.to_dict() if hasattr(player.stats, 'to_dict') else vars(player.stats),
                    is_drafted=player.is_drafted
                ) for player in player_pool.players
            ])

        # Get TeamResponse
        teams_response = []
        
        for team in draft.teams.teams:
            roster_json = draft.get_team_roster(team.name)
            team_roster_data = json.loads(roster_json) if isinstance(roster_json, str) else roster_json
            roster = {pos: player if player else None for pos, player in team_roster_data.items()}
            name = team.name
            strategy = team.strategy
            teams_response.append(TeamResponse(name=name, strategy=strategy, roster=roster))
        
        # Get draft_order_response - List[TeamResponse]
        draft_order_response = []
        
        draft_order_json = draft.get_draft_order(1)
        draft_order_list = json.loads(draft_order_json) if isinstance(draft_order_json, str) else draft_order_json
        for team in draft_order_list:
            team_response = next((tr for tr in teams_response if tr.name == team.name), None)
            if not team_response:
                raise HTTPException(status_code=404, detail="TeamResponse not found in draft order")
            draft_order_response.append(team_response.name)

        
        # Get History - List[DraftHistoryItemResponse]
        history = await DraftHistory.get(draft.id.lower())
        history_response = [
            DraftHistoryItemResponse(
                round=item.round,
                pick=item.pick,
                team=item.team,
                selection=item.selection,
                rationale=item.rationale
            ) for item in history.items
        ] if history else []
        

        return DraftResponse(
            draft_id=draft.id,
            name=draft.name,
            num_rounds=draft.num_rounds,
            is_complete=draft.is_complete,
            teams=teams_response,
            player_pool=player_pool_response,
            draft_order=draft_order_response,
            draft_history=history_response
        )

    except Exception as e:
        logging.error(f"Error initiating draft: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error initiating draft: {str(e)}")

@router.get("/drafts/{id}", response_model=DraftResponse)
async def get_draft_by_id(id: str):
    draft = await Draft.get(id=id.lower())
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Get PlayerPoolResponse
    if not draft.player_pool:
        raise HTTPException(status_code=404, detail="Player pool not found")
    
    player_pool = draft.player_pool        
    player_pool_response = PlayerPoolResponse(
        id=player_pool.id,
        players=[
            PlayerResponse(
                id=player.id,
                name=player.name,
                team=player.team,
                position=player.position,
                stats=player.stats.to_dict() if hasattr(player.stats, 'to_dict') else vars(player.stats),
                is_drafted=player.is_drafted
            ) for player in player_pool.players
        ])

    # Get TeamResponse
    teams_response = []
        
    for team in draft.teams.teams:
            roster = team.roster
            name = team.name
            strategy = team.strategy
            teams_response.append(TeamResponse(name=name, strategy=strategy, roster=roster))
        
    # Get draft_order_response - List[TeamResponse]
    draft_order_response = []
      
    draft_order_json = draft.get_draft_order( 1)
    draft_order_list = json.loads(draft_order_json) if isinstance(draft_order_json, str) else draft_order_json
    for team in draft_order_list:
            team_response = next((tr for tr in teams_response if tr.name == team.name), None)
            if not team_response:
                raise HTTPException(status_code=404, detail="TeamResponse not found in draft order")
            draft_order_response.append(team_response.name)

        
    # Get History - List[DraftHistoryItemResponse]
    history = await DraftHistory.get(draft.id.lower())
    history_response = [
            DraftHistoryItemResponse(
                round=item.round,
                pick=item.pick,
                team=item.team,
                selection=item.selection,
                rationale=item.rationale
            ) for item in history.items
        ] if history else []
        

    return DraftResponse(
            draft_id=draft.id,
            name=draft.name,
            num_rounds=draft.num_rounds,
            is_complete=draft.is_complete,
            teams=teams_response,
            player_pool= player_pool_response,
            draft_order=draft_order_response,
            draft_history=history_response
        )

@router.post("/drafts/{draft_id}/resume")
async def resume_draft(draft_id: str):
    """Resume an incomplete draft"""
    draft = await Draft.get(draft_id.lower())
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if draft.is_complete:
        raise HTTPException(status_code=400, detail="Draft is already complete")
    
    # Load draft state from memory if available
    memory_state = load_draft_state(draft_id.lower())
    if memory_state:
        # Use memory state to restore draft
        draft.current_round = memory_state.get('current_round', draft.current_round)
        draft.current_pick = memory_state.get('current_pick', draft.current_pick)
    
    return {
        "draft_id": draft.id,
        "current_round": draft.current_round,
        "current_pick": draft.current_pick,
        "message": "Draft ready to resume"
    }

@router.get("/drafts/{draft_id}/teams/{team_name}/round/{round}/pick/{pick}/select-player", response_model=DraftResponse)
async def select_player(draft_id: str, team_name: str, round: int, pick: int):
    draft = await Draft.get(draft_id.lower())
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    # Validate the team should be drafting at this pick
    try:
        expected_team = draft.get_team_for_pick(round, pick)
        if expected_team.name.lower() != team_name.lower():
            error_msg = f"Invalid draft order: {team_name} cannot draft at Round {round}, Pick {pick}. Expected: {expected_team.name}"
            logging.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
    except ValueError as e:
        logging.error(f"Invalid pick validation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    team = next((team for team in draft.teams.teams if team.name.lower() == team_name.lower()), None)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found in draft")
    
    if draft.is_complete:
        raise HTTPException(status_code=400, detail="Draft is complete")
    
    logging.info(f"Team {team_name} drafting at Round {round}, Pick {pick}")
    
    await team.select_player(draft, round, pick)
    draft = await Draft.get(draft_id.lower())
    
    # Get PlayerPoolResponse
    if not draft.player_pool:
        raise HTTPException(status_code=404, detail="Player pool not found")
    
    player_pool = draft.player_pool        
    player_pool_response = PlayerPoolResponse(
        id=player_pool.id,
        players=[
            PlayerResponse(
                id=player.id,
                name=player.name,
                team=player.team,
                position=player.position,
                stats=player.stats.to_dict() if hasattr(player.stats, 'to_dict') else vars(player.stats),
                is_drafted=player.is_drafted
            ) for player in player_pool.players
        ])

    # Get TeamResponse
    teams_response = []
        
    for team in draft.teams.teams:
        roster = team.roster
        name = team.name
        strategy = team.strategy
        teams_response.append(TeamResponse(name=name, strategy=strategy, roster=roster))
        
    # Get draft_order_response
    draft_order_response = []
    draft_order_json = draft.get_draft_order(1)
    draft_order_list = json.loads(draft_order_json) if isinstance(draft_order_json, str) else draft_order_json
    for team in draft_order_list:
        team_response = next((tr for tr in teams_response if tr.name == team.name), None)
        if not team_response:
            raise HTTPException(status_code=404, detail="TeamResponse not found in draft order")
        draft_order_response.append(team_response.name)

    # Get History
    history = await DraftHistory.get(draft.id.lower())
    history_response = [
        DraftHistoryItemResponse(
            round=item.round,
            pick=item.pick,
            team=item.team,
            selection=item.selection,
            rationale=item.rationale
        ) for item in history.items
    ] if history else []

    return DraftResponse(
        draft_id=draft.id,
        name=draft.name,
        num_rounds=draft.num_rounds,
        is_complete=draft.is_complete,
        teams=teams_response,
        player_pool=player_pool_response,
        draft_order=draft_order_response,
        draft_history=history_response
    )
    
@router.get("/drafts", response_model=List[DraftsResponse])
async def get_drafts():
  #  if use_local_db:
    drafts = read_drafts()
    if not drafts:
        raise HTTPException(status_code=404, detail="No drafts found")
    
    drafts_response = []
        
    for draft_dict in drafts:
            if isinstance(draft_dict, dict):
                draft = Draft.from_dict(draft_dict)
            drafts_response.append(DraftsResponse( 
            draft_id=draft.id,
            name=draft.name,
            num_rounds=draft.num_rounds,
            is_complete=draft.is_complete
            ))
        
    return drafts_response
