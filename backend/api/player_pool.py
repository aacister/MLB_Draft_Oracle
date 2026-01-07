from fastapi import HTTPException
from typing import List
from pydantic import BaseModel as PydanticBaseModel
from backend.models.player_pool import PlayerPool
from backend.data.postgresql.unified_db import player_pool_exists, get_latest_player_pool
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

api_url = os.getenv("API_URL")

router = APIRouter()

logger = logging.getLogger(__name__)
logger.info("Player Pool API using PostgreSQL RDS exclusively")

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
    """Get player pool by ID - PostgreSQL RDS only"""
    logger.info(f"GET /player-pools/{id} - Using PostgreSQL RDS")
    player_pool = await PlayerPool.get(id=id.lower())
    if not player_pool:
        raise HTTPException(status_code=404, detail="Player pool not found in PostgreSQL RDS")

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
    """Get latest player pool - PostgreSQL RDS only"""
    logger.info("GET /player-pool - Using PostgreSQL RDS")
    player_pool = await PlayerPool.get(id=None)
    if not player_pool:
        raise HTTPException(status_code=404, detail="Player pool not found in PostgreSQL RDS")

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

@router.get("/player-pool/check", response_model=dict)
async def check_player_pool():
    """Check if a player pool exists - PostgreSQL RDS only"""
    logger.info("GET /player-pool/check - Using PostgreSQL RDS")
    exists = player_pool_exists()
    pool_data = None
    
    if exists:
        pool_data = get_latest_player_pool()
    
    return {
        "exists": exists,
        "pool_id": pool_data.get('id') if pool_data else None,
        "database": "PostgreSQL RDS"
    }