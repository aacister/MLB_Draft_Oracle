"""
DEPRECATED: Memory storage module
All memory storage functionality has been disabled in favor of PostgreSQL RDS.
This file is preserved for reference but all functions are no-ops.
"""
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ALL MEMORY STORAGE FUNCTIONS ARE DISABLED
# Data is now stored exclusively in PostgreSQL RDS
# ============================================================================

def save_draft_state(draft_id: str, draft_data: dict):
    """DEPRECATED: Memory storage disabled. Using PostgreSQL only."""
    logger.debug(f"save_draft_state called for {draft_id} but memory storage is disabled")
    pass

def load_draft_state(draft_id: str) -> dict:
    """DEPRECATED: Memory storage disabled. Using PostgreSQL only."""
    logger.debug(f"load_draft_state called for {draft_id} but memory storage is disabled")
    return None

def draft_exists_in_memory(draft_id: str) -> bool:
    """DEPRECATED: Memory storage disabled. Using PostgreSQL only."""
    logger.debug(f"draft_exists_in_memory called for {draft_id} but memory storage is disabled")
    return False

def delete_draft_state(draft_id: str):
    """DEPRECATED: Memory storage disabled. Using PostgreSQL only."""
    logger.debug(f"delete_draft_state called for {draft_id} but memory storage is disabled")
    pass

def list_draft_states():
    """DEPRECATED: Memory storage disabled. Using PostgreSQL only."""
    logger.debug("list_draft_states called but memory storage is disabled")
    return []

def cleanup_old_drafts(keep_count: int = 10):
    """DEPRECATED: Memory storage disabled. Using PostgreSQL only."""
    logger.debug("cleanup_old_drafts called but memory storage is disabled")
    pass

# ============================================================================
# ORIGINAL IMPLEMENTATION (PRESERVED FOR REFERENCE)
# ============================================================================
# import os
# import json
# from pathlib import Path
# import logging
# from backend.config.settings import settings
# 
# # Use centralized settings
# MEMORY_DIR = Path(settings.MEMORY_DIR)
# 
# # Log environment detection on module load
# logging.info(f"Memory module loaded - Lambda environment: {settings.is_lambda}")
# logging.info(f"Memory storage location: {'S3' if settings.is_lambda else 'Local filesystem'}")
# if settings.is_lambda:
#     logging.info(f"S3 Memory Bucket: {settings.S3_MEMORY_BUCKET}")
# else:
#     logging.info(f"Local Memory Directory: {MEMORY_DIR}")
# 
# def ensure_memory_dir():
#     """Ensure memory directory exists (only for non-Lambda environments)"""
#     if not settings.is_lambda:
#         MEMORY_DIR.mkdir(parents=True, exist_ok=True)
#     # In Lambda, we don't need to create directories since we use S3
# 
# def save_draft_state(draft_id: str, draft_data: dict):
#     """Save draft state to memory (local directory or S3 based on environment)"""
#     try:
#         if settings.is_lambda:
#             # Use S3 in Lambda environment
#             logging.info(f"Using S3 storage for draft {draft_id}")
#             from backend.data.memory.s3_sync import upload_memory_to_s3
#             upload_memory_to_s3(draft_id.lower(), draft_data)
#             logging.info(f"Draft {draft_id} saved to S3 bucket {settings.S3_MEMORY_BUCKET}")
#         else:
#             # Use local directory in non-Lambda environment
#             logging.info(f"Using local filesystem storage for draft {draft_id}")
#             ensure_memory_dir()
#             file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
#             with open(file_path, 'w') as f:
#                 json.dump(draft_data, f, indent=2)
#             logging.info(f"Draft {draft_id} saved to memory at {file_path}")
#     except Exception as e:
#         logging.error(f"Failed to save draft {draft_id} to memory: {e}", exc_info=True)
#         raise
