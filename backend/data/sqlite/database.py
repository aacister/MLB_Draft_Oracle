import sqlite3
import json
from datetime import datetime
import os

#DB = "backend/data/mlbdraftoracle.db"
DB = "/app/sqlite-data/mlbdraftoracle.db" 
'''
if os.path.exists(file_path):
    try:
        os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file '{file_path}': {e}")
else:
    print(f"File '{file_path}' does not exist")    
'''
#if os.getenv("DEPLOYMENT_ENVIRONMENT") == 'DEV':
with sqlite3.connect(DB) as conn:
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS teams (name TEXT PRIMARY KEY, data TEXT)')        
    cursor.execute('CREATE TABLE IF NOT EXISTS draft (id TEXT PRIMARY KEY, data TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, data TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS player_pool (id TEXT PRIMARY KEY, data TEXT)')        
    cursor.execute('CREATE TABLE IF NOT EXISTS draft_teams (id TEXT PRIMARY KEY, data TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS draft_history (id TEXT PRIMARY KEY, data TEXT)')
    conn.commit()


def write_team(name, team_dict):
    json_data = json.dumps(team_dict)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO teams (name, data)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET data=excluded.data
        ''', (name.lower(), json_data))
        conn.commit()

def read_team(name):
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM teams WHERE name = ?', (name.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None

def write_player_pool(id, player_pool_dict):
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

def read_player_pool(id):
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM player_pool WHERE id = ?', (id.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None

def write_player(id, player_dict):
    json_data = json.dumps(player_dict)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO players (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data=excluded.data
        ''', (id, json_data))
        conn.commit()

def read_player(id):
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM players WHERE id = ?', (id,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    

def write_draft(id: str, data: dict) -> None:
    print(f"Writing draft for id: {id}")
    print(f"Draft data keys: {data.keys()}")
    print(f"Teams in draft data: {'teams' in data}")
    
    data_json = json.dumps(data, default=str)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO draft (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data=excluded.data
        ''', (id.lower(), data_json))
        conn.commit()
    print(f"Successfully wrote draft for id: {id}")

def read_draft(id: str) -> dict | None:
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM draft WHERE id = ?', (id.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None

def read_drafts() -> list[dict | None]:
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM draft')
        rows = cursor.fetchall()
        return [json.loads(row[0]) for row in rows if row[0]]
    
def write_draft_teams(id, draft_teams_dict):
    # If passed a list of Team objects, convert each to dict
    if isinstance(draft_teams_dict, list) and draft_teams_dict and hasattr(draft_teams_dict[0], 'model_dump'):
        draft_teams_dict = [team.model_dump(by_alias=True) for team in draft_teams_dict]
    elif hasattr(draft_teams_dict, 'model_dump'):
        draft_teams_dict = draft_teams_dict.model_dump(by_alias=True)
    
    print(f"Writing draft_teams for id: {id}")
    print(f"Draft teams dict keys: {draft_teams_dict.keys() if isinstance(draft_teams_dict, dict) else 'not a dict'}")
    
    json_data = json.dumps(draft_teams_dict, default=str)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO draft_teams (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data=excluded.data
        ''', (id.lower(), json_data))
        conn.commit()
    print(f"Successfully wrote draft_teams for id: {id}")

def read_draft_teams(id):
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM draft_teams WHERE id = ?', (id.lower(),))
        row = cursor.fetchone()
        result = json.loads(row[0]) if row else None
        if result:
            print(f"Read draft_teams for id: {id}, has teams: {'teams' in result if isinstance(result, dict) else False}")
        else:
            print(f"No draft_teams found for id: {id}")
        return result



    
def write_draft_history(id: str, data: dict) -> None:
    data_json = json.dumps(data)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO draft_history (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data=excluded.data
        ''', (id.lower(), data_json))
        conn.commit()

def read_draft_history(id: str) -> dict | None:
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM draft_history WHERE id = ?', (id.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None

def get_latest_player_pool() -> dict | None:
    """Get the most recently created player pool"""
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
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM player_pool')
        count = cursor.fetchone()[0]
        return count > 0