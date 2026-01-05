from pydantic import BaseModel, Field
from backend.models.player_stats import PlayerStatistics
from backend.data.postgresql.unified_db import read_player, write_player
#from backend.data.postgresql.main import read_postgres_player, write_postgres_player
import os


class Player(BaseModel):
    id: int = Field(description="Id of the player")
    name: str = Field(description="Name of the player")
    team: str = Field(description="player's Major League Baseball team")
    position: str = Field(description="Baseball position the player plays")
    stats: PlayerStatistics = Field(description="Statistics of the player")
    is_drafted: bool = Field(default=False, description="Has the player been drafted in the league")

    @classmethod
    def from_dict(cls, data):
        stats = data["stats"]
        if isinstance(stats, dict):
            stats = PlayerStatistics(**stats)
        return cls(
            id=data["id"],
            name=data["name"],
            position=data["position"],
            team=data["team"],
            stats=stats,
            is_drafted=data.get("is_drafted", False)
        )
    
    @classmethod
    def get(cls, id: int):
        fields = read_player(id)
        if not fields:
            fields = {
                "id": id,
                "name": "",
                "position": "",
                "team": "",
                "stats": {},
                "is_drafted": False
            }
            #if use_local_db:
            write_player(id, fields)
    #        else:
    #            write_postgres_player(id, fields)
        return cls.from_dict(fields)
    
    def save(self):
        data = self.model_dump(by_alias=True)
        write_player(self.id, data)

    def mark_drafted(self):
        self.is_drafted = True
        self.save()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'team': self.team,
            'position': self.position,
            'stats': self.stats.to_dict() if hasattr(self.stats, 'to_dict') else vars(self.stats),
            'is_drafted': self.is_drafted
        }

