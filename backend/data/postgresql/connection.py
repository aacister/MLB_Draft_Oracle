import os
import json
import logging
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import boto3
from botocore.exceptions import ClientError
from backend.config.settings import settings

logger = logging.getLogger(__name__)

# Global variables for connection caching
_engine = None
_session_factory = None
_db_credentials = None


def get_db_credentials() -> dict:
    """
    Retrieve database credentials from AWS Secrets Manager.
    PostgreSQL RDS ONLY - SQLite support removed.
    
    Returns:
        dict: Database connection parameters for PostgreSQL
    """
    global _db_credentials
    
    # Return cached credentials if available
    if _db_credentials:
        return _db_credentials
    
    # AWS Lambda/Production: Use RDS PostgreSQL ONLY
    secret_arn = os.getenv('DB_SECRET_ARN')
    if not secret_arn:
        raise ValueError("DB_SECRET_ARN environment variable not set - PostgreSQL RDS is required")
    
    try:
        # Create Secrets Manager client
        region = settings.AWS_REGION if hasattr(settings, 'AWS_REGION') else 'us-east-2'
        client = boto3.client('secretsmanager', region_name=region)
        
        # Retrieve secret
        response = client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        
        _db_credentials = {
            'engine': 'postgresql',
            'host': secret['host'],
            'port': secret.get('port', 5432),
            'database': secret['dbname'],
            'username': secret['username'],
            'password': secret['password']
        }
        logger.info(f"Retrieved PostgreSQL credentials from Secrets Manager for host: {secret['host']}")
        
    except ClientError as e:
        logger.error(f"Failed to retrieve database credentials from Secrets Manager: {e}")
        raise
    except KeyError as e:
        logger.error(f"Missing required key in secret: {e}")
        raise
    
    return _db_credentials


def get_connection_string() -> str:
    """
    Build PostgreSQL RDS connection string.
    
    Returns:
        str: SQLAlchemy connection string for PostgreSQL
    """
    creds = get_db_credentials()
    
    # PostgreSQL connection string ONLY
    return (
        f"postgresql+psycopg2://{creds['username']}:{creds['password']}"
        f"@{creds['host']}:{creds['port']}/{creds['database']}"
    )


def get_engine():
    """
    Get or create SQLAlchemy engine for PostgreSQL RDS.
    
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
    logger.info("Created PostgreSQL engine for RDS")
    
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
    global _engine, _session_factory, _db_credentials
    
    if _engine:
        _engine.dispose()
        _engine = None
    
    _session_factory = None
    _db_credentials = None
    
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