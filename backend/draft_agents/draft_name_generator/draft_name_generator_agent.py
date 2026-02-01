from agents import Agent
from backend.templates.templates import draft_name_generator_instructions

async def get_draft_name_generator() -> Agent:
    draft_name_generator_agent = Agent(
        name="DraftNameGenerator",
        instructions=draft_name_generator_instructions(),
        model="gpt-41-mini"
    )
    return draft_name_generator_agent
