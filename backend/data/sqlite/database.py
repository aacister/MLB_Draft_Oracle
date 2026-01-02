import sqlite3
import json
from datetime import datetime
from backend.config.settings import settings
from backend.data.sqlite.s3_sync import upload_db_to_s3
import logging
import os

logger = logging.getLogger(__name__)

# Use centralized settings
DB = settings.SQLITE_DB_PATH

# Track if tables have been initialized
_tables_initialized = False

def _ensure_tables_initialized():
    
    """
    Ensure database tables are created.
    This is called lazily on first database access to avoid issues
    when the database file doesn't exist yet (e.g., in Lambda before download).
    """
    global _tables_initialized
    logger.info(f"SQLite version: {sqlite3.sqlite_version}")
    if _tables_initialized:
        return
    
    try:
        # Ensure the directory exists
        db_dir = os.path.dirname(DB)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # Create tables
        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS teams (name TEXT PRIMARY KEY, data TEXT)')        
            cursor.execute('CREATE TABLE IF NOT EXISTS draft (id TEXT PRIMARY KEY, data TEXT)')
            cursor.execute('CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, data TEXT)')
            cursor.execute('CREATE TABLE IF NOT EXISTS player_pool (id TEXT PRIMARY KEY, data TEXT)')        
            cursor.execute('CREATE TABLE IF NOT EXISTS draft_teams (id TEXT PRIMARY KEY, data TEXT)')
            cursor.execute('CREATE TABLE IF NOT EXISTS draft_history (id TEXT PRIMARY KEY, data TEXT)')
            conn.commit()
        
        _tables_initialized = True
        logger.info(f"Database tables initialized at {DB}")
        
    except Exception as e:
        logger.error(f"Error initializing database tables: {e}")
        # Don't set _tables_initialized to True so it will retry next time
        raise


def _upload_after_write():
    """Helper function to upload database to S3 after write operations"""
    if settings.is_lambda:
        try:
            upload_db_to_s3()
        except Exception as e:
            logger.error(f"Failed to upload database to S3 after write: {e}")
            # Don't raise - we want the write operation to succeed even if upload fails
            # The data is still in /tmp and can be uploaded on next successful operation


def write_team(name, team_dict):
    
    _ensure_tables_initialized()
    json_data = json.dumps(team_dict)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO teams (name, data)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET data=excluded.data
        ''', (name.lower(), json_data))
        conn.commit()
    _upload_after_write()


def read_team(name):
    _ensure_tables_initialized()
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM teams WHERE name = ?', (name.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None


def write_player_pool(id, player_pool_dict):
    _ensure_tables_initialized()
    # If passed a PlayerPool object, convert to dict
    if hasattr(player_pool_dict, 'model_dump'):
        player_pool_dict = player_pool_dict.model_dump(by_alias=True)
    json_data = json.dumps(player_pool_dict, default=str)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO player_pool (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data=excluded.data
        ''', (id.lower(), json_data))
        conn.commit()
    _upload_after_write()


def read_player_pool(id):
    _ensure_tables_initialized()
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM player_pool WHERE id = ?', (id.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None


def write_player(id, player_dict):
    _ensure_tables_initialized()
    json_data = json.dumps(player_dict)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO players (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data=excluded.data
        ''', (id, json_data))
        conn.commit()
    _upload_after_write()


def read_player(id):
    _ensure_tables_initialized()
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM players WHERE id = ?', (id,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    

def write_draft(id: str, data: dict) -> None:
    _ensure_tables_initialized()
    logger.info(f"Writing draft for id: {id}")
    data_json = json.dumps(data, default=str)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO draft (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data=excluded.data
        ''', (id.lower(), data_json))
        conn.commit()
    logger.info(f"Successfully wrote draft for id: {id}")
    _upload_after_write()


def read_draft(id: str) -> dict | None:
    _ensure_tables_initialized()
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM draft WHERE id = ?', (id.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None


def read_drafts() -> list[dict | None]:
    _ensure_tables_initialized()
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM draft')
        rows = cursor.fetchall()
        return [json.loads(row[0]) for row in rows if row[0]]
    

def write_draft_teams(id, draft_teams_dict):
    _ensure_tables_initialized()
    # If passed a list of Team objects, convert each to dict
    if isinstance(draft_teams_dict, list) and draft_teams_dict and hasattr(draft_teams_dict[0], 'model_dump'):
        draft_teams_dict = [team.model_dump(by_alias=True) for team in draft_teams_dict]
    elif hasattr(draft_teams_dict, 'model_dump'):
        draft_teams_dict = draft_teams_dict.model_dump(by_alias=True)
    
    logger.info(f"Writing draft_teams for id: {id}")
    json_data = json.dumps(draft_teams_dict, default=str)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO draft_teams (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data=excluded.data
        ''', (id.lower(), json_data))
        conn.commit()
    logger.info(f"Successfully wrote draft_teams for id: {id}")
    _upload_after_write()


def read_draft_teams(id):
    _ensure_tables_initialized()
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM draft_teams WHERE id = ?', (id.lower(),))
        row = cursor.fetchone()
        result = json.loads(row[0]) if row else None
        if result:
            logger.info(f"Read draft_teams for id: {id}, has teams: {'teams' in result if isinstance(result, dict) else False}")
        else:
            logger.info(f"No draft_teams found for id: {id}")
        return result


def write_draft_history(id: str, data: dict) -> None:
    _ensure_tables_initialized()
    data_json = json.dumps(data)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO draft_history (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data=excluded.data
        ''', (id.lower(), data_json))
        conn.commit()
    _upload_after_write()


def read_draft_history(id: str) -> dict | None:
    _ensure_tables_initialized()
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM draft_history WHERE id = ?', (id.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None


def get_latest_player_pool() -> dict | None:
    """Get the most recently created player pool"""
    _ensure_tables_initialized()
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, data FROM player_pool ORDER BY rowid DESC LIMIT 1')
        row = cursor.fetchone()
        if row:
            pool_data = json.loads(row[1])
            return pool_data
        return None


def player_pool_exists() -> bool:
    """Check if any player pool exists in database"""
    _ensure_tables_initialized()
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM player_pool')
        count = cursor.fetchone()[0]
        return count > 0