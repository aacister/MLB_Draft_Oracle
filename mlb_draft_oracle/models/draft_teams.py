from typing import List
from models.teams import Team
from utils.util import Position
from data.sqlite.database import read_draft_teams, write_draft_teams
from data.postgresql.main import read_postgres_draft_teams, write_postgres_draft_teams
from utils.util import  draft_strategy_set
from pydantic import BaseModel, Field
from templates.templates import team_name_generator_message
from draft_agents.team_name_generator.team_name_generator_agent import get_team_name_generator
from draft_agents.team_name_generator.team_name_data import TeamNameData
from agents import Runner
import random
import os

if os.getenv("DEPLOYMENT_ENVIRONMENT") == 'DEV':
    use_local_db = True
else: 
    use_local_db = False

class DraftTeams(BaseModel):
    draft_id: str = Field(description="Id of the draft.")
    teams: List[Team] = Field(description="Teams in draft.")

    @classmethod
    async def get(cls, id: str, num_teams):
        import ast
        if use_local_db:
            fields = read_draft_teams(id.lower())
        else:
            fields = read_postgres_draft_teams(id.lower())
        if not fields:
            print(f"Initializing teams in DraftTeams model...")
            teams = await initialize_teams(num_teams)
            fields = {
                "draft_id": id.lower(),
                "teams": [team.model_dump(by_alias=True) if hasattr(team, 'model_dump') else team for team in teams],
            }
            if use_local_db:
                write_draft_teams(id.lower(), fields)
            else:
                write_postgres_draft_teams(id.lower(), fields)
        # Ensure teams are Team objects, not dicts or strings
        if fields and isinstance(fields.get("teams", None), list):
            from models.teams import Team
            new_teams = []
            for team in fields["teams"]:
                if isinstance(team, dict):
                    new_teams.append(Team(**team))
                elif isinstance(team, str):
                    try:
                        team_dict = ast.literal_eval(team)
                        if isinstance(team_dict, dict):
                            new_teams.append(Team(**team_dict))
                        else:
                            # fallback: skip or handle error
                            pass
                    except Exception:
                        # fallback: skip or handle error
                        pass
                else:
                    new_teams.append(team)
            fields["teams"] = new_teams
        if "draft_id" not in fields and "id" in fields:
            fields["draft_id"] = fields.pop("id")
        return cls(**fields)
    
    def save(self):
        data = self.model_dump(by_alias=True)
        if use_local_db:
            write_draft_teams(self.name.lower(), data)
        else:
            write_postgres_draft_teams(self.name.lower(), data)
    
async def initialize_teams( num_of_teams: int) -> List[Team]:

    teams = []
    roster_dict = {
    Position.CATCHER: None,
    Position.FIRST_BASE: None,
    # Position.SECOND_BASE: None,
    # Position.SHORTSOP: None,
    # Position.THIRD_BASE: None,
    Position.OUTFIELD: None,
    # Position.LEFT_FIELD: None,
    # Position.CENTER_FIELD: None,
    # Position.RIGHT_FIELD: None,
    Position.PITCHER: None
}
    team_name_generator_agent = await get_team_name_generator(num_of_teams)
    message = team_name_generator_message(num_of_teams=num_of_teams)
    result = await Runner.run(team_name_generator_agent, message)
    if(result.final_output and isinstance(result.final_output, TeamNameData)):
        for team_name in result.final_output.names:
            print(f"team name: {team_name}")
            strategies = tuple(draft_strategy_set)
            teamStrategy = random.choice(strategies)
            teams.append(Team(name=f"{team_name}", strategy=teamStrategy, roster=roster_dict, drafted_players=[]))
    
    else:
        print("unexpected  agent output format for team names.")
    return teams       