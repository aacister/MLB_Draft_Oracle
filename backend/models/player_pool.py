from pydantic import BaseModel, Field
from typing import List, Any, Optional, Dict
import statsapi
from backend.models.players import Player
from backend.models.player_stats import PlayerStatistics
from backend.utils.util import outfield_postion_set, pitcher_position_set, hitter_position_set, all_position_set
from backend.data.sqlite.database import read_player_pool, write_player_pool
#from backend.data.postgresql.main import read_postgres_player_pool, write_postgres_player_pool
from uuid import uuid4
import uuid
import os

#if os.getenv("DEPLOYMENT_ENVIRONMENT") == 'DEV':
#    use_local_db = True
#else: 
#    use_local_db = False
use_local_db = True

class PlayerPool(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    players: List[Player] = Field(default=[], description="Pool of players available to draft")

    @classmethod
    async def get(cls, id: Optional[str]):
        if id is None:
            id=str(uuid.uuid4()).lower()
    #    if use_local_db:
        fields = read_player_pool(id.lower())
    #    else:
    #        fields = read_postgres_player_pool(id.lower())
        if not fields:
            player_pool = await initialize_player_pool(id=id.lower())
            fields = player_pool.model_dump(by_alias=True)
    #    if use_local_db:
        write_player_pool(id.lower(), fields)
    #    else:
    #        write_postgres_player_pool(id.lower(), fields)
        return cls(**fields)
    
    def get_undrafted_players_dict(self) -> List[dict[str, Any]]:
        
        available_players = []
        for player in self.players:
            player_dict = player.to_dict()
            available_players.append(player_dict)
        return available_players

    def to_list(self):
        return [player.to_dict() for player in self.players]

    def to_dict(self):
        return {"players": [player.to_dict() for player in self.players]}

    def save(self):
        data = self.model_dump(by_alias=True)
        if use_local_db:
            write_player_pool(self.id, data)
        else:
            write_postgres_player_pool(self.id, data)

async def initialize_player_pool(id: str) -> PlayerPool:

        #create player list
        season = 2025
        names_set = await get_players_from_statsapi(names_set=set(), season=season)
        player_pool = []
        player_position_count_map = {
             '1B': 0,
            # '2B': 0,
            # '3B': 0,
            # 'SS': 0,
             'C': 0,
             'P': 0,
             'OF': 0
            # 'RF': 0,
            #'LF': 0,
            # 'CF': 0
        }
        await add_to_player_pool(names_set=names_set, player_pool=player_pool, player_position_count_map=player_position_count_map, season=season)
        #less_than_or_equal_zero = any(value <= 0 for value in player_position_count_map.values())
        print (f"Player position count map: {player_position_count_map}")
        '''
        if has_zero_or_less:
        '''
        # Pull another season players to expand pool
       # season = 2024
       # names_set = await get_players_from_statsapi(names_set=set(), season=season)
       # await add_to_player_pool(names_set=names_set, player_pool=player_pool, player_position_count_map=player_position_count_map, season=season)
        
        print (f"Player position count map: {player_position_count_map}")
        print(f"Player pool length: {len(player_pool)}")
        return PlayerPool(id=id, players=player_pool)

async def add_to_player_pool(names_set: set, player_pool: list, player_position_count_map: dict, season: int):
    
    for name in names_set:
            try:
                players = statsapi.lookup_player(name)
                player = players[0]
                fantasy_position = player.get('primaryPosition', {}).get('abbreviation', 'N/A')
                if not fantasy_position in all_position_set:
                    print(f"{player['fullName']} not added. Fantasy position {fantasy_position} not valid.")
                    continue
                stat_group = None
                if fantasy_position in pitcher_position_set:
                    stat_group='pitching'
                elif fantasy_position in hitter_position_set:
                    stat_group='hitting'
                else:
                    stat_group=None
                if stat_group == None:
                    print(f"{player['fullName']} not added.  Stat_group = None")
                    continue
                
                pos = fantasy_position
                if fantasy_position in outfield_postion_set:
                    pos = 'OF'
                if player_position_count_map[pos] >= 20:
                    #print(f"{player['fullName']} not added. Position {pos} >= 20")
                    continue
                
                stats = statsapi.player_stat_data(player['id'], group=stat_group, type='season', sportId=1, season=season)
                player_stats = stats.get('stats', [{}])[0].get('stats', {})
                if stat_group == 'hitting':
                        at_bats = player_stats.get('atBats', 0)
                        r = player_stats.get('runs', 0)
                        hr = player_stats.get('homeRuns', 0)
                        rbi = player_stats.get('rbi', 0)
                        sb = player_stats.get('sb', 0)
                        obp = player_stats.get('obp', '.000')
                        slg = player_stats.get('slg', '.000')
                        avg = player_stats.get('avg', '.000')
                        innings_pitched = ''
                        wins=0
                        strikeouts=0
                        era='-,--'
                        whip='-.--'
                        saves=0

                elif stat_group == "pitching":
                        innings_pitched = player_stats.get('inningsPitched', None)
                        if innings_pitched is not None:
                            innings_pitched = innings_pitched
                        else:
                            innings_pitched = ''
                        wins = player_stats.get('wins', 0)
                        strikeouts = player_stats.get('strikeOuts', 0)
                        era = player_stats.get('era', '-.--')
                        whip = player_stats.get('whip', '-.--')
                        saves = player_stats.get('saves', 0)
                        at_bats =  0
                        r =  0
                        hr =  0
                        rbi = 0
                        sb = 0
                        obp = '.000'
                        slg = '.000'
                        avg = '.000'

                else:
                    print(f"{player['fullName']} not added.  Invalid player position")
                    continue

                player_statistics = PlayerStatistics(
                        at_bats = at_bats,
                        r=r,
                        hr=hr,
                        rbi=rbi,
                        sb=sb,
                        avg=avg,
                        obp = obp,
                        slg = slg,
                        w=wins,
                        k=strikeouts,
                        era=era,
                        whip=whip,
                        s=saves,
                        innings_pitched = innings_pitched

                    )
                current_team = player.get('currentTeam', {})
                team_id = current_team.get('id', 0)
                team_info = statsapi.lookup_team(team_id)
                if team_info:
                    team_data = team_info[0]
                    team_abbr = team_data['name']
                else:
                    team_abbr = 'N/A'

                player_id=player['id']

                player_id_exists = any(player.id == player_id for player in player_pool)
                if player_id_exists:
                    print(f"{player['fullName']} not added.  Player_id exists")
                    continue

                name=player['fullName']
                
                player = Player(
                    id=player_id,
                    name=name,
                    position=pos,
                    team=team_abbr,
                    stats=player_statistics
                )
                player.save()
                player_pool.append(player)
                player_position_count_map[fantasy_position] += 1
                 
                #print(f"Player {player.name} added for position {player.position} ")
            except Exception as e:
                print(f"Error processing player: {e}")

async def get_players_from_statsapi(names_set: set, season: int) -> set:
    try:
        hr_leaders = statsapi.league_leader_data('homeRuns', season=season, limit=50, statGroup=None, leagueId=None, gameTypes=None, playerPool=None, sportId=1, statType=None)
        ba_leaders = statsapi.league_leader_data('battingAverage', season=season, limit=50, statGroup=None, leagueId=None, gameTypes=None, playerPool=None, sportId=1, statType=None)
        sb_leaders = statsapi.league_leader_data('stolenBases', season=season, limit=50, statGroup=None, leagueId=None, gameTypes=None, playerPool=None, sportId=1, statType=None)
        slugging_leaders = statsapi.league_leader_data('sluggingPercentage', season=season, limit=50, statGroup=None, leagueId=None, gameTypes=None, playerPool=None, sportId=1, statType=None)
        strikeout_leaders = statsapi.league_leader_data('strikeouts', season=season, limit=50, statGroup=None, leagueId=None, gameTypes=None, playerPool=None, sportId=1, statType=None)
        wins_leaders = statsapi.league_leader_data('wins', season=season, limit=50, statGroup=None, leagueId=None, gameTypes=None, playerPool=None, sportId=1, statType=None)
        saves_leaders = statsapi.league_leader_data('saves', season=season, limit=50, statGroup=None, leagueId=None, gameTypes=None, playerPool=None, sportId=1, statType=None)
        strikeoutWalkRatio_leaders = statsapi.league_leader_data('strikeoutWalkRatio', season=season, limit=50, statGroup=None, leagueId=None, gameTypes=None, playerPool=None, sportId=1, statType=None)
        runs_leaders = statsapi.league_leader_data('runs', season=season, limit=50, statGroup=None, leagueId=None, gameTypes=None, playerPool=None, sportId=1, statType=None)
        hits_leaders = statsapi.league_leader_data('hits', season=season, limit=50, statGroup=None, leagueId=None, gameTypes=None, playerPool=None, sportId=1, statType=None)
        
        for hr_leader in hr_leaders:
            #print(f"hr_leader: {hr_leader}")
            names_set.add(hr_leader[1])
        for ba_leader in ba_leaders:
            #print(f"ba_leader: {ba_leader}")
            names_set.add(ba_leader[1])
        for sb_leader in sb_leaders:
            #print(f"sb_leader: {sb_leader}")
            names_set.add(sb_leader[1])
        for slugging_leader in slugging_leaders:
            #print(f"slugging_leader: {slugging_leader}")
            names_set.add(slugging_leader[1])
        for k_leader in strikeout_leaders:
            #print(f"k_leader: {k_leader}")
            names_set.add(k_leader[1])
        
        for runs_leader in runs_leaders:
            #print(f"runs_leader: {runs_leader}")
            names_set.add(runs_leader[1])
        for hits_leader in hits_leaders:
            #print(f"hits_leader: {hits_leader}")
            names_set.add(hits_leader[1])
        
        for win_leader in wins_leaders:
            #print(f"win_leader: {win_leader}")
            names_set.add(win_leader[1])
        for saves_leader in saves_leaders:
            #print(f"saves_leader: {saves_leader}")
            names_set.add(saves_leader[1])
        for k_walk_ration_leader in strikeoutWalkRatio_leaders:
            #print(f"k_walk_ration_leader: {k_walk_ration_leader}")
            names_set.add(k_walk_ration_leader[1])
        
        return names_set
    except Exception as e:
        print(f"Error fetching players: {e}")
        return []
    