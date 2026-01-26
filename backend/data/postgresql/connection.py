# ============================================================================
# backend/data/postgresql/connection.py 
# ============================================================================
import os
import logging
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from backend.config.settings import settings

logger = logging.getLogger(__name__)

# Global variables for connection caching
_engine = None
_session_factory = None


def get_connection_string() -> str:
    """
    Build PostgreSQL connection string from DB_URL environment variable.
    
    Returns:
        str: SQLAlchemy connection string for PostgreSQL
    
    Raises:
        ValueError: If DB_URL is not set
    """
    db_url = os.getenv('DB_URL')
    
    if not db_url:
        raise ValueError(
            "DB_URL environment variable not set. "
            "Expected format: postgresql+psycopg2://user:password@host:port/database"
        )
    
    logger.info(f"Using database connection from DB_URL environment variable")
    return db_url


def get_engine():
    """
    Get or create SQLAlchemy engine for PostgreSQL.
    
    Returns:
        Engine: SQLAlchemy engine instance
    """
    global _engine
    
    if _engine:
        return _engine
    
    connection_string = get_connection_string()
    
    # PostgreSQL configuration for AWS RDS
    _engine = create_engine(
        connection_string,
        poolclass=NullPool,  # No connection pooling in Lambda
        echo=False,
        pool_pre_ping=True,  # Verify connections before using
        connect_args={
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30 second timeout
        }
    )
    logger.info("Created PostgreSQL engine")
    
    return _engine


def get_session_factory():
    """
    Get or create session factory.
    
    Returns:
        sessionmaker: SQLAlchemy session factory
    """
    global _session_factory
    
    if _session_factory:
        return _session_factory
    
    engine = get_engine()
    _session_factory = sessionmaker(bind=engine, expire_on_commit=False, autocommit=False, autoflush=False)
    
    return _session_factory


def get_session() -> Session:
    """
    Create a new database session.
    
    Returns:
        Session: SQLAlchemy session instance
    """
    factory = get_session_factory()
    return factory()


def close_connections():
    """
    Close all database connections and clear cached resources.
    Useful for cleanup in Lambda functions.
    """
    global _engine, _session_factory
    
    if _engine:
        _engine.dispose()
        _engine = None
    
    _session_factory = None
    
    logger.info("Closed all database connections")


# Context manager for sessions - FIXED VERSION
class DatabaseSession:
    """Context manager for database sessions with automatic cleanup and explicit commit."""
    
    def __init__(self):
        self.session = None
    
    def __enter__(self) -> Session:
        self.session = get_session()
        logger.debug(f"[DatabaseSession] Opened new session: {id(self.session)}")
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            try:
                if exc_type is not None:
                    # Exception occurred, rollback
                    logger.warning(f"[DatabaseSession] Rolling back session {id(self.session)} due to exception")
                    self.session.rollback()
                else:
                    # No exception, commit changes
                    logger.debug(f"[DatabaseSession] Committing session {id(self.session)}")
                    self.session.commit()
            except Exception as e:
                logger.error(f"[DatabaseSession] Error during commit/rollback: {e}")
                try:
                    self.session.rollback()
                except:
                    pass
            finally:
                logger.debug(f"[DatabaseSession] Closing session {id(self.session)}")
                self.session.close()