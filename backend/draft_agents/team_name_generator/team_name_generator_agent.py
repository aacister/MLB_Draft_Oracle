from agents import Agent
from backend.templates.templates import team_name_generator_instructions
from backend.draft_agents.team_name_generator.team_name_data import TeamNameData

async def get_team_name_generator(num_of_teams: int) -> Agent:
    team_name_generator_agent = Agent(
        name="TeamNameGenerator",
        instructions=team_name_generator_instructions(num_of_teams),
        model="gpt-41-mini",
        output_type=TeamNameData
    )
    return team_name_generator_agent


