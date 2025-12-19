import os
import json
from pathlib import Path
import logging

MEMORY_DIR = Path("/app/memory")

def ensure_memory_dir():
    """Ensure memory directory exists"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def save_draft_state(draft_id: str, draft_data: dict):
    """Save draft state to memory directory"""
    try:
        ensure_memory_dir()
        file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
        with open(file_path, 'w') as f:
            json.dump(draft_data, f, indent=2)
        logging.info(f"Draft {draft_id} saved to memory at {file_path}")
    except Exception as e:
        logging.error(f"Failed to save draft {draft_id} to memory: {e}", exc_info=True)
        raise

def load_draft_state(draft_id: str) -> dict:
    """Load draft state from memory directory"""
    try:
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
    """Check if draft exists in memory directory"""
    file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
    return file_path.exists()

def delete_draft_state(draft_id: str):
    """Delete draft state from memory directory"""
    try:
        file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
        if file_path.exists():
            file_path.unlink()
            logging.info(f"Draft {draft_id} deleted from memory")
    except Exception as e:
        logging.error(f"Failed to delete draft {draft_id} from memory: {e}", exc_info=True)

def list_draft_states():
    """List all draft states in memory directory"""
    try:
        ensure_memory_dir()
        return [f.stem for f in MEMORY_DIR.glob("*.json")]
    except Exception as e:
        logging.error(f"Failed to list draft states: {e}", exc_info=True)
        return []

def cleanup_old_drafts(keep_count: int = 10):
    """
    Keep only the most recent N drafts in memory.
    Useful for preventing memory directory from growing indefinitely.
    """
    try:
        ensure_memory_dir()
        draft_files = sorted(
            MEMORY_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        # Delete older files beyond keep_count
        for old_file in draft_files[keep_count:]:
            old_file.unlink()
            logging.info(f"Cleaned up old draft from memory: {old_file.stem}")
            
    except Exception as e:
        logging.error(f"Failed to cleanup old drafts: {e}", exc_info=True)