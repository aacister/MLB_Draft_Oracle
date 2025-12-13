from backend.models.players import Player
from pydantic import BaseModel, Field
from typing import Optional


class DraftSelectionData(BaseModel):
    reason: str
    "Your reasoning for drafting the player."

    player_id: int
    "Id of player drafted."

    player_name: str
    "Name of player drafted."

    #player: Optional[Player]
    #"The player drafted."