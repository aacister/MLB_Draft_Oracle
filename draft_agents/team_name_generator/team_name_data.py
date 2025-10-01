from pydantic import BaseModel
from typing import List

class TeamNameData(BaseModel):
    names: List[str]
    "Name of team."

