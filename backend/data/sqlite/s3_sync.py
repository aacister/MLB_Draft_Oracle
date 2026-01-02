import boto3
import logging
import os
from pathlib import Path
from botocore.exceptions import ClientError
from backend.config.settings import settings

logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = boto3.client('s3')

def download_db_from_s3():
    """
    Download SQLite database from S3 to local path.
    Creates a new empty database if it doesn't exist in S3.
    """
    try:
        # Ensure directory exists
        db_path = Path(settings.SQLITE_DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to download from S3
        logger.info(f"Attempting to download database from s3://{settings.S3_BUCKET}/{settings.S3_DB_KEY}")
        s3_client.download_file(
            settings.S3_BUCKET,
            settings.S3_DB_KEY,
            settings.SQLITE_DB_PATH
        )
        logger.info(f"Successfully downloaded database to {settings.SQLITE_DB_PATH}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            logger.info(f"Database not found in S3 at s3://{settings.S3_BUCKET}/{settings.S3_DB_KEY}")
            logger.info("A new database will be created on first write")
            return False
        else:
            logger.error(f"Error downloading database from S3: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error downloading database: {e}")
        raise


def upload_db_to_s3():
    """
    Upload SQLite database from local path to S3.
    """
    try:
        # Check if database file exists
        if not os.path.exists(settings.SQLITE_DB_PATH):
            logger.warning(f"Database file not found at {settings.SQLITE_DB_PATH}, skipping upload")
            return False
        
        # Get file size for logging
        file_size = os.path.getsize(settings.SQLITE_DB_PATH)
        logger.info(f"Uploading database ({file_size} bytes) to s3://{settings.S3_BUCKET}/{settings.S3_DB_KEY}")
        
        # Upload to S3
        s3_client.upload_file(
            settings.SQLITE_DB_PATH,
            settings.S3_BUCKET,
            settings.S3_DB_KEY
        )
        logger.info("Successfully uploaded database to S3")
        return True
        
    except Exception as e:
        logger.error(f"Error uploading database to S3: {e}")
        raise


def ensure_db_downloaded():
    """
    Ensure database is downloaded from S3 before any operations.
    Call this at application startup or before first database access.
    """
    if settings.is_lambda:
        # In Lambda, always try to download from S3
        download_db_from_s3()
    else:
        # In local/dev environment, only download if local file doesn't exist
        if not os.path.exists(settings.SQLITE_DB_PATH):
            logger.info("Local database not found, attempting to download from S3")
            download_db_from_s3()
        else:
            logger.info(f"Using existing local database at {settings.SQLITE_DB_PATH}")