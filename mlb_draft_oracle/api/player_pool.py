from fastapi import HTTPException
from typing import List
from pydantic import BaseModel as PydanticBaseModel
from models.player_pool import PlayerPool
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
import os

api_url = os.getenv("API_URL")

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


@router.get("/player-pools/{id}", response_model=PlayerPoolResponse)
async def get_player_pool(id: str):
    player_pool = await PlayerPool.get(id=id.lower())
    if not player_pool:
        raise HTTPException(status_code=404, detail="Player pool not found")

    return PlayerPoolResponse(
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
        ]
    )

@router.get("/player-pool", response_model=PlayerPoolResponse)
async def get_player_pool():
    player_pool = await PlayerPool.get(id=None)
    if not player_pool:
        raise HTTPException(status_code=404, detail="Player pool not found")

    return PlayerPoolResponse(
        id=player_pool.id.lower(),
        players=[
            PlayerResponse(
                id=player.id,
                name=player.name,
                team=player.team,
                position=player.position,
                stats=player.stats.to_dict() if hasattr(player.stats, 'to_dict') else vars(player.stats),
                is_drafted=player.is_drafted
            ) for player in player_pool.players
        ]
    )