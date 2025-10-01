from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as PydanticBaseModel
from models.players import Player
from fastapi import APIRouter
import os

api_url = os.getenv("API_URL")
router = APIRouter()

class PlayerResponse(PydanticBaseModel):
    id: int
    name: str
    team: str
    position: str
    stats: dict


@router.get("/players/{player_id}", response_model=PlayerResponse)
async def get_player(player_id: int):
    player = Player.get(player_id)
    if not player:  # Check if player exists and has a valid name
        raise HTTPException(status_code=404, detail="Player not found")
    return PlayerResponse(
        id=player.id,
        name=player.name,
        team=player.team,
        position=player.position,
        stats=player.stats.to_dict() if hasattr(player.stats, 'to_dict') else vars(player.stats)
    )