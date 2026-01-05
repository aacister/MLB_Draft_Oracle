from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
from backend.config.settings import settings
from backend.data.postgresql.connection import get_engine, get_session


Base = declarative_base()
engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Use centralized settings
if not settings.is_dev:
    db_url = os.getenv("DB_URL")


if os.getenv("DEPLOYMENT_ENVIRONMENT") != 'DEV':
    # Use hardcoded PostgreSQL URL
    #db_url = os.getenv("DB_URL")
    #db_url = "postgresql://rootuser:RogerFedererNumber1@mlb-draft-oracle-database.cn46mqoccdqx.us-east-2.rds.amazonaws.com:5432/postgres"
    print(f"{db_url}")
    if db_url:
        try:
            # Add connection timeout and pool settings
            engine = create_engine(
                db_url,
                pool_timeout=5,  # 5 second timeout
                pool_recycle=300,  # Recycle connections after 5 minutes
                connect_args={"connect_timeout": 5}  # 5 second connection timeout
            )
            print("PostgreSQL engine created successfully")
        except Exception as e:
            print(f"Failed to create PostgreSQL engine: {e}")
            engine = None
    else:
        print("Warning: DB_URL not set, database functionality will be limited")
        engine = None

if engine is not None:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#else:
#    SessionLocal = None

class Team(Base):
    __tablename__ = 'teams'
    name = Column(String, primary_key=True)
    data = Column(JSONB) 

class Draft(Base):
    __tablename__ = 'drafts'
    id = Column(String, primary_key=True, index=True)
    data = Column(JSONB) 

class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True, index=True)
    data = Column(JSONB) 

class PlayerPool(Base):
    __tablename__ = 'player_pool'
    id = Column(String, primary_key=True, index=True)
    data = Column(JSONB) 

class DraftTeam(Base):
    __tablename__ = 'draft_teams'
    id = Column(String, primary_key=True, index=True)
    data = Column(JSONB) 

class DraftHistory(Base):
    __tablename__ = 'draft_history'
    id = Column(String, primary_key=True, index=True)
    data = Column(JSONB) 

if os.getenv("DEPLOYMENT_ENVIRONMENT") != 'DEV':
    Base.metadata.create_all(bind=engine)
