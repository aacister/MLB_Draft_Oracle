from pydantic import BaseModel, Field
from typing import Optional

class PlayerStatistics(BaseModel):
    at_bats: int = Field(default=None, description="At bats")
    innings_pitched: str = Field(default=None, description="Innings pitched")
    r: int = Field(default=None, description="Runs")
    hr: int = Field(default=None, description="Home runs")
    rbi: int = Field(default=None, description="Runs batted in")
    sb: int = Field(default=None, description="Stolen bases")
    avg: str = Field(default=None, description="Batting average")
    obp: str = Field(default=None, description="On-base percentage")
    slg: str = Field(default=None, description="Slugging percentage")
    w: int = Field(default=None, description="Wins")
    k: int = Field(default=None, description="Strikeouts")
    era: str = Field(default=None, description="Earned run average")
    whip: str = Field(default=None, description="Walks plus hits per inning pitched")
    s: int = Field(default=None, description="Saves")

    def to_dict(self):
        return self.dict()