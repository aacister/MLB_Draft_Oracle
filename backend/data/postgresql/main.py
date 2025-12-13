from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import PendingRollbackError
from .models import Team, PlayerPool, Player, Draft, DraftTeam, DraftHistory, SessionLocal, engine
import json

session = SessionLocal()

def write_postgres_team(name, team_dict):
    try:
        json_data = json.dumps(team_dict)
        insert_stmt = insert(Team).values(name=name, data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['name'], set_=dict(data=json_data))
        session.execute(do_update_stmt)
        session.commit()
    except PendingRollbackError:
        session.rollback()  # Roll back the invalid transaction
        # Optionally, close and recreate the session if issues persist
    except Exception as e:
        session.rollback()  # Always rollback on other errors to prevent this state
        raise e

def read_postgres_team(name):    # Retrieve data 
    retrieved_item = session.query(Team).filter_by(name=name).first()
    return json.loads(retrieved_item.data) if retrieved_item else None

def write_postgres_player_pool(id, player_pool_dict):
    try:
        if hasattr(player_pool_dict, 'model_dump'):
            player_pool_dict = player_pool_dict.model_dump(by_alias=True)
        json_data = json.dumps(player_pool_dict, default=str)
        insert_stmt = insert(PlayerPool).values(id=id, data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'], set_=dict(data=json_data))
        session.execute(do_update_stmt)
        session.commit()
    except PendingRollbackError:
        session.rollback()  # Roll back the invalid transaction
    except Exception as e:
        session.rollback()  # Always rollback on other errors to prevent this state
        raise e



def read_postgres_player_pool(id):
    retrieved_item = session.query(PlayerPool).filter_by(id=id).first()
    return json.loads(retrieved_item.data) if retrieved_item else None


def write_postgres_player(id, player_dict):
    try:
        json_data = json.dumps(player_dict, default=str)
        insert_stmt = insert(Player).values(id=id, data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'], set_=dict(data=json_data))
        session.execute(do_update_stmt)
        session.commit()
    except PendingRollbackError:
        session.rollback()  # Roll back the invalid transaction
    except Exception as e:
        session.rollback()  # Always rollback on other errors to prevent this state
        raise e


def read_postgres_player(id):
    #retrieved_item = session.query(Player).filter_by(id=id).first()
    retrieved_item = session.query(Player).filter(Player.id == str(id)).one()
    print(f"Retrieved player: {retrieved_item}")
    return json.loads(retrieved_item.data) if retrieved_item else None


def write_postgres_draft(id: str, data: dict) -> None:
    try:
        json_data = json.dumps(data)
        insert_stmt = insert(Draft).values(id=id, data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'], set_=dict(data=json_data))
        session.execute(do_update_stmt)
        session.commit()
    except PendingRollbackError:
        session.rollback()  # Roll back the invalid transaction
    except Exception as e:
        session.rollback()  # Always rollback on other errors to prevent this state
        raise e


def read_postgres_draft(id: str) -> dict | None:
    retrieved_item = session.query(Draft).filter_by(id=id).first()
    return json.loads(retrieved_item.data) if retrieved_item else None


def read_postgres_drafts() -> list[dict | None]:
    result_list = []
    drafts = session.query(Draft).all()
    for draft in drafts:
        draft_json = json.loads(draft.data)
        result_list.append(draft_json)
    return result_list

    
    
def write_postgres_draft_teams(id, draft_teams_dict):
    try:
        if isinstance(draft_teams_dict, list) and draft_teams_dict and hasattr(draft_teams_dict[0], 'model_dump'):
            draft_teams_dict = [team.model_dump(by_alias=True) for team in draft_teams_dict]
        elif hasattr(draft_teams_dict, 'model_dump'):
            draft_teams_dict = draft_teams_dict.model_dump(by_alias=True)
        json_data = json.dumps(draft_teams_dict, default=str)
        insert_stmt = insert(DraftTeam).values(id=id, data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'], set_=dict(data=json_data)
        )
        session.execute(do_update_stmt)
        session.commit()
    except PendingRollbackError:
        session.rollback()  # Roll back the invalid transaction
    except Exception as e:
        session.rollback()  # Always rollback on other errors to prevent this state
        raise e

    

def read_postgres_draft_teams(id):
    retrieved_item = session.query(DraftTeam).filter_by(id=id).first()
    return json.loads(retrieved_item.data) if retrieved_item else None

def write_postgres_draft_history(id: str, data: dict) -> None:
    try:
        json_data = json.dumps(data)
        insert_stmt = insert(DraftHistory).values(id=id, data=json_data)
        do_update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'], set_=dict(data=json_data))
        session.execute(do_update_stmt)
        session.commit()
    except PendingRollbackError:
        session.rollback()  # Roll back the invalid transaction

    except Exception as e:
        session.rollback()  # Always rollback on other errors to prevent this state
        raise e

    
def read_postgres_draft_history(id: str) -> dict | None:
    retrieved_item = session.query(DraftHistory).filter_by(id=id).first()
    return json.loads(retrieved_item.data) if retrieved_item else None


    
