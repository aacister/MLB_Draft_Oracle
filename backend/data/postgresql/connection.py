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
    Retrieve database credentials from AWS Secrets Manager or environment variables.
    
    Returns:
        dict: Database connection parameters
    """
    global _db_credentials
    
    # Return cached credentials if available
    if _db_credentials:
        return _db_credentials
    
    if settings.is_dev:
        # Local development: Use SQLite
        _db_credentials = {
            'engine': 'sqlite',
            'database': settings.SQLITE_DB_PATH
        }
        logger.info(f"Using SQLite for local development at {settings.SQLITE_DB_PATH}")
    else:
        # AWS Lambda/Production: Use RDS PostgreSQL
        secret_arn = os.getenv('DB_SECRET_ARN')
        if not secret_arn:
            raise ValueError("DB_SECRET_ARN environment variable not set in production")
        
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
            logger.info(f"Retrieved PostgreSQL credentials from Secrets Manager")
            
        except ClientError as e:
            logger.error(f"Failed to retrieve database credentials: {e}")
            raise
        except KeyError as e:
            logger.error(f"Missing required key in secret: {e}")
            raise
    
    return _db_credentials


def get_connection_string() -> str:
    """
    Build database connection string based on environment.
    
    Returns:
        str: SQLAlchemy connection string
    """
    creds = get_db_credentials()
    
    if creds['engine'] == 'sqlite':
        # SQLite connection string
        return f"sqlite:///{creds['database']}"
    else:
        # PostgreSQL connection string
        return (
            f"postgresql+psycopg2://{creds['username']}:{creds['password']}"
            f"@{creds['host']}:{creds['port']}/{creds['database']}"
        )


def get_engine():
    """
    Get or create SQLAlchemy engine with appropriate configuration.
    
    Returns:
        Engine: SQLAlchemy engine instance
    """
    global _engine
    
    if _engine:
        return _engine
    
    connection_string = get_connection_string()
    creds = get_db_credentials()
    
    if creds['engine'] == 'sqlite':
        # SQLite configuration
        _engine = create_engine(
            connection_string,
            echo=False,
            connect_args={'check_same_thread': False}
        )
        
        # Enable foreign keys for SQLite
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            
        logger.info("Created SQLite engine")
    else:
        # PostgreSQL configuration for AWS Lambda
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
    _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    
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


# Context manager for sessions
class DatabaseSession:
    """Context manager for database sessions with automatic cleanup."""
    
    def __init__(self):
        self.session = None
    
    def __enter__(self) -> Session:
        self.session = get_session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type is not None:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()