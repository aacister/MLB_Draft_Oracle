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

# PostgreSQL RDS ONLY - all environments use RDS
logger = __import__('logging').getLogger(__name__)
logger.info("Using PostgreSQL RDS for all database operations")

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

# Create all tables in PostgreSQL RDS
try:
    Base.metadata.create_all(bind=engine)
    logger.info("PostgreSQL tables created/verified successfully")
except Exception as e:
    logger.error(f"Error creating PostgreSQL tables: {e}")
    raise