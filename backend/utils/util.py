from enum import Enum
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from backend.templates.strategies import early_ace_strategy, balanced_strategy, power_hitting_focus_strategy, speed_strategy, hitters_first_strategy, pitching_heavy_strategy

class Position(Enum):
    FIRST_BASE = "1B"
    # SECOND_BASE = "2B"
    # THIRD_BASE = "3B"
    # SHORTSOP = "SS"
    CATCHER = "C"
    PITCHER = "P"
    # RIGHT_FIELD = "RF"
    # LEFT_FIELD = "LF"
    # CENTER_FIELD = "CF"
    OUTFIELD = "OF"


    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler):
        # This allows Pydantic v2 to serialize/deserialize the enum as its value
        return core_schema.json_or_python_schema(
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(cls),
                core_schema.str_schema()
            ]),
            json_schema=core_schema.str_schema(),
        )

mlbstatsapi_position_map = {
            'First Baseman': Position.FIRST_BASE,
            # 'Second Baseman': Position.SECOND_BASE,
            # 'Third Baseman': Position.THIRD_BASE,
            #'Shortstop': Position.SHORTSOP,
            'Catcher': Position.CATCHER,
            'Pitcher': Position.PITCHER,
            # 'Right Fielder': Position.RIGHT_FIELD,
            #'Left Fielder': Position.LEFT_FIELD,
            # 'Center Fielder': Position.CENTER_FIELD,
            'Outfielder': Position.OUTFIELD
        }

mlbstatsapi_reverse_position_map = {
             Position.FIRST_BASE: '1B',
            # Position.SECOND_BASE: '2B',
            # Position.THIRD_BASE: '3B',
            # Position.SHORTSOP: 'SS',
            Position.CATCHER: 'C',
            Position.PITCHER: 'P',
            Position.OUTFIELD: 'OF'
            # Position.RIGHT_FIELD: 'RF',
            # Position.LEFT_FIELD: 'LF',
            # Position.CENTER_FIELD: 'CF'
        }
# all_position_set = { '1B','2B', '3B', 'SS', 'C', 'RF', 'LF', 'CF', 'P'}
all_position_set = { '1B', 'C', 'RF', 'LF', 'CF', 'P', 'OF'}

# hitter_position_set = { '1B','2B', '3B', 'SS', 'C', 'RF', 'LF', 'CF'}
hitter_position_set = { '1B', 'C', 'RF', 'LF', 'CF'}
                        
outfield_postion_set = { 'RF', 'LF', 'CF' }

pitcher_position_set = {'P'}

draft_strategy_set = {early_ace_strategy,
                      balanced_strategy, 
                      power_hitting_focus_strategy, 
                      speed_strategy, 
                      hitters_first_strategy, 
                      pitching_heavy_strategy
                      }

NO_OF_TEAMS = 2
NO_OF_ROUNDS = 4