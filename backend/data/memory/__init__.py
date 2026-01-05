import os
import json
from pathlib import Path
import logging
from backend.config.settings import settings

# Use centralized settings
MEMORY_DIR = Path(settings.MEMORY_DIR)

# Log environment detection on module load
logging.info(f"Memory module loaded - Lambda environment: {settings.is_lambda}")
logging.info(f"Memory storage location: {'S3' if settings.is_lambda else 'Local filesystem'}")
if settings.is_lambda:
    logging.info(f"S3 Memory Bucket: {settings.S3_MEMORY_BUCKET}")
else:
    logging.info(f"Local Memory Directory: {MEMORY_DIR}")

def ensure_memory_dir():
    """Ensure memory directory exists (only for non-Lambda environments)"""
    if not settings.is_lambda:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    # In Lambda, we don't need to create directories since we use S3

def save_draft_state(draft_id: str, draft_data: dict):
    """Save draft state to memory (local directory or S3 based on environment)"""
    try:
        if settings.is_lambda:
            # Use S3 in Lambda environment
            logging.info(f"Using S3 storage for draft {draft_id}")
            from backend.data.memory.s3_sync import upload_memory_to_s3
            upload_memory_to_s3(draft_id.lower(), draft_data)
            logging.info(f"Draft {draft_id} saved to S3 bucket {settings.S3_MEMORY_BUCKET}")
        else:
            # Use local directory in non-Lambda environment
            logging.info(f"Using local filesystem storage for draft {draft_id}")
            ensure_memory_dir()
            file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
            with open(file_path, 'w') as f:
                json.dump(draft_data, f, indent=2)
            logging.info(f"Draft {draft_id} saved to memory at {file_path}")
    except Exception as e:
        logging.error(f"Failed to save draft {draft_id} to memory: {e}", exc_info=True)
        raise

def load_draft_state(draft_id: str) -> dict:
    """Load draft state from memory (local directory or S3 based on environment)"""
    try:
        if settings.is_lambda:
            # Use S3 in Lambda environment
            logging.info(f"Loading draft {draft_id} from S3")
            from backend.data.memory.s3_sync import download_memory_from_s3
            data = download_memory_from_s3(draft_id.lower())
            if data:
                logging.info(f"Draft {draft_id} loaded from S3")
            else:
                logging.debug(f"Draft {draft_id} not found in S3")
            return data
        else:
            # Use local directory in non-Lambda environment
            logging.info(f"Loading draft {draft_id} from local filesystem")
            file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
            if not file_path.exists():
                logging.debug(f"Draft {draft_id} not found in memory")
                return None
            with open(file_path, 'r') as f:
                data = json.load(f)
            logging.info(f"Draft {draft_id} loaded from memory")
            return data
    except Exception as e:
        logging.error(f"Failed to load draft {draft_id} from memory: {e}", exc_info=True)
        return None

def draft_exists_in_memory(draft_id: str) -> bool:
    """Check if draft exists in memory (local directory or S3 based on environment)"""
    try:
        if settings.is_lambda:
            from backend.data.memory.s3_sync import memory_exists_in_s3
            exists = memory_exists_in_s3(draft_id.lower())
            logging.debug(f"Draft {draft_id} exists in S3: {exists}")
            return exists
        else:
            file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
            exists = file_path.exists()
            logging.debug(f"Draft {draft_id} exists in local memory: {exists}")
            return exists
    except Exception as e:
        logging.error(f"Error checking if draft {draft_id} exists: {e}")
        return False

def delete_draft_state(draft_id: str):
    """Delete draft state from memory (local directory or S3 based on environment)"""
    try:
        if settings.is_lambda:
            from backend.data.memory.s3_sync import delete_memory_from_s3
            delete_memory_from_s3(draft_id.lower())
            logging.info(f"Draft {draft_id} deleted from S3")
        else:
            file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
            if file_path.exists():
                file_path.unlink()
                logging.info(f"Draft {draft_id} deleted from memory")
    except Exception as e:
        logging.error(f"Failed to delete draft {draft_id} from memory: {e}", exc_info=True)

def list_draft_states():
    """List all draft states in memory (local directory or S3 based on environment)"""
    try:
        if settings.is_lambda:
            from backend.data.memory.s3_sync import list_memory_states_in_s3
            draft_ids = list_memory_states_in_s3()
            logging.info(f"Listed {len(draft_ids)} drafts from S3")
            return draft_ids
        else:
            ensure_memory_dir()
            draft_ids = [f.stem for f in MEMORY_DIR.glob("*.json")]
            logging.info(f"Listed {len(draft_ids)} drafts from local memory")
            return draft_ids
    except Exception as e:
        logging.error(f"Failed to list draft states: {e}", exc_info=True)
        return []

def cleanup_old_drafts(keep_count: int = 10):
    """
    Keep only the most recent N drafts in memory.
    Useful for preventing memory storage from growing indefinitely.
    Note: In Lambda/S3 environment, this uses last modified time from S3.
    """
    try:
        if settings.is_lambda:
            # For S3, we need to list objects with metadata and sort by last modified
            import boto3
            s3_client = boto3.client('s3')
            
            response = s3_client.list_objects_v2(
                Bucket=settings.S3_MEMORY_BUCKET
            )
            
            if 'Contents' not in response:
                logging.info("No objects found in S3 bucket for cleanup")
                return
            
            # Sort by LastModified descending (newest first)
            objects = sorted(
                response['Contents'],
                key=lambda x: x['LastModified'],
                reverse=True
            )
            
            # Delete older objects beyond keep_count
            deleted_count = 0
            for old_obj in objects[keep_count:]:
                s3_client.delete_object(
                    Bucket=settings.S3_MEMORY_BUCKET,
                    Key=old_obj['Key']
                )
                logging.info(f"Cleaned up old draft from S3: {old_obj['Key']}")
                deleted_count += 1
            
            if deleted_count > 0:
                logging.info(f"Cleaned up {deleted_count} old drafts from S3")
        else:
            # Local directory cleanup
            ensure_memory_dir()
            draft_files = sorted(
                MEMORY_DIR.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            # Delete older files beyond keep_count
            deleted_count = 0
            for old_file in draft_files[keep_count:]:
                old_file.unlink()
                logging.info(f"Cleaned up old draft from memory: {old_file.stem}")
                deleted_count += 1
            
            if deleted_count > 0:
                logging.info(f"Cleaned up {deleted_count} old drafts from local memory")
            
    except Exception as e:
        logging.error(f"Failed to cleanup old drafts: {e}", exc_info=True)