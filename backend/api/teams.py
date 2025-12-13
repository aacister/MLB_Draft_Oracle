from fastapi import HTTPException
from typing import List
from pydantic import BaseModel as PydanticBaseModel
from backend.models.draft import Draft
from backend.models.teams import Team
from fastapi import APIRouter
import os

api_url = os.getenv("API_URL")
router = APIRouter()
class TeamResponse(PydanticBaseModel):
    name: str
    strategy: str
    roster: dict
    drafted_players: List[dict]





@router.get("/drafts/{draft_id}/teams/{team_name}", response_model=TeamResponse)
async def get_team(draft_id: str, team_name: str):
    draft = await Draft.get(draft_id.lower())
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    team = next((t for t in draft.teams.teams if t.name.lower() == team_name.lower()), None)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found in draft")
    
    return TeamResponse(
        name=team.name,
        strategy=team.strategy,
        roster={k: v.dict() if v else None for k, v in team.roster.items()},
        drafted_players=[p.dict() for p in team.drafted_players]
    )
