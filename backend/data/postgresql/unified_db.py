"""
Unified database access layer - PostgreSQL RDS ONLY
Location: backend/data/postgresql/unified_db.py

This module provides database operations exclusively through PostgreSQL RDS.
SQLite code has been commented out but preserved for potential rollback.
"""
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def use_rds() -> bool:
    """
    Always return True - we only use PostgreSQL RDS now.
    """
    return True


# ============================================================================
# DRAFT OPERATIONS
# ============================================================================

def write_draft(id: str, data: dict) -> None:
    """Write draft data to PostgreSQL RDS."""
    _write_draft_postgres(id, data)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import write_draft as sqlite_write_draft
    # sqlite_write_draft(id, data)


def read_draft(id: str) -> Optional[dict]:
    """Read draft data from PostgreSQL RDS."""
    return _read_draft_postgres(id)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import read_draft as sqlite_read_draft
    # return sqlite_read_draft(id)


def read_drafts() -> List[Optional[dict]]:
    """Read all drafts from PostgreSQL RDS."""
    return _read_drafts_postgres()
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import read_drafts as sqlite_read_drafts
    # return sqlite_read_drafts()


# ============================================================================
# TEAM OPERATIONS
# ============================================================================

def write_team(name: str, team_dict: dict) -> None:
    """Write team data to PostgreSQL RDS."""
    _write_team_postgres(name, team_dict)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import write_team as sqlite_write_team
    # sqlite_write_team(name, team_dict)


def read_team(name: str) -> Optional[dict]:
    """Read team data from PostgreSQL RDS."""
    return _read_team_postgres(name)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import read_team as sqlite_read_team
    # return sqlite_read_team(name)


# ============================================================================
# PLAYER POOL OPERATIONS
# ============================================================================

def write_player_pool(id: str, player_pool_dict: dict) -> None:
    """Write player pool data to PostgreSQL RDS."""
    _write_player_pool_postgres(id, player_pool_dict)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import write_player_pool as sqlite_write_player_pool
    # sqlite_write_player_pool(id, player_pool_dict)


def read_player_pool(id: str) -> Optional[dict]:
    """Read player pool data from PostgreSQL RDS."""
    return _read_player_pool_postgres(id)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import read_player_pool as sqlite_read_player_pool
    # return sqlite_read_player_pool(id)


def get_latest_player_pool() -> Optional[dict]:
    """Get the most recently created player pool from PostgreSQL RDS."""
    return _get_latest_player_pool_postgres()
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import get_latest_player_pool as sqlite_get_latest_player_pool
    # return sqlite_get_latest_player_pool()


def player_pool_exists() -> bool:
    """Check if any player pool exists in PostgreSQL RDS."""
    return _player_pool_exists_postgres()
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import player_pool_exists as sqlite_player_pool_exists
    # return sqlite_player_pool_exists()


# ============================================================================
# PLAYER OPERATIONS
# ============================================================================

def write_player(id: int, player_dict: dict) -> None:
    """Write player data to PostgreSQL RDS."""
    _write_player_postgres(id, player_dict)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import write_player as sqlite_write_player
    # sqlite_write_player(id, player_dict)


def read_player(id: int) -> Optional[dict]:
    """Read player data from PostgreSQL RDS."""
    return _read_player_postgres(id)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import read_player as sqlite_read_player
    # return sqlite_read_player(id)


# ============================================================================
# DRAFT TEAMS OPERATIONS
# ============================================================================

def write_draft_teams(id: str, draft_teams_dict) -> None:
    """Write draft teams data to PostgreSQL RDS."""
    _write_draft_teams_postgres(id, draft_teams_dict)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import write_draft_teams as sqlite_write_draft_teams
    # sqlite_write_draft_teams(id, draft_teams_dict)


def read_draft_teams(id: str) -> Optional[dict]:
    """Read draft teams data from PostgreSQL RDS."""
    return _read_draft_teams_postgres(id)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import read_draft_teams as sqlite_read_draft_teams
    # return sqlite_read_draft_teams(id)


# ============================================================================
# DRAFT HISTORY OPERATIONS
# ============================================================================

def write_draft_history(id: str, data: dict) -> None:
    """Write draft history data to PostgreSQL RDS."""
    _write_draft_history_postgres(id, data)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import write_draft_history as sqlite_write_draft_history
    # sqlite_write_draft_history(id, data)


def read_draft_history(id: str) -> Optional[dict]:
    """Read draft history data from PostgreSQL RDS."""
    return _read_draft_history_postgres(id)
    # SQLite implementation commented out:
    # from backend.data.sqlite.database import read_draft_history as sqlite_read_draft_history
    # return sqlite_read_draft_history(id)


# ============================================================================
# POSTGRESQL IMPLEMENTATION (Active)
# ============================================================================

def _write_draft_postgres(id: str, data: dict) -> None:
    """Write draft to PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import Draft
    from sqlalchemy.dialects.postgresql import insert
    
    with DatabaseSession() as session:
        json_data = json.dumps(data, default=str)
        insert_stmt = insert(Draft).values(id=id.lower(), data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['id'], 
            set_=dict(data=json_data)
        )
        session.execute(do_update_stmt)
        logger.info(f"Wrote draft {id} to PostgreSQL")


def _read_draft_postgres(id: str) -> Optional[dict]:
    """Read draft from PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import Draft
    
    with DatabaseSession() as session:
        result = session.query(Draft).filter_by(id=id.lower()).first()
        if result:
            return json.loads(result.data)
        return None


def _read_drafts_postgres() -> List[Optional[dict]]:
    """Read all drafts from PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import Draft
    
    with DatabaseSession() as session:
        results = session.query(Draft).all()
        return [json.loads(r.data) for r in results if r.data]


def _write_team_postgres(name: str, team_dict: dict) -> None:
    """Write team to PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import Team
    from sqlalchemy.dialects.postgresql import insert
    
    with DatabaseSession() as session:
        json_data = json.dumps(team_dict, default=str)
        insert_stmt = insert(Team).values(name=name.lower(), data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['name'], 
            set_=dict(data=json_data)
        )
        session.execute(do_update_stmt)
        logger.info(f"Wrote team {name} to PostgreSQL")


def _read_team_postgres(name: str) -> Optional[dict]:
    """Read team from PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import Team
    
    with DatabaseSession() as session:
        result = session.query(Team).filter_by(name=name.lower()).first()
        if result:
            return json.loads(result.data)
        return None


def _write_player_pool_postgres(id: str, player_pool_dict) -> None:
    """Write player pool to PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import PlayerPool
    from sqlalchemy.dialects.postgresql import insert
    
    # Handle Pydantic models
    if hasattr(player_pool_dict, 'model_dump'):
        player_pool_dict = player_pool_dict.model_dump(by_alias=True)
    
    with DatabaseSession() as session:
        json_data = json.dumps(player_pool_dict, default=str)
        insert_stmt = insert(PlayerPool).values(id=id.lower(), data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['id'], 
            set_=dict(data=json_data)
        )
        session.execute(do_update_stmt)
        logger.info(f"Wrote player pool {id} to PostgreSQL")


def _read_player_pool_postgres(id: str) -> Optional[dict]:
    """Read player pool from PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import PlayerPool
    
    with DatabaseSession() as session:
        result = session.query(PlayerPool).filter_by(id=id.lower()).first()
        if result:
            return json.loads(result.data)
        return None


def _get_latest_player_pool_postgres() -> Optional[dict]:
    """Get most recent player pool from PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import PlayerPool
    
    with DatabaseSession() as session:
        result = session.query(PlayerPool).order_by(PlayerPool.id.desc()).first()
        if result:
            pool_data = json.loads(result.data)
            return pool_data
        return None


def _player_pool_exists_postgres() -> bool:
    """Check if any player pool exists in PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import PlayerPool
    from sqlalchemy import func
    
    with DatabaseSession() as session:
        count = session.query(func.count(PlayerPool.id)).scalar()
        return count > 0


def _write_player_postgres(id: int, player_dict: dict) -> None:
    """Write player to PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import Player
    from sqlalchemy.dialects.postgresql import insert
    
    with DatabaseSession() as session:
        json_data = json.dumps(player_dict, default=str)
        insert_stmt = insert(Player).values(id=str(id), data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['id'], 
            set_=dict(data=json_data)
        )
        session.execute(do_update_stmt)
        logger.debug(f"Wrote player {id} to PostgreSQL")


def _read_player_postgres(id: int) -> Optional[dict]:
    """Read player from PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import Player
    
    with DatabaseSession() as session:
        result = session.query(Player).filter_by(id=str(id)).first()
        if result:
            return json.loads(result.data)
        return None


def _write_draft_teams_postgres(id: str, draft_teams_dict) -> None:
    """Write draft teams to PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import DraftTeam
    from sqlalchemy.dialects.postgresql import insert
    
    # Handle list of Pydantic models
    if isinstance(draft_teams_dict, list) and draft_teams_dict and hasattr(draft_teams_dict[0], 'model_dump'):
        draft_teams_dict = [team.model_dump(by_alias=True) for team in draft_teams_dict]
    # Handle single Pydantic model
    elif hasattr(draft_teams_dict, 'model_dump'):
        draft_teams_dict = draft_teams_dict.model_dump(by_alias=True)
    
    with DatabaseSession() as session:
        json_data = json.dumps(draft_teams_dict, default=str)
        insert_stmt = insert(DraftTeam).values(id=id.lower(), data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['id'], 
            set_=dict(data=json_data)
        )
        session.execute(do_update_stmt)
        logger.info(f"Wrote draft teams {id} to PostgreSQL")


def _read_draft_teams_postgres(id: str) -> Optional[dict]:
    """Read draft teams from PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import DraftTeam
    
    with DatabaseSession() as session:
        result = session.query(DraftTeam).filter_by(id=id.lower()).first()
        if result:
            return json.loads(result.data)
        return None


def _write_draft_history_postgres(id: str, data: dict) -> None:
    """Write draft history to PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import DraftHistory
    from sqlalchemy.dialects.postgresql import insert
    
    with DatabaseSession() as session:
        json_data = json.dumps(data, default=str)
        insert_stmt = insert(DraftHistory).values(id=id.lower(), data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['id'], 
            set_=dict(data=json_data)
        )
        session.execute(do_update_stmt)
        logger.info(f"Wrote draft history {id} to PostgreSQL")


def _read_draft_history_postgres(id: str) -> Optional[dict]:
    """Read draft history from PostgreSQL"""
    from backend.data.postgresql.connection import DatabaseSession
    from backend.data.postgresql.models import DraftHistory
    
    with DatabaseSession() as session:
        result = session.query(DraftHistory).filter_by(id=id.lower()).first()
        if result:
            return json.loads(result.data)
        return None