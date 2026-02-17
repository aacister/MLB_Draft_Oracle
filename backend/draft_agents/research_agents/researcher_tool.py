from agents import Agent, Tool
from backend.templates.templates import researcher_instructions,  research_tool

async def get_researcher(mcp_servers) -> Agent:
    researcher = Agent(
        name="Researcher",
        instructions=researcher_instructions(),
        model="gpt-4o-mini",
        mcp_servers=mcp_servers,
    )
    return researcher

async def get_researcher_tool(mcp_servers) -> Tool:
    researcher = await get_researcher(mcp_servers)
    return researcher.as_tool(
            tool_name="Researcher",
            tool_description=research_tool()
        )