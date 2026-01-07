from typing import List
from backend.models.teams import Team
from backend.utils.util import Position
from backend.data.postgresql.unified_db import read_draft_teams, write_draft_teams
from backend.utils.util import  draft_strategy_set
from pydantic import BaseModel, Field
from backend.templates.templates import team_name_generator_message
from backend.draft_agents.team_name_generator.team_name_generator_agent import get_team_name_generator
from backend.draft_agents.team_name_generator.team_name_data import TeamNameData
from agents import Runner
import random
import logging

logger = logging.getLogger(__name__)


class DraftTeams(BaseModel):
    draft_id: str = Field(description="Id of the draft.")
    teams: List[Team] = Field(description="Teams in draft.")

    @classmethod
    async def get(cls, id: str, num_teams):
        """Get draft teams from PostgreSQL RDS"""
        import ast
        logger.info(f"Loading draft teams for {id} from PostgreSQL RDS")
        fields = read_draft_teams(id.lower())
        
        if not fields:
            logger.info(f"Initializing teams in DraftTeams model for draft {id}")
            teams = await initialize_teams(num_teams)
            fields = {
                "draft_id": id.lower(),
                "teams": [team.model_dump(by_alias=True) if hasattr(team, 'model_dump') else team for team in teams],
            }
            write_draft_teams(id.lower(), fields)
            logger.info(f"Saved {len(teams)} teams to PostgreSQL RDS for draft {id}")
        
        # Ensure teams are Team objects, not dicts or strings
        if fields and isinstance(fields.get("teams", None), list):
            from backend.models.teams import Team
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
                            pass
                    except Exception as e:
                        logger.error(f"Error parsing team: {e}")
                        pass
                elif isinstance(team, Team):
                    new_teams.append(team)
                else:
                    logger.warning(f"Unexpected team type: {type(team)}")
            fields["teams"] = new_teams
        
        # Ensure draft_id field exists
        if "draft_id" not in fields and "id" in fields:
            fields["draft_id"] = fields.pop("id")
        elif "draft_id" not in fields:
            fields["draft_id"] = id.lower()
        
        # Validate we have teams
        if not fields.get("teams"):
            logger.warning(f"No teams found for draft {id}, reinitializing...")
            teams = await initialize_teams(num_teams)
            fields["teams"] = teams
            write_draft_teams(id.lower(), fields)
        
        logger.info(f"Loaded {len(fields['teams'])} teams from PostgreSQL RDS for draft {id}")
        return cls(**fields)
    
    def save(self):
        """Save draft teams to PostgreSQL RDS"""
        data = self.model_dump(by_alias=True)
        write_draft_teams(self.draft_id.lower(), data)
        logger.debug(f"Saved draft teams to PostgreSQL RDS for draft {self.draft_id}")
    
async def initialize_teams(num_of_teams: int) -> List[Team]:
    """Initialize teams for a new draft"""
    logger.info(f"Initializing {num_of_teams} teams")
    teams = []
    roster_dict = {
        Position.CATCHER: None,
        Position.FIRST_BASE: None,
        Position.OUTFIELD: None,
        Position.PITCHER: None
    }
    team_name_generator_agent = await get_team_name_generator(num_of_teams)
    message = team_name_generator_message(num_of_teams=num_of_teams)
    result = await Runner.run(team_name_generator_agent, message)
    if(result.final_output and isinstance(result.final_output, TeamNameData)):
        for team_name in result.final_output.names:
            logger.info(f"Generated team name: {team_name}")
            strategies = tuple(draft_strategy_set)
            teamStrategy = random.choice(strategies)
            teams.append(Team(name=f"{team_name}", strategy=teamStrategy, roster=roster_dict, drafted_players=[]))
        
    else:
        logger.error("Unexpected agent output format for team names")
    
    logger.info(f"Successfully initialized {len(teams)} teams")
    return teams