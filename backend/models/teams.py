from typing import Dict, List, Optional
import json
from pydantic import BaseModel, Field
from backend.utils.util import Position, NO_OF_TEAMS, NO_OF_ROUNDS
from backend.models.players import Player
from backend.data.postgresql.unified_db import write_team, read_team
from agents import Agent,  Runner, trace
from contextlib import AsyncExitStack
from agents.mcp import MCPServerStdio, MCPServerStreamableHttp
from backend.config.mcp_params import drafter_mcp_server_params, researcher_mcp_server_params, knowledgebase_mcp_server_params
from backend.templates.templates import  team_instructions,  team_message, team_input, drafter_instructions, researcher_instructions, drafter_agent_instructions, researcher_agent_instructions
from backend.mcp_clients.draft_client import get_draft_tools, read_team_roster_resource, read_draft_player_pool_available_resource
from backend.mcp_clients.knowledgebase_client import get_knowledgebase_tools
from backend.draft_agents.research_agents.researcher_tool import get_researcher_tool, get_researcher
import math
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

RESEARCHER_MAX_TURNS = 15
DRAFTER_MAX_TURNS = 15

# CRITICAL: Increase MCP connection timeout for Lambda cold starts
# Lambda containers take longer to spawn subprocesses
MCP_INIT_TIMEOUT = 60  # seconds (increased from default 5)

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
        """Get team from PostgreSQL RDS"""
        logger.info(f"Loading team {name} from PostgreSQL RDS")
        fields = read_team(name.lower())
        if not fields:
            fields = {
                "name": name.lower(),
                "strategy": "",
                "roster": {},
                "drafted_players": []
            }
            write_team(name, fields)
            logger.info(f"Initialized empty team {name} in PostgreSQL RDS")
        return cls.from_dict(fields)

    def get_needed_positions(self) -> set:
        return {key for key, value in self.roster.items() if value is None}
        
    def get_strategy(self) -> str:
        return self.strategy
    
    def save(self):
        """Save team to PostgreSQL RDS"""
        write_team(self.name.lower(), self.to_dict())
        logger.debug(f"Saved team {self.name} to PostgreSQL RDS")

    def get_roster(self) -> Dict[str, Optional[Player]]:
        return self.roster
        
    async def reportRoster(self) -> str:
        data = {pos: player.to_dict() if player else None for pos, player in self.roster.items()}
        return json.dumps(data)
    
    async def _create_agent(self, agent_name, mcp_servers, tools, handoffs, instructions) -> Agent:
        self._agent = Agent(
            name=agent_name,
            instructions=instructions,
            model="gpt-4o-mini", 
            tools=tools,
            mcp_servers=mcp_servers,
            handoffs=handoffs        
        )
        return self._agent
    
    async def _init_mcp_server_with_timeout(self, stack, params, server_name):
        """
        Initialize MCP server with custom timeout.
        The MCP client has a hardcoded 5s timeout, but Lambda needs more time.
        """
        logger.info(f"[_init_mcp_server] Starting {server_name} MCP server (timeout: {MCP_INIT_TIMEOUT}s)...")
        
        try:
            # Create the MCP server with extended timeout in environment
            # Note: This sets it at the subprocess level
            server = MCPServerStdio(params=params)
            
            # Override the session timeout by waiting longer
            async with asyncio.timeout(MCP_INIT_TIMEOUT):
                await stack.enter_async_context(server)
                logger.info(f"[_init_mcp_server] ✓ {server_name} MCP server initialized successfully")
                return server
                
        except asyncio.TimeoutError:
            logger.error(f"[_init_mcp_server] ✗ {server_name} MCP server timeout after {MCP_INIT_TIMEOUT}s")
            raise Exception(f"{server_name} MCP server failed to start within {MCP_INIT_TIMEOUT}s")
        except Exception as e:
            logger.error(f"[_init_mcp_server] ✗ {server_name} MCP server error: {e}", exc_info=True)
            raise

    async def select_player(self, draft, round: int, pick: int) -> str:
        """Select player for team - saves to PostgreSQL RDS"""
        logger.info(f"Team {self.name} selecting player in Round {round}, Pick {pick}")
        if draft.is_complete:
            return "Draft is complete"
        
        with trace(f"{self.name}-drafting Round: {round} Pick: {pick}"):
            async with AsyncExitStack() as stack:
                try:
                    logger.info("[select_player] Initializing MCP servers with extended timeout...")
                    
                    # Initialize drafter MCP servers
                    drafter_mcp_servers = []
                    for i, params in enumerate(drafter_mcp_server_params):
                        server = await self._init_mcp_server_with_timeout(
                            stack, params, f"Drafter-{i+1}"
                        )
                        drafter_mcp_servers.append(server)
                    
                    if not drafter_mcp_servers:
                        raise Exception("Failed to initialize drafter MCP servers")
                    
                    # Initialize researcher MCP servers
                    researcher_mcp_servers = []
                    for i, params in enumerate(researcher_mcp_server_params):
                        server = await self._init_mcp_server_with_timeout(
                            stack, params, f"Researcher-{i+1}"
                        )
                        researcher_mcp_servers.append(server)
                    
                    if not researcher_mcp_servers:
                        raise Exception("Failed to initialize researcher MCP servers")
                    
                    logger.info("[select_player] ✓ All MCP servers initialized successfully")
                    
                    strategy = self.get_strategy()

                    roster_json = await read_team_roster_resource(draft.id.lower(), self.name.lower())
                    roster = json.loads(roster_json) if isinstance(roster_json, str) else roster_json
                    needed_positions_set = {key for key, value in roster.items() if value is None}
                    needed_positions = ','.join(map(str, needed_positions_set))
                    player_pool_json = await read_draft_player_pool_available_resource(draft.id.lower())

                    draft_tools = await get_draft_tools()
                    drafter_message = drafter_agent_instructions(draft_id=draft.id, team_name=self.name, strategy=strategy, needed_positions=needed_positions, availale_players=player_pool_json, round=round, pick=pick)
                    researcher_message = researcher_agent_instructions(draft_id=draft.id, team_name=self.name, strategy=strategy, needed_positions=needed_positions, available_players=player_pool_json)
                    
                    # Create drafter agent
                    drafter_agent = await self._create_agent(agent_name="Drafter", mcp_servers=drafter_mcp_servers, tools=draft_tools, handoffs=[], instructions=drafter_message)
                    
                    # Create researcher agent with web search tools
                    research_tool = await get_researcher_tool(researcher_mcp_servers)
                    research_tools = [research_tool]
                    
                    research_agent = await self._create_agent(agent_name="Researcher", mcp_servers=researcher_mcp_servers, tools=research_tools, handoffs=[], instructions=researcher_message)
                    
                    team_context = TeamContext(draft_id=draft.id.lower(), team_name=self.name, strategy=strategy, needed_positions=needed_positions, available_players=player_pool_json, round=round, pick=pick)
                    
                    # First, run the researcher to get player recommendations
                    logger.info("[select_player] Running Researcher agent...")
                    researcher_result = await Runner.run(
                        starting_agent=research_agent,
                        input=team_input(),
                        context=team_context,
                        max_turns=RESEARCHER_MAX_TURNS
                    )
                    
                    logger.info(f"[select_player] Researcher output: {researcher_result.final_output}")
                    
                    # Then run the drafter with the researcher's output
                    logger.info("[select_player] Running Drafter agent...")
                    drafter_result = await Runner.run(
                        starting_agent=drafter_agent,
                        input=f"Researcher recommendations: {researcher_result.final_output}",
                        context=team_context,
                        max_turns=DRAFTER_MAX_TURNS
                    )
                    
                    roster_with_selected_player = await read_team_roster_resource(draft.id.lower(), self.name.lower())
                    logger.info(f"Team {self.name} roster updated in PostgreSQL RDS: {roster_with_selected_player}")
                    logger.info(f"Drafter output: {drafter_result.final_output}")
                    
                    return str(drafter_result.final_output)
                
                except Exception as e:
                    logger.error(f"[select_player] Error: {e}", exc_info=True)
                    raise
            
    def to_dict(self):
        return {
            'name': self.name,
            'strategy': self.strategy,
            'roster': {pos: player.to_dict() if player else None for pos, player in self.roster.items()},
            'drafted_players': [player.to_dict() for player in self.drafted_players]
        }