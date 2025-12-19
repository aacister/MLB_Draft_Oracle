import os
import json
from pathlib import Path

MEMORY_DIR = Path("/app/memory")

def ensure_memory_dir():
    """Ensure memory directory exists"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def save_draft_state(draft_id: str, draft_data: dict):
    """Save draft state to memory directory"""
    ensure_memory_dir()
    file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
    with open(file_path, 'w') as f:
        json.dump(draft_data, f, indent=2)

def load_draft_state(draft_id: str) -> dict:
    """Load draft state from memory directory"""
    file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
    if not file_path.exists():
        return None
    with open(file_path, 'r') as f:
        return json.load(f)

def delete_draft_state(draft_id: str):
    """Delete draft state from memory directory"""
    file_path = MEMORY_DIR / f"{draft_id.lower()}.json"
    if file_path.exists():
        file_path.unlink()

def list_draft_states():
    """List all draft states in memory directory"""
    ensure_memory_dir()
    return [f.stem for f in MEMORY_DIR.glob("*.json")]