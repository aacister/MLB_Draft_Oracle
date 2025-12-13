from typing import Dict, List, Optional
import json
from pydantic import BaseModel, Field
from backend.utils.util import Position, NO_OF_TEAMS, NO_OF_ROUNDS
from backend.models.players import Player
from backend.data.sqlite.database import write_team, read_team
#from backend.data.postgresql.main import write_postgres_team, read_postgres_team
from agents import Agent,  Runner, trace
from contextlib import AsyncExitStack
from agents.mcp import MCPServerStdio, MCPServerStreamableHttp
from backend.config.mcp_params import drafter_mcp_server_params, researcher_mcp_server_params
from backend.templates.templates import  team_instructions,  team_message, team_input, drafter_instructions, researcher_instructions, drafter_agent_instructions, researcher_agent_instructions
from backend.mcp_clients.draft_client import get_draft_tools, read_team_roster_resource, read_draft_player_pool_available_resource
from backend.draft_agents.research_agents.researcher_tool import get_researcher_tool, get_researcher
import math
import os

MAX_TURNS = 15
#if os.getenv("DEPLOYMENT_ENVIRONMENT") == 'DEV':
#    use_local_db = True
#else: 
#    use_local_db = False
use_local_db = True

class TeamContext(BaseModel):
    draft_id: str
    team_name: str
    strategy: str
    needed_positions: str
    available_players: str
    round: int
    pick: int

class Team(BaseModel):
    name: str = Field(description="Name of the team.")
    strategy: str = Field(description="Stategy of the team")
    roster: Dict[str, Optional[Player]] = Field(description="team's roster of positions and player drafted for respective position ")
    drafted_players: List[Player] = Field(description="List of players drafted by team")
    #_agent: Optional[Agent] = PrivateAttr(default=None)

    @classmethod
    def from_dict(cls, data):
        roster = {}
        for pos_str, player_dict in data.get("roster", {}).items():
            pos = Position(pos_str) if pos_str in Position._value2member_map_ else pos_str
            player = Player.from_dict(player_dict) if player_dict else None
            roster[pos] = player
        drafted_players = [Player.from_dict(p) for p in data.get("drafted_players", [])]
        return cls(
            name=data["name"],
            strategy=data["strategy"],
            roster=roster,
            drafted_players=drafted_players
        )

    @classmethod
    def get(cls, name: str):
    #    if use_local_db:
        fields = read_team(name.lower())
    #    else: 
    #        fields = read_postgres_team(name.lower())
        if not fields:
            fields = {
                "name": name.lower(),
                "strategy": "",
                "roster": {},
                "drafted_players": []
            }
            #if use_local_db:
            write_team(name, fields)
            #else:
    #            write_postgres_team(name, fields)
        return cls.from_dict(fields)

    def get_needed_positions(self) -> set:
        return {key for key, value in self.roster.items() if value is None}
        
    def get_strategy(self) -> str:
        return self.strategy
    
    def save(self):
        #if use_local_db:
        write_team(self.name.lower(), self.to_dict())
        #else:
    #        write_postgres_team(self.name.lower(), self.to_dict())

    
    def get_roster(self) -> Dict[str, Optional[Player]]:
        return self.roster
        
    async def reportRoster(self) -> str:
        data = {pos: player.to_dict() if player else None for pos, player in self.roster.items()}
        return json.dumps(data)
    
    async def _create_agent(self, agent_name, mcp_servers, tools, handoffs, instructions) -> Agent:
        #research_tool = await get_researcher_tool(researcher_mcp_servers)
        #draft_tools = await get_draft_tools()
        self._agent = Agent(
            name=agent_name,
            instructions=instructions,
            model="gpt-4o-mini", 
            #tools=[research_tool] + draft_tools,
            tools=tools,
            mcp_servers=mcp_servers,
            handoffs=handoffs        
        )
        return self._agent
    
    async def research_test(self):
        research_question = "What's the latest news in fantasy baseball?"
        async with AsyncExitStack() as stack:
            researcher_mcp_servers = [await stack.enter_async_context(MCPServerStdio(params=params, client_session_timeout=30)) for params in researcher_mcp_server_params]
            '''
            researcher_mcp_servers = [await stack.enter_async_context(MCPServerStreamableHttp(name="Brave Search MCP Server",
                        params={
                            "url": "http://brave-search:8081/mcp",  # Adjust if using a different port or host
                            "headers": {},  # No auth needed by default; add if customized
                            "timeout": 30,  # Increase for complex searches
                        },
                        cache_tools_list=True))]
            '''
            if not researcher_mcp_servers:
                raise Exception("Failed to initialize MCP server: researcher_mcp_servers.")
            researcher = await get_researcher(researcher_mcp_servers)
            with trace("Researcher"):
                result = await Runner.run(researcher, research_question)
                print(result.final_output)

          

    async def select_player(self, draft, round: int, pick: int) -> str:
        if draft.is_complete:
            return "Draft is complete"
        with trace(f"{self.name}-drafting Round: {round} Pick: {pick}"):
            #await self.research_test()
            async with AsyncExitStack() as stack:
                drafter_mcp_servers = [await stack.enter_async_context(MCPServerStdio(params=params, cache_tools_list=False)) for params in drafter_mcp_server_params]
                if not drafter_mcp_servers:
                    raise Exception("Failed to initialize MCP server: drafter_mcp_servers.")
                async with AsyncExitStack() as stack:
                    researcher_mcp_servers = [await stack.enter_async_context(MCPServerStdio(params=params)) for params in researcher_mcp_server_params]
                    '''
                    researcher_mcp_servers = [await stack.enter_async_context(MCPServerStreamableHttp(
                        name="Brave Search MCP Server",
                        params={
                            "url": "http://brave_search:8081/mcp",
                            "headers": {},
                            "timeout": 30,
                        },
                        cache_tools_list=True
                    ))]
                    '''
                    strategy = self.get_strategy()

                    roster_json = await read_team_roster_resource(draft.id.lower(), self.name.lower() )
                    roster = json.loads(roster_json) if isinstance(roster_json, str) else roster_json
                    needed_positions_set = {key for key, value in roster.items() if value is None}
                    needed_positions = ','.join(map(str, needed_positions_set))
                    player_pool_json = await read_draft_player_pool_available_resource(draft.id.lower())

                    draft_tools = await get_draft_tools()
                    drafter_message = drafter_agent_instructions(draft_id=draft.id, team_name=self.name, strategy=strategy, needed_positions=needed_positions, availale_players=player_pool_json, round=round, pick=pick)
                    researcher_message = researcher_agent_instructions(draft_id=draft.id, team_name=self.name, strategy=strategy, needed_positions=needed_positions, available_players=player_pool_json)
                    
                    # Create agents without handoffs - we'll handle the flow manually
                    drafter_agent = await self._create_agent(agent_name="Drafter", mcp_servers=drafter_mcp_servers, tools=draft_tools, handoffs=[], instructions=drafter_message)
                    research_tool = await get_researcher_tool(researcher_mcp_servers)
                    research_tools = [research_tool]
                    research_agent = await self._create_agent(agent_name="Researcher", mcp_servers=researcher_mcp_servers, tools=research_tools, handoffs=[], instructions=researcher_message)
                    
                    # message = team_message(draft_id=draft.id.lower(), team_name=self.name, strategy=strategy, needed_positions=needed_positions, availale_players=available_players, round=round, pick=pick)
                    team_context = TeamContext(draft_id=draft.id.lower(), team_name=self.name, strategy=strategy, needed_positions=needed_positions, available_players=player_pool_json, round=round, pick=pick )
                    
                    # First, run the researcher to get player recommendations
                    researcher_result = await Runner.run(
                        starting_agent=research_agent,
                        input=team_input(),
                        context=team_context,
                        max_turns=MAX_TURNS
                    )
                    
                    print(f"Researcher output: {researcher_result.final_output}")
                    
                    # Then run the drafter with the researcher's output
                    drafter_result = await Runner.run(
                        starting_agent=drafter_agent,
                        input=f"Researcher recommendations: {researcher_result.final_output}",
                        context=team_context,
                        max_turns=MAX_TURNS
                    )
                    
                    roster_with_selected_player = await read_team_roster_resource(draft.id.lower(), self.name.lower() )
                    print(f"Team {self.name} roster: {roster_with_selected_player}")
                    print(f"Drafter output: {drafter_result.final_output}")
                    
                  
                    return str(drafter_result.final_output)
            
    def to_dict(self):
        return {
            'name': self.name,
            'strategy': self.strategy,
            'roster': {pos: player.to_dict() if player else None for pos, player in self.roster.items()},
            'drafted_players': [player.to_dict() for player in self.drafted_players]
        }
    
    