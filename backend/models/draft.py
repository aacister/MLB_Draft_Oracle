from pydantic import BaseModel, Field
from uuid import uuid4
import traceback
from typing import List, Optional, Dict, Tuple, Any
import json
import logging
from backend.data.postgresql.unified_db import write_draft, read_draft, read_drafts
from backend.models.players import Player
from backend.models.teams import Team
from backend.models.draft_history import DraftHistory
from backend.models.draft_teams import DraftTeams
from backend.models.draft_task import DraftTask
from backend.models.draft_selection_data import DraftSelectionData
from backend.models.player_pool import PlayerPool
from backend.mcp_clients.draft_client import read_team_roster_resource, read_draft_history_resource
from backend.utils.util import NO_OF_TEAMS, NO_OF_ROUNDS
from backend.draft_agents.draft_name_generator.draft_name_generator_agent import get_draft_name_generator
from backend.templates.templates import draft_name_generator_message
# MEMORY STORAGE DISABLED - Using PostgreSQL RDS only
# from backend.data.memory import save_draft_state, load_draft_state
from agents import Runner
import uuid
import math
import os

use_local_db = True

class Draft(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(description="Name of the draft.", default="")
    num_rounds: int = Field(default=NO_OF_ROUNDS,description="Number of rounds")
    player_pool: Optional[PlayerPool] = Field(description="List of players available to draft", default=None)
    teams: DraftTeams = Field(description="List of teams in draft", default=None)
    current_round: int = Field(default=1, description="Current round.")
    current_pick: int = Field(default=1, description="Current pick.")
    is_complete: bool = Field(default=False, description="Is draft complete")

    @classmethod
    def from_dict(cls, data):
        player_pool = data.get("player_pool")
        if isinstance(player_pool, dict):
            player_pool = PlayerPool(**player_pool)
        
        teams = data.get("teams")
        if isinstance(teams, dict):
            teams = DraftTeams(**teams)
        elif teams is None:
            print(f"Warning: teams is None in from_dict for draft {data.get('id')}")
            raise ValueError("Cannot create Draft with None teams")

        return cls(
            id=data["id"],
            name=data["name"],
            num_rounds=data["num_rounds"],
            player_pool=player_pool,
            teams=teams,
            current_round=data.get("current_round", 1),
            current_pick=data.get("current_pick", 1),
            is_complete=data.get("is_complete", False)
        )
    
    @classmethod
    async def get(cls, id: Optional[str]):
        # Generate draft name first (MOVED OUTSIDE the if block)
        draft_name_generator_agent = await get_draft_name_generator()
        message = draft_name_generator_message()
        result = await Runner.run(draft_name_generator_agent, message)
        draft_name = result.final_output
        if(id is None):
            id = str(uuid.uuid4())
            draft_name_generator_agent = await get_draft_name_generator()
            message = draft_name_generator_message()
            result = await Runner.run(draft_name_generator_agent, message)
            draft_name = result.final_output        

        import ast
        
        # Load from PostgreSQL database only (memory storage disabled)
        fields = read_draft(id.lower())
        
        if not fields:
            # Initialize teams first
            teams = await DraftTeams.get(id.lower(), NO_OF_TEAMS)
            player_pool = await PlayerPool.get(id=None)
            
            fields = {
                "id": id,
                "name": draft_name,
                "num_rounds": NO_OF_ROUNDS,
                "player_pool": player_pool.model_dump(by_alias=True, mode="json"),
                "teams": teams.model_dump(by_alias=True, mode="json"),
                "current_round": 1,
                "current_pick": 1,
                "is_complete": False
            }
            
            # Save to PostgreSQL database only
            write_draft(id.lower(), fields)
            await DraftHistory.get(id.lower())
        
        # Ensure teams is properly loaded from fields
        if fields and 'teams' in fields and fields['teams'] is not None:
            if isinstance(fields['teams'], dict):
                fields['teams'] = DraftTeams(**fields['teams'])
            elif isinstance(fields['teams'], str):
                try:
                    teams_dict = ast.literal_eval(fields['teams'])
                    if isinstance(teams_dict, dict):
                        fields['teams'] = DraftTeams(**teams_dict)
                except Exception as e:
                    print(f"Error parsing teams from string: {e}")
                    fields['teams'] = await DraftTeams.get(id.lower(), NO_OF_TEAMS)
            elif isinstance(fields['teams'], DraftTeams):
                pass
            else:
                print(f"Unexpected teams type: {type(fields['teams'])}")
                fields['teams'] = await DraftTeams.get(id.lower(), NO_OF_TEAMS)
        else:
            print(f"Teams not found in fields or is None, initializing...")
            fields['teams'] = await DraftTeams.get(id.lower(), NO_OF_TEAMS)
        
        if not fields.get('teams'):
            raise ValueError(f"Failed to initialize teams for draft {id}")
        
        return cls(**fields)

    def get_draft_order(self, round_num: int) -> List[Team]:
        """Get the draft order for a specific round. Snake draft: odd rounds use normal order, even rounds reverse."""
        base_order = self.teams.teams
        if round_num % 2 == 0:
            return list(reversed(base_order))
        return base_order

    def get_team_for_pick(self, round_num: int, pick_num: int) -> Team:
        """Get the team that should draft at a specific pick number."""
        num_teams = len(self.teams.teams)
        picks_in_round = num_teams
        first_pick_of_round = ((round_num - 1) * picks_in_round) + 1
        pick_index_in_round = pick_num - first_pick_of_round
        
        draft_order = self.get_draft_order(round_num)
        
        if pick_index_in_round < 0 or pick_index_in_round >= len(draft_order):
            raise ValueError(f"Invalid pick index {pick_index_in_round} for round {round_num}")
        
        return draft_order[pick_index_in_round]
    
    def get_undrafted_players(self) -> List[Player]:
        return [player for player in self.player_pool.players if player.is_drafted == False]
    
    def get_team_roster(self, team_name) -> Dict[str, Optional[Player]]:
        draft_team = next((t for t in self.teams.teams if t.name.lower() == team_name.lower()), None)
        if draft_team == None:
            print(f"Team {team_name} not found in {self.teams.teams}.")
            raise ValueError(f"Team {team_name} not found in {self.teams.teams}.")
        return draft_team.roster
        
    def get_draft_player_pool(self) -> PlayerPool: 
        return self.player_pool
    
    def get_player_from_pool(self, name: str) -> Optional[Player]:
        first_player = next((player for player in self.player_pool if player.name == name), None)
        if first_player:
            print(f"Found player in pool: {first_player.name}, Player: {first_player.to_dict()}")
        else:
            print("Player not found in player pool.")
            raise ValueError("Player not found in player pool.")
    
    def save(self):
        """Save draft to PostgreSQL database only (memory storage disabled)"""
        try:
            data = self.model_dump(by_alias=True)
            write_draft(self.id.lower(), data)
            logging.info(f"Draft {self.id} saved to PostgreSQL")
        except Exception as e:
            logging.error(f"Error saving draft {self.id}: {e}", exc_info=True)
            raise

    def report(self) -> str:
        """Return a json string representing the draft."""
        data = self.model_dump(by_alias=True)
        return json.dumps(data, default=str)
    
    def roster_player(self, team: Team, player: Player):
        drafted_position_str = player.position
        draft_team = next((t for t in self.teams.teams if t.name.lower() == team.name), None)
        if draft_team == None:
            print(f"Team {team.name} not found in {self.teams.teams}.")
            raise ValueError(f"Team {team.name} not found in {self.teams.teams}.")
        draft_team.roster[drafted_position_str] = player
        draft_team.drafted_players.append(player)

    async def draft_player(self, team: Team, round: int, pick: int, selected_player: Player, rationale: str) -> DraftSelectionData:
        try:
            draft_team = next((t for t in self.teams.teams if t.name.lower() == team.name), None)
            needed_positions_set = draft_team.get_needed_positions()
            if not needed_positions_set:
                raise Exception(f"Error: Roster is full for team: {team.name}. Needed positions: {needed_positions_set}")

            drafted_position = selected_player.position

            if drafted_position not in needed_positions_set:
                print(f"Error: Position {drafted_position} already filled.")
                raise Exception(f"Error: Position {drafted_position} already filled.")
            
            # Add to team roster
            self.roster_player(team, selected_player)

            # Mark player as drafted in player pool
            players_in_pool = [player for player in self.player_pool.players if player.id == selected_player.id]
            if players_in_pool is None or not players_in_pool: 
                raise Exception(f"Error: Selected player {selected_player.name} does not exist in player pool.")
            
            players_in_pool[0].mark_drafted()
            self.player_pool.save()

            # Update draft history
            history = await DraftHistory.get(self.id.lower())
            history.update_draft_history(round, pick, selected_player, rationale)

            total_picks = NO_OF_TEAMS * NO_OF_ROUNDS
            if self.current_pick == total_picks:
                self.is_complete = True
            else:
                self.current_pick += 1
                math.ceil(self.current_pick/NO_OF_TEAMS)
            
            # Save to PostgreSQL database only (memory storage disabled)
            self.save()
            
            print(f"Team {team.name} drafted {selected_player.id}: {selected_player.name} ({selected_player.position} in round {round}.")
            return DraftSelectionData(reason=rationale, player_id=selected_player.id, player_name=selected_player.name)
    
        except Exception as e:
            logging.error(f"An error occurred in draft_player: {e}", exc_info=True)
            
            # Save draft state to database on error (memory storage disabled)
            try:
                self.save()
                logging.info(f"Draft state saved to database after error")
            except Exception as save_error:
                logging.error(f"Failed to save draft state after error: {save_error}", exc_info=True)
            
            print(f"An error occurred in draft_player: {e}")
            raise

    async def run_draft(self) -> Tuple[Any, DraftHistory]:
        try:
            for round_num in range(1, self.num_rounds + 1):
                draft_order = self.get_draft_order(round_num)
                for team in draft_order:
                    await team.select_player(self, self.current_round, self.current_pick)
                    self.current_pick += 1   
                self.current_round += 1
            
            # Print draft history
            import json
            from backend.models.draft_history import DraftHistory
            history_data = await read_draft_history_resource(self.id.lower())
            if isinstance(history_data, str):
                history_dict = json.loads(history_data)
            else:
                history_dict = history_data
            history = DraftHistory(**history_dict)
            return self, history
            
        except Exception as e:
            logging.error(f"Error in run_draft: {e}", exc_info=True)
            
            # Save draft state to database on error (memory storage disabled)
            try:
                self.save()
                logging.info(f"Draft state saved to database after run_draft error")
            except Exception as save_error:
                logging.error(f"Failed to save draft state after run_draft error: {save_error}", exc_info=True)
            
            raise

    async def run(self, player_pool_id: Optional[str]):
        try:
            # Ensure player_pool is always initialized
            if self.player_pool is None:
                if player_pool_id is not None:
                    self.player_pool = await PlayerPool.get(id=player_pool_id.lower())
                else:
                    self.player_pool = await PlayerPool.get(id=None)
                
                # Save after initializing player pool
                self.save()
            
            draft, history = await self.run_draft()
            
            # Print final rosters 
            print("\n=== Final Rosters ===")
            for team in draft.teams.teams:
                print(f"\n{team.name} Roster:")
                roster = await read_team_roster_resource(draft.id.lower(), team.name.lower())
                print(roster)
            print(f"\n=== Draft History ===")
            print(history)
            return draft, history
            
        except Exception as e:
            traceback.print_exc()
            logging.error("An error occurred in draft.run", exc_info=True)
            
            # Save draft state to database on error (memory storage disabled)
            try:
                self.save()
                logging.info(f"Draft state saved to database after draft.run error")
            except Exception as save_error:
                logging.error(f"Failed to save draft state after draft.run error: {save_error}", exc_info=True)
            
            print(f"Error running MLB Draft Oracle simulation: {e}")
            raise