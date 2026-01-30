from typing import Dict, List, Optional
import json
from pydantic import BaseModel, Field
from backend.utils.util import Position, NO_OF_TEAMS, NO_OF_ROUNDS
from backend.models.players import Player
from backend.data.postgresql.unified_db import write_team, read_team
from agents import FunctionTool, Agent, Runner, trace
from contextlib import AsyncExitStack
from backend.templates.templates import team_input, drafter_agent_instructions, researcher_agent_instructions
from backend.mcp_clients.draft_client import get_draft_tools, read_team_roster_resource, read_draft_player_pool_available_resource
import math
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

RESEARCHER_MAX_TURNS = 30
DRAFTER_MAX_TURNS = 100

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
    strategy: str = Field(description="Strategy of the team")
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
        """Create agent with tools"""
        logger.info(f"[_create_agent] Creating agent '{agent_name}' with {len(tools)} tools")
        
        # Log tool names for debugging
        tool_names = []
        for tool in tools:
            if isinstance(tool, dict):
                name = tool.get('function', {}).get('name', 'unknown')
            else:
                name = getattr(tool, 'name', 'unknown')
            tool_names.append(name)
        
        logger.info(f"[_create_agent] Tool names: {tool_names}")
        
        self._agent = Agent(
            name=agent_name,
            instructions=instructions,
            model="gpt-4o-mini",  
            tools=tools,
        )
        return self._agent

    async def select_player(self, draft, round: int, pick: int) -> str:
        """Select player for team - uses Lambda MCP invokers in Lambda, stdio in local dev"""
        logger.info(f"Team {self.name} selecting player in Round {round}, Pick {pick}")
        if draft.is_complete:
            return "Draft is complete"
        
        with trace(f"{self.name}-drafting Round: {round} Pick: {pick}"):
            try:
                # Get draft context
                strategy = self.get_strategy()
                roster_json = await read_team_roster_resource(draft.id.lower(), self.name.lower())
                
                # Handle empty roster
                if not roster_json or (isinstance(roster_json, str) and roster_json.strip() == ""):
                    logger.info(f"Empty roster - using empty roster")
                    roster = {"roster": []}
                else:
                    try:
                        roster = json.loads(roster_json) if isinstance(roster_json, str) else roster_json
                        logger.info(f"✓ Successfully parsed roster JSON")
                    except json.JSONDecodeError as e:
                        logger.error(f"✗ Invalid JSON in roster: {e}")
                        roster = {"roster": []}
                
                needed_positions_set = {key for key, value in roster.items() if value is None}
                needed_positions = ','.join(map(str, needed_positions_set))
                # TEMPORARY FIX: Read player pool directly from database instead of MCP resource
               
                logger.info("[select_player] ===== LOADING PLAYER POOL DIRECTLY =====")

                try:
                    if draft.player_pool and hasattr(draft.player_pool, 'players'):
                        all_players = draft.player_pool.players
                        logger.info(f"[select_player] Total players in pool: {len(all_players)}")
                        
                        # Filter to undrafted players
                        available_players = [p for p in all_players if not p.is_drafted]
                        logger.info(f"[select_player] Available players: {len(available_players)}")
                        
                        # Convert to SIMPLE JSON (name + position only to save tokens)
                        players_data = []
                        for p in available_players:
                            # MINIMAL data to stay under token limit
                            player_dict = {
                                "name": p.name,
                                "position": p.position,
                            }
                            players_data.append(player_dict)
                        
                        player_pool_json = json.dumps(players_data)
                        logger.info(f"[select_player] ✓ Player pool JSON created: {len(player_pool_json)} chars")
                        logger.info(f"[select_player] ✓ Sample players: {[p['name'] for p in players_data[:5]]}")
                    else:
                        logger.error("[select_player] ❌ Draft has no player_pool or players attribute")
                        player_pool_json = json.dumps([])
                except Exception as e:
                    logger.error(f"[select_player] ❌ Error loading player pool: {e}", exc_info=True)
                    player_pool_json = json.dumps([])

                # Parse player pool to create a simple name list for the agent
                try:
                    player_pool_data = json.loads(player_pool_json) if isinstance(player_pool_json, str) else player_pool_json
                    
                    # Create a simplified list with just names and positions for easier validation
                    if isinstance(player_pool_data, list):
                        simple_player_list = [
                            {"name": p.get("name", ""), "position": p.get("position", "")} 
                            for p in player_pool_data
                        ]
                        simple_player_list_str = json.dumps(simple_player_list, indent=2)
                        
                        logger.info(f"[select_player] Simplified player list has {len(simple_player_list)} players")
                        logger.info(f"[select_player] Sample players: {simple_player_list[:5]}")
                    else:
                        simple_player_list_str = player_pool_json
                        
                except Exception as e:
                    logger.warning(f"[select_player] Could not simplify player list: {e}")
                    simple_player_list_str = player_pool_json

                # Prepare agent instructions
                drafter_message = drafter_agent_instructions(
                    draft_id=draft.id, 
                    team_name=self.name, 
                    strategy=strategy, 
                    needed_positions=needed_positions, 
                    available_players=simple_player_list_str, 
                    round=round, 
                    pick=pick
                )
                researcher_message = researcher_agent_instructions(
                    draft_id=draft.id, 
                    team_name=self.name, 
                    strategy=strategy, 
                    needed_positions=needed_positions, 
                    available_players=simple_player_list_str
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
                    logger.info("[select_player] Using Lambda MCP invokers (separate Lambda functions)")
                    
                    from backend.mcp_clients.lambda_mcp_invoker import (
                        get_draft_mcp_invoker,
                        get_search_mcp_invoker
                    )
                    
                    # Get invokers
                    draft_invoker = get_draft_mcp_invoker()
                    search_invoker = get_search_mcp_invoker()
                    
                    logger.info("[select_player] Lambda MCP invokers initialized")
                    
                    # Get tools from MCP Lambdas
                    logger.info("[select_player] Fetching tools from MCP Lambdas...")
                    draft_tools_raw = await draft_invoker.list_tools()
                    
                    logger.info(f"[select_player] Got {len(draft_tools_raw)} draft tools from MCP Lambda")
                    logger.info(f"[select_player] Raw draft tools: {[t['name'] for t in draft_tools_raw]}")
                    
                    # Helper function to fix schema for OpenAI compatibility
                    def fix_schema_for_openai(schema):
                        """Fix schema to meet OpenAI's strict requirements"""
                        fixed_schema = schema.copy()
                        
                        # 1. Add additionalProperties: false if not present
                        if 'additionalProperties' not in fixed_schema:
                            fixed_schema['additionalProperties'] = False
                        
                        # 2. Ensure 'required' includes ALL properties (OpenAI requirement)
                        if 'properties' in fixed_schema:
                            all_property_keys = list(fixed_schema['properties'].keys())
                            if 'required' not in fixed_schema:
                                fixed_schema['required'] = all_property_keys
                            else:
                                # Merge existing required with all properties
                                existing_required = set(fixed_schema['required'])
                                all_props = set(all_property_keys)
                                fixed_schema['required'] = list(existing_required.union(all_props))
                        
                        return fixed_schema
                    
                    # Helper function to create tool wrapper with proper closure
                    def create_tool_wrapper(invoker, tool_name):
                        """Create a tool wrapper function with proper closure binding"""
                        async def tool_function(ctx, args):
                            logger.info(f"[Tool] ===== TOOL CALLED: {tool_name} =====")
                            logger.info(f"[Tool] Args: {args}")
                            # Parse args if it's a string
                            parsed_args = json.loads(args) if isinstance(args, str) else args
                            logger.info(f"[Tool] Parsed args: {parsed_args}")
                            result = await invoker.call_tool(tool_name, parsed_args)
                            logger.info(f"[Tool] Result: {result}")
                            return result
                        return tool_function
                    
                    # Convert MCP tools to FunctionTool objects with fixed schemas
                    draft_tools = []
                    for tool_def in draft_tools_raw:
                        tool_name = tool_def['name']
                        logger.info(f"[select_player] Processing draft tool: {tool_name}")
                        
                        # Fix schema for OpenAI compatibility
                        schema = fix_schema_for_openai(tool_def['inputSchema'])
                        logger.info(f"[select_player] Fixed schema for {tool_name}: {schema}")
                        
                        # Create tool wrapper with proper closure
                        tool_wrapper = create_tool_wrapper(draft_invoker, tool_name)
                        
                        # Create FunctionTool object
                        function_tool = FunctionTool(
                            name=tool_def['name'],
                            description=tool_def['description'],
                            params_json_schema=schema,
                            on_invoke_tool=tool_wrapper
                        )
                        
                        draft_tools.append(function_tool)
                        logger.info(f"[select_player] ✓ Added draft tool: {tool_name}")
                    
                    logger.info(f"[select_player] Total draft tools: {len(draft_tools)}")
                    logger.info(f"[select_player] Draft tool names: {[t.name for t in draft_tools]}")
                    
                    # Create drafter agent with FunctionTool objects
                    logger.info(f"[select_player] Creating Drafter agent with {len(draft_tools)} tools")
                    drafter_agent = Agent(
                        name="Drafter",
                        instructions=drafter_message,
                        model="gpt-4o-mini",
                        tools=draft_tools,
                    )
                    
                    logger.info(f"[select_player] Drafter agent created. Agent tools: {getattr(drafter_agent, 'tools', 'NO TOOLS ATTR')}")
                    
                    # Get search tools
                    try:
                        search_tools_raw = await search_invoker.list_tools()
                        logger.info(f"[select_player] Got {len(search_tools_raw)} search tools")
                        logger.info(f"[select_player] Raw search tools: {[t['name'] for t in search_tools_raw]}")
                        
                        researcher_tools = []
                        for tool_def in search_tools_raw:
                            tool_name = tool_def['name']
                            logger.info(f"[select_player] Processing search tool: {tool_name}")
                            
                            # Fix schema for OpenAI compatibility
                            schema = fix_schema_for_openai(tool_def['inputSchema'])
                            logger.info(f"[select_player] Fixed schema for {tool_name}: {schema}")
                            
                            # Create tool wrapper with proper closure
                            tool_wrapper = create_tool_wrapper(search_invoker, tool_name)
                            
                            # Create FunctionTool for search
                            function_tool = FunctionTool(
                                name=tool_def['name'],
                                description=tool_def['description'],
                                params_json_schema=schema,
                                on_invoke_tool=tool_wrapper
                            )
                            
                            researcher_tools.append(function_tool)
                            logger.info(f"[select_player] ✓ Added search tool: {tool_name}")
                        
                        logger.info(f"[select_player] Total researcher tools: {len(researcher_tools)}")
                        logger.info(f"[select_player] Researcher tool names: {[t.name for t in researcher_tools]}")
                        
                    except Exception as e:
                        logger.error(f"Could not get search tools: {e}", exc_info=True)
                        researcher_tools = []
                    
                    logger.info(f"[select_player] Creating Researcher agent with {len(researcher_tools)} tools")
                    researcher_agent = Agent(
                        name="Researcher",
                        instructions=researcher_message,
                        model="gpt-4o-mini",
                        tools=researcher_tools,
                    )
                    
                    logger.info(f"[select_player] Researcher agent created. Agent tools: {getattr(researcher_agent, 'tools', 'NO TOOLS ATTR')}")
                    
                    # Run agents
                    logger.info("[select_player] ===== RUNNING RESEARCHER AGENT =====")
                    logger.info(f"[select_player] Researcher has {len(researcher_tools)} tools available")
                    researcher_result = await Runner.run(
                        starting_agent=researcher_agent,
                        input=researcher_message,
                        context=team_context,
                        max_turns=RESEARCHER_MAX_TURNS
                    )
                    
                    logger.info(f"[select_player] Researcher output: {researcher_result.final_output}")
                    
                    logger.info("[select_player] ===== RUNNING DRAFTER AGENT =====")
                    logger.info(f"[select_player] Drafter has {len(draft_tools)} tools available")
                    drafter_result = await Runner.run(
                        starting_agent=drafter_agent,
                        input=f"Researcher recommendations: {researcher_result.final_output}",
                        context=team_context,
                        max_turns=DRAFTER_MAX_TURNS
                    )
                    
                    roster_with_selected_player = await read_team_roster_resource(draft.id.lower(), self.name.lower())
                    logger.info(f"Team {self.name} roster updated: {roster_with_selected_player}")
                    logger.info(f"Drafter output: {drafter_result.final_output}")
                    # ====================================================================
                    # CHECK IF DRAFT WAS SUCCESSFUL BY COMPARING ROSTER SIZE
                    # ====================================================================
                    logger.info("[select_player] Checking if draft was successful...")

                    # Get roster before draft (we already have it as roster)
                    roster_before_count = len([v for v in roster.values() if v is not None]) if roster else 0
                    logger.info(f"[select_player] Roster count before draft: {roster_before_count}")

                    # Get roster after draft
                    roster_with_selected_player = await read_team_roster_resource(draft.id.lower(), self.name.lower())
                    try:
                        roster_after = json.loads(roster_with_selected_player) if isinstance(roster_with_selected_player, str) else roster_with_selected_player
                        roster_after_count = len([v for v in roster_after.values() if v is not None]) if roster_after else 0
                        logger.info(f"[select_player] Roster count after draft: {roster_after_count}")
                    except Exception as e:
                        logger.error(f"[select_player] Error parsing roster after draft: {e}")
                        roster_after_count = roster_before_count  # Assume no change if error

                    # Check if a player was actually drafted
                    if roster_after_count <= roster_before_count:
                        # NO PLAYER WAS DRAFTED - ALL ATTEMPTS FAILED
                        error_msg = (
                            f"DRAFT FAILED for {self.name} at Round {round}, Pick {pick}. "
                            f"Agent attempted to draft players but all 50 attempts failed. "
                            f"Drafter output: {drafter_result.final_output}"
                        )
                        logger.error(f"[select_player] {error_msg}")
                        
                        # Raise exception to stop draft execution
                        raise Exception(error_msg)

                    # Success - player was drafted
                    logger.info(f"[select_player] ✓ Draft successful! Team {self.name} roster updated")
                    logger.info(f"[select_player] Roster after: {roster_with_selected_player}")
                    logger.info(f"[select_player] Drafter output: {drafter_result.final_output}")
                    
                    return str(drafter_result.final_output)
                else:
                    # ================================================================
                    # Local development - use stdio MCP servers
                    # ================================================================
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
                            input=researcher_message,
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

                    # ====================================================================
                    # CHECK IF DRAFT WAS SUCCESSFUL BY COMPARING ROSTER SIZE
                    # ====================================================================
                    logger.info("[select_player] Checking if draft was successful...")

                    # Get roster before draft (we already have it as roster)
                    roster_before_count = len([v for v in roster.values() if v is not None]) if roster else 0
                    logger.info(f"[select_player] Roster count before draft: {roster_before_count}")

                    # Get roster after draft
                    roster_with_selected_player = await read_team_roster_resource(draft.id.lower(), self.name.lower())
                    try:
                        roster_after = json.loads(roster_with_selected_player) if isinstance(roster_with_selected_player, str) else roster_with_selected_player
                        roster_after_count = len([v for v in roster_after.values() if v is not None]) if roster_after else 0
                        logger.info(f"[select_player] Roster count after draft: {roster_after_count}")
                    except Exception as e:
                        logger.error(f"[select_player] Error parsing roster after draft: {e}")
                        roster_after_count = roster_before_count  # Assume no change if error

                    # Check if a player was actually drafted
                    if roster_after_count <= roster_before_count:
                        # NO PLAYER WAS DRAFTED - ALL ATTEMPTS FAILED
                        error_msg = (
                            f"DRAFT FAILED for {self.name} at Round {round}, Pick {pick}. "
                            f"Agent attempted to draft players but all 5 attempts failed. "
                            f"Drafter output: {drafter_result.final_output}"
                        )
                        logger.error(f"[select_player] {error_msg}")
                        
                        # Raise exception to propagate to frontend
                        raise Exception(error_msg)

                    # Success - player was drafted
                    logger.info(f"[select_player] ✓ Draft successful! Team {self.name} roster updated")
                    logger.info(f"[select_player] Roster after: {roster_with_selected_player}")
                    logger.info(f"[select_player] Drafter output: {drafter_result.final_output}")

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












