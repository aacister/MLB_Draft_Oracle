import mcp
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

params = StdioServerParameters(command="uv", args=["run", "teams_server.py"], env=None)

async def read_team_strategy_resource(name):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            session.request_timeout = 120
            await session.initialize(timeout=120)
            result = await session.read_resource(f"teams://strategy/{name}")
            return result.contents[0].text

async def read_team_needed_positions_resource(name):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            session.request_timeout = 120
            await session.initialize(timeout=120)
            result = await session.read_resource(f"teams://neededPositions/{name}")
            print(f"read_team_needed_positions_resource: {result}")
            return result.contents[0].text

async def read_team_roster_resource(name):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            session.request_timeout = 120
            await session.initialize(timeout=120)
            result = await session.read_resource(f"teams://roster/{name}")
            return result.contents[0].text
