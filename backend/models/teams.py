from typing import Dict, List, Optional
import json
from pydantic import BaseModel, Field
from backend.utils.util import Position, NO_OF_TEAMS, NO_OF_ROUNDS
from backend.models.players import Player
from backend.data.postgresql.unified_db import write_team, read_team
from agents import Agent, Runner, trace
from contextlib import AsyncExitStack
from backend.templates.templates import team_input, drafter_agent_instructions, researcher_agent_instructions
from backend.mcp_clients.draft_client import get_draft_tools, read_team_roster_resource, read_draft_player_pool_available_resource
import math
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

RESEARCHER_MAX_TURNS = 15
DRAFTER_MAX_TURNS = 15

# Detect if running in Lambda environment
IS_LAMBDA = os.path.exists("/var/task") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")

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
    
    async def _create_agent(self, agent_name, tools, instructions) -> Agent:
        """Create agent without MCP servers (tools provide MCP functionality)"""
        self._agent = Agent(
            name=agent_name,
            instructions=instructions,
            model="gpt-4o-mini", 
            tools=tools,
        )
        return self._agent

    async def select_player(self, draft, round: int, pick: int) -> str:
        """Select player for team - uses Lambda MCP clients in Lambda, stdio in local dev"""
        logger.info(f"Team {self.name} selecting player in Round {round}, Pick {pick}")
        if draft.is_complete:
            return "Draft is complete"
        
        with trace(f"{self.name}-drafting Round: {round} Pick: {pick}"):
            try:
                # Get draft context
                strategy = self.get_strategy()
                roster_json = await read_team_roster_resource(draft.id.lower(), self.name.lower())
                roster = json.loads(roster_json) if isinstance(roster_json, str) else roster_json
                needed_positions_set = {key for key, value in roster.items() if value is None}
                needed_positions = ','.join(map(str, needed_positions_set))
                player_pool_json = await read_draft_player_pool_available_resource(draft.id.lower())

                # Prepare agent instructions
                drafter_message = drafter_agent_instructions(
                    draft_id=draft.id, 
                    team_name=self.name, 
                    strategy=strategy, 
                    needed_positions=needed_positions, 
                    availale_players=player_pool_json, 
                    round=round, 
                    pick=pick
                )
                researcher_message = researcher_agent_instructions(
                    draft_id=draft.id, 
                    team_name=self.name, 
                    strategy=strategy, 
                    needed_positions=needed_positions, 
                    available_players=player_pool_json
                )
                
                team_context = TeamContext(
                    draft_id=draft.id.lower(), 
                    team_name=self.name, 
                    strategy=strategy, 
                    needed_positions=needed_positions, 
                    available_players=player_pool_json, 
                    round=round, 
                    pick=pick
                )

                if IS_LAMBDA:
                    # Lambda environment - use Lambda MCP clients (no stdio)
                    logger.info("[select_player] Using Lambda MCP clients")
                    
                    # Import Lambda MCP clients
                    from backend.mcp_clients.lambda_mcp_client import (
                        get_draft_mcp_client,
                        get_knowledgebase_mcp_client,
                        get_brave_search_mcp_client
                    )
                    
                    # Initialize clients (these are lightweight objects, not servers)
                    draft_client = get_draft_mcp_client()
                    kb_client = get_knowledgebase_mcp_client()
                    search_client = get_brave_search_mcp_client()
                    
                    logger.info("[select_player] Lambda MCP clients initialized")
                    
                    # Get draft tools (these use Lambda MCP clients internally)
                    draft_tools = await get_draft_tools()
                    
                    # Create drafter agent with tools only (no MCP servers)
                    drafter_agent = await self._create_agent(
                        agent_name="Drafter",
                        tools=draft_tools,
                        instructions=drafter_message
                    )
                    
                    # For researcher, we can use knowledge base tools if needed
                    # For now, create a simple researcher agent
                    from backend.mcp_clients.knowledgebase_client import get_knowledgebase_tools
                    
                    try:
                        kb_tools = await get_knowledgebase_tools()
                        researcher_tools = kb_tools
                    except Exception as e:
                        logger.warning(f"Could not get knowledge base tools: {e}")
                        researcher_tools = []
                    
                    researcher_agent = await self._create_agent(
                        agent_name="Researcher",
                        tools=researcher_tools,
                        instructions=researcher_message
                    )
                    
                    # Run researcher
                    logger.info("[select_player] Running Researcher agent...")
                    researcher_result = await Runner.run(
                        starting_agent=researcher_agent,
                        input=team_input(),
                        context=team_context,
                        max_turns=RESEARCHER_MAX_TURNS
                    )
                    
                    logger.info(f"[select_player] Researcher output: {researcher_result.final_output}")
                    
                    # Run drafter
                    logger.info("[select_player] Running Drafter agent...")
                    drafter_result = await Runner.run(
                        starting_agent=drafter_agent,
                        input=f"Researcher recommendations: {researcher_result.final_output}",
                        context=team_context,
                        max_turns=DRAFTER_MAX_TURNS
                    )
                    
                    roster_with_selected_player = await read_team_roster_resource(draft.id.lower(), self.name.lower())
                    logger.info(f"Team {self.name} roster updated: {roster_with_selected_player}")
                    logger.info(f"Drafter output: {drafter_result.final_output}")
                    
                    return str(drafter_result.final_output)
                
                else:
                    # Local development - use stdio MCP servers
                    logger.info("[select_player] Using stdio MCP servers (local dev)")
                    
                    from agents.mcp import MCPServerStdio
                    from backend.config.mcp_params import drafter_mcp_server_params, researcher_mcp_server_params
                    from backend.draft_agents.research_agents.researcher_tool import get_researcher_tool
                    
                    async with AsyncExitStack() as stack:
                        # Initialize drafter MCP servers
                        drafter_mcp_servers = []
                        for i, params in enumerate(drafter_mcp_server_params):
                            logger.info(f"[select_player] Starting Drafter MCP server {i+1}...")
                            server = MCPServerStdio(params=params)
                            await stack.enter_async_context(server)
                            drafter_mcp_servers.append(server)
                            logger.info(f"[select_player] Drafter MCP server {i+1} started")
                        
                        # Initialize researcher MCP servers
                        researcher_mcp_servers = []
                        for i, params in enumerate(researcher_mcp_server_params):
                            logger.info(f"[select_player] Starting Researcher MCP server {i+1}...")
                            server = MCPServerStdio(params=params)
                            await stack.enter_async_context(server)
                            researcher_mcp_servers.append(server)
                            logger.info(f"[select_player] Researcher MCP server {i+1} started")
                        
                        logger.info("[select_player] All MCP servers initialized successfully")
                        
                        # Get draft tools
                        draft_tools = await get_draft_tools()
                        
                        # Create drafter agent with MCP servers
                        drafter_agent = Agent(
                            name="Drafter",
                            instructions=drafter_message,
                            model="gpt-4o-mini",
                            tools=draft_tools,
                            mcp_servers=drafter_mcp_servers,
                        )
                        
                        # Create researcher agent
                        research_tool = await get_researcher_tool(researcher_mcp_servers)
                        research_agent = Agent(
                            name="Researcher",
                            instructions=researcher_message,
                            model="gpt-4o-mini",
                            tools=[research_tool],
                            mcp_servers=researcher_mcp_servers,
                        )
                        
                        # Run researcher
                        logger.info("[select_player] Running Researcher agent...")
                        researcher_result = await Runner.run(
                            starting_agent=research_agent,
                            input=team_input(),
                            context=team_context,
                            max_turns=RESEARCHER_MAX_TURNS
                        )
                        
                        logger.info(f"[select_player] Researcher output: {researcher_result.final_output}")
                        
                        # Run drafter
                        logger.info("[select_player] Running Drafter agent...")
                        drafter_result = await Runner.run(
                            starting_agent=drafter_agent,
                            input=f"Researcher recommendations: {researcher_result.final_output}",
                            context=team_context,
                            max_turns=DRAFTER_MAX_TURNS
                        )
                        
                        roster_with_selected_player = await read_team_roster_resource(draft.id.lower(), self.name.lower())
                        logger.info(f"Team {self.name} roster updated: {roster_with_selected_player}")
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