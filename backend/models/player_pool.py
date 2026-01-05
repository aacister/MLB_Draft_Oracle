from pydantic import BaseModel, Field
from typing import List, Any, Optional, Dict
import statsapi
from backend.models.players import Player
from backend.models.player_stats import PlayerStatistics
from backend.utils.util import outfield_postion_set, pitcher_position_set, hitter_position_set, all_position_set
from backend.data.postgresql.unified_db import read_player_pool, write_player_pool, get_latest_player_pool, player_pool_exists
from uuid import uuid4
import uuid
import os
import socket
import time
from functools import wraps
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Set global socket timeout for all network operations
socket.setdefaulttimeout(30)  # 30 second timeout

# Retry decorator for API calls
def with_retry(max_retries=3, backoff=2):
    """
    Retry decorator with exponential backoff for handling API failures.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff: Base delay in seconds (exponential: backoff^attempt)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
                        raise
                    wait_time = backoff ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        return wrapper
    return decorator


@with_retry(max_retries=3, backoff=2)
def fetch_league_leaders(stat_type, season, limit=50):
    """
    Fetch league leaders with retry logic and timeout handling.
    
    Args:
        stat_type: Type of statistic to fetch (e.g., 'homeRuns', 'battingAverage')
        season: Season year (e.g., 2024)
        limit: Maximum number of leaders to fetch
    
    Returns:
        List of league leaders from MLB Stats API
    """
    logger.info(f"Fetching {stat_type} leaders for {season} season...")
    return statsapi.league_leader_data(
        stat_type,
        season=season,
        limit=limit,
        statGroup=None,
        leagueId=None,
        gameTypes=None,
        playerPool=None,
        sportId=1,
        statType=None
    )


class PlayerPool(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    players: List[Player] = Field(default=[], description="Pool of players available to draft")

    @classmethod
    async def get(cls, id: Optional[str]):
        # First, try to get any existing player pool from database
        if id is None:
            # Check if any player pool exists in the database
            existing_pool = get_latest_player_pool()
            
            if existing_pool:
                logger.info(f"Found existing player pool: {existing_pool['id']}")
                return cls(**existing_pool)
            
            # No existing pool found, create new one
            logger.info("No existing player pool found, creating new one...")
            id = str(uuid.uuid4()).lower()
        
        fields = read_player_pool(id.lower())
        
        if not fields:
            player_pool = await initialize_player_pool(id=id.lower())
            fields = player_pool.model_dump(by_alias=True)
            write_player_pool(id.lower(), fields)
        
        return cls(**fields)

    
    def get_undrafted_players_dict(self) -> List[dict[str, Any]]:
        """Get list of undrafted players as dictionaries"""
        available_players = []
        for player in self.players:
            if not player.is_drafted:
                player_dict = player.to_dict()
                available_players.append(player_dict)
        return available_players

    def to_list(self):
        """Convert player pool to list of player dictionaries"""
        return [player.to_dict() for player in self.players]

    def to_dict(self):
        """Convert player pool to dictionary"""
        return {"players": [player.to_dict() for player in self.players]}

    def save(self):
        """Save player pool to database"""
        data = self.model_dump(by_alias=True)
        write_player_pool(self.id, data)


async def initialize_player_pool(id: str) -> PlayerPool:
    """
    Initialize player pool by fetching data from MLB Stats API.
    
    Args:
        id: Unique identifier for the player pool
    
    Returns:
        PlayerPool instance with fetched players
    """
    logger.info("Initializing player pool...")
    
    # Use 2024 season (most recent completed season with full data)
    season = 2024
    
    try:
        names_set = await get_players_from_statsapi(names_set=set(), season=season)
        
        if not names_set:
            logger.warning("No player names fetched from MLB Stats API")
            logger.warning("Returning empty player pool")
            return PlayerPool(id=id, players=[])
        
        logger.info(f"Fetched {len(names_set)} unique player names")
        
    except Exception as e:
        logger.error(f"Error fetching player names from MLB Stats API: {e}")
        logger.warning("Returning empty player pool")
        return PlayerPool(id=id, players=[])
    
    # Initialize player pool and position count map
    player_pool = []
    player_position_count_map = {
        '1B': 0,
        'C': 0,
        'P': 0,
        'OF': 0
    }
    
    # Add players to pool
    await add_to_player_pool(
        names_set=names_set, 
        player_pool=player_pool, 
        player_position_count_map=player_position_count_map, 
        season=season
    )
    
    logger.info(f"Player position count map: {player_position_count_map}")
    logger.info(f"Player pool length: {len(player_pool)}")
    
    return PlayerPool(id=id, players=player_pool)


async def add_to_player_pool(names_set: set, player_pool: list, player_position_count_map: dict, season: int):
    """
    Add players to the pool by fetching their stats from MLB Stats API.
    
    Args:
        names_set: Set of player names to fetch
        player_pool: List to append Player objects to
        player_position_count_map: Dictionary tracking player counts by position
        season: Season year for stats
    """
    logger.info(f"Processing {len(names_set)} players...")
    processed = 0
    
    for name in names_set:
        try:
            # Lookup player
            players = statsapi.lookup_player(name)
            if not players:
                logger.debug(f"No player found for name: {name}")
                continue
            
            player = players[0]
            fantasy_position = player.get('primaryPosition', {}).get('abbreviation', 'N/A')
            
            # Validate position
            if fantasy_position not in all_position_set:
                logger.debug(f"{player['fullName']} not added. Fantasy position {fantasy_position} not valid.")
                continue
            
            # Determine stat group
            stat_group = None
            if fantasy_position in pitcher_position_set:
                stat_group = 'pitching'
            elif fantasy_position in hitter_position_set:
                stat_group = 'hitting'
            else:
                logger.debug(f"{player['fullName']} not added. Could not determine stat group.")
                continue
            
            # Map position (consolidate outfield positions)
            pos = fantasy_position
            if fantasy_position in outfield_postion_set:
                pos = 'OF'
            
            # Check position quota
            if player_position_count_map.get(pos, 0) >= 20:
                logger.debug(f"{player['fullName']} not added. Position {pos} quota reached (>= 20)")
                continue
            
            # Fetch player stats
            try:
                stats = statsapi.player_stat_data(
                    player['id'], 
                    group=stat_group, 
                    type='season', 
                    sportId=1, 
                    season=season
                )
                player_stats = stats.get('stats', [{}])[0].get('stats', {})
            except Exception as e:
                logger.warning(f"Could not fetch stats for {player['fullName']}: {e}")
                continue
            
            # Parse stats based on stat group
            if stat_group == 'hitting':
                at_bats = player_stats.get('atBats', 0)
                r = player_stats.get('runs', 0)
                hr = player_stats.get('homeRuns', 0)
                rbi = player_stats.get('rbi', 0)
                sb = player_stats.get('stolenBases', 0)
                obp = player_stats.get('obp', '.000')
                slg = player_stats.get('slg', '.000')
                avg = player_stats.get('avg', '.000')
                innings_pitched = ''
                wins = 0
                strikeouts = 0
                era = '-.--'
                whip = '-.--'
                saves = 0
                
            elif stat_group == "pitching":
                innings_pitched = player_stats.get('inningsPitched', '')
                wins = player_stats.get('wins', 0)
                strikeouts = player_stats.get('strikeOuts', 0)
                era = player_stats.get('era', '-.--')
                whip = player_stats.get('whip', '-.--')
                saves = player_stats.get('saves', 0)
                at_bats = 0
                r = 0
                hr = 0
                rbi = 0
                sb = 0
                obp = '.000'
                slg = '.000'
                avg = '.000'
            else:
                logger.debug(f"{player['fullName']} not added. Invalid stat group")
                continue
            
            # Create player statistics object
            player_statistics = PlayerStatistics(
                at_bats=at_bats,
                r=r,
                hr=hr,
                rbi=rbi,
                sb=sb,
                avg=avg,
                obp=obp,
                slg=slg,
                w=wins,
                k=strikeouts,
                era=era,
                whip=whip,
                s=saves,
                innings_pitched=innings_pitched
            )
            
            # Get team info
            current_team = player.get('currentTeam', {})
            team_id = current_team.get('id', 0)
            try:
                team_info = statsapi.lookup_team(team_id)
                if team_info:
                    team_data = team_info[0]
                    team_abbr = team_data['name']
                else:
                    team_abbr = 'N/A'
            except Exception as e:
                logger.warning(f"Could not fetch team for {player['fullName']}: {e}")
                team_abbr = 'N/A'
            
            player_id = player['id']
            
            # Check for duplicate player IDs
            player_id_exists = any(p.id == player_id for p in player_pool)
            if player_id_exists:
                logger.debug(f"{player['fullName']} not added. Player ID {player_id} already exists")
                continue
            
            name = player['fullName']
            
            # Create and save player
            new_player = Player(
                id=player_id,
                name=name,
                position=pos,
                team=team_abbr,
                stats=player_statistics
            )
            new_player.save()
            player_pool.append(new_player)
            player_position_count_map[pos] = player_position_count_map.get(pos, 0) + 1
            
            processed += 1
            if processed % 10 == 0:
                logger.info(f"Processed {processed}/{len(names_set)} players...")
            
        except Exception as e:
            logger.error(f"Error processing player {name}: {e}")
            continue
    
    logger.info(f"Successfully processed {processed} players")


async def get_players_from_statsapi(names_set: set, season: int) -> set:
    """
    Fetch player names from MLB Stats API leader boards.
    
    Args:
        names_set: Set to add player names to
        season: Season year to fetch leaders from
    
    Returns:
        Set of unique player names
    """
    try:
        logger.info(f"Fetching MLB Stats API leader boards for {season} season...")
        
        # Fetch various stat leaders
        hr_leaders = fetch_league_leaders('homeRuns', season=season, limit=50)
        logger.info(f"✓ Fetched {len(hr_leaders)} home run leaders")
        
        ba_leaders = fetch_league_leaders('battingAverage', season=season, limit=50)
        logger.info(f"✓ Fetched {len(ba_leaders)} batting average leaders")
        
        sb_leaders = fetch_league_leaders('stolenBases', season=season, limit=50)
        logger.info(f"✓ Fetched {len(sb_leaders)} stolen base leaders")
        
        slugging_leaders = fetch_league_leaders('sluggingPercentage', season=season, limit=50)
        logger.info(f"✓ Fetched {len(slugging_leaders)} slugging percentage leaders")
        
        strikeout_leaders = fetch_league_leaders('strikeouts', season=season, limit=50)
        logger.info(f"✓ Fetched {len(strikeout_leaders)} strikeout leaders")
        
        wins_leaders = fetch_league_leaders('wins', season=season, limit=50)
        logger.info(f"✓ Fetched {len(wins_leaders)} wins leaders")
        
        saves_leaders = fetch_league_leaders('saves', season=season, limit=50)
        logger.info(f"✓ Fetched {len(saves_leaders)} saves leaders")
        
        strikeoutWalkRatio_leaders = fetch_league_leaders('strikeoutWalkRatio', season=season, limit=50)
        logger.info(f"✓ Fetched {len(strikeoutWalkRatio_leaders)} K/BB ratio leaders")
        
        runs_leaders = fetch_league_leaders('runs', season=season, limit=50)
        logger.info(f"✓ Fetched {len(runs_leaders)} runs leaders")
        
        hits_leaders = fetch_league_leaders('hits', season=season, limit=50)
        logger.info(f"✓ Fetched {len(hits_leaders)} hits leaders")
        
        # Add all names to set
        for hr_leader in hr_leaders:
            names_set.add(hr_leader[1])
        for ba_leader in ba_leaders:
            names_set.add(ba_leader[1])
        for sb_leader in sb_leaders:
            names_set.add(sb_leader[1])
        for slugging_leader in slugging_leaders:
            names_set.add(slugging_leader[1])
        for k_leader in strikeout_leaders:
            names_set.add(k_leader[1])
        for runs_leader in runs_leaders:
            names_set.add(runs_leader[1])
        for hits_leader in hits_leaders:
            names_set.add(hits_leader[1])
        for win_leader in wins_leaders:
            names_set.add(win_leader[1])
        for saves_leader in saves_leaders:
            names_set.add(saves_leader[1])
        for k_walk_ratio_leader in strikeoutWalkRatio_leaders:
            names_set.add(k_walk_ratio_leader[1])
        
        logger.info(f"✓ Collected {len(names_set)} unique player names from leader boards")
        return names_set
        
    except Exception as e:
        logger.error(f"Error fetching players from MLB Stats API: {e}")
        import traceback
        traceback.print_exc()
        return set()