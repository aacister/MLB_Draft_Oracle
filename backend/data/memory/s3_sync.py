import boto3
import logging
import json
from pathlib import Path
from botocore.exceptions import ClientError
from backend.config.settings import settings

logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = boto3.client('s3')

def upload_memory_to_s3(draft_id: str, data: dict):
    """
    Upload draft memory state to S3.
    
    Args:
        draft_id: The ID of the draft
        data: The draft data dictionary to upload
    """
    try:
        # Convert data to JSON string
        json_data = json.dumps(data, indent=2)
        
        # S3 key path
        s3_key = f"{draft_id.lower()}.json"
        
        logger.info(f"Uploading memory state for draft {draft_id} to s3://{settings.S3_MEMORY_BUCKET}/{s3_key}")
        
        # Upload to S3
        s3_client.put_object(
            Bucket=settings.S3_MEMORY_BUCKET,
            Key=s3_key,
            Body=json_data.encode('utf-8'),
            ContentType='application/json'
        )
        
        logger.info(f"Successfully uploaded memory state for draft {draft_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error uploading memory state for draft {draft_id} to S3: {e}")
        raise


def download_memory_from_s3(draft_id: str) -> dict:
    """
    Download draft memory state from S3.
    
    Args:
        draft_id: The ID of the draft
        
    Returns:
        Dictionary containing the draft state, or None if not found
    """
    try:
        s3_key = f"{draft_id.lower()}.json"
        
        logger.info(f"Attempting to download memory state for draft {draft_id} from s3://{settings.S3_MEMORY_BUCKET}/{s3_key}")
        
        # Download from S3
        response = s3_client.get_object(
            Bucket=settings.S3_MEMORY_BUCKET,
            Key=s3_key
        )
        
        # Parse JSON data
        json_data = response['Body'].read().decode('utf-8')
        data = json.loads(json_data)
        
        logger.info(f"Successfully downloaded memory state for draft {draft_id}")
        return data
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            logger.info(f"Memory state not found in S3 for draft {draft_id}")
            return None
        else:
            logger.error(f"Error downloading memory state from S3: {e}")
            return None
    except Exception as e:
        logger.error(f"Unexpected error downloading memory state: {e}")
        return None


def delete_memory_from_s3(draft_id: str):
    """
    Delete draft memory state from S3.
    
    Args:
        draft_id: The ID of the draft
    """
    try:
        s3_key = f"{draft_id.lower()}.json"
        
        logger.info(f"Deleting memory state for draft {draft_id} from s3://{settings.S3_MEMORY_BUCKET}/{s3_key}")
        
        s3_client.delete_object(
            Bucket=settings.S3_MEMORY_BUCKET,
            Key=s3_key
        )
        
        logger.info(f"Successfully deleted memory state for draft {draft_id}")
        
    except Exception as e:
        logger.error(f"Error deleting memory state from S3: {e}")
        raise


def list_memory_states_in_s3():
    """
    List all draft memory states in S3.
    
    Returns:
        List of draft IDs (without .json extension)
    """
    try:
        logger.info(f"Listing memory states in s3://{settings.S3_MEMORY_BUCKET}")
        
        response = s3_client.list_objects_v2(
            Bucket=settings.S3_MEMORY_BUCKET
        )
        
        if 'Contents' not in response:
            return []
        
        # Extract draft IDs from keys (remove .json extension)
        draft_ids = [
            obj['Key'].replace('.json', '')
            for obj in response['Contents']
            if obj['Key'].endswith('.json')
        ]
        
        return draft_ids
        
    except Exception as e:
        logger.error(f"Error listing memory states from S3: {e}")
        return []


def memory_exists_in_s3(draft_id: str) -> bool:
    """
    Check if a draft memory state exists in S3.
    
    Args:
        draft_id: The ID of the draft
        
    Returns:
        True if the memory state exists, False otherwise
    """
    try:
        s3_key = f"{draft_id.lower()}.json"
        
        s3_client.head_object(
            Bucket=settings.S3_MEMORY_BUCKET,
            Key=s3_key
        )
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            return False
        else:
            logger.error(f"Error checking memory state existence in S3: {e}")
            return False