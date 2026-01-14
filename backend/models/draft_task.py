from pydantic import BaseModel, Field
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


class DraftTask(BaseModel):
    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Task status: processing, drafting, completed, error, not_found")
    message: str = Field(default="", description="Status message")
    player_name: Optional[str] = Field(default=None, description="Player being drafted")
    player_id: Optional[int] = Field(default=None, description="Player ID if completed")
    team_name: Optional[str] = Field(default=None, description="Team drafting")
    draft_id: Optional[str] = Field(default=None, description="Draft ID")
    round: Optional[int] = Field(default=None, description="Round number")
    pick: Optional[int] = Field(default=None, description="Pick number")
    reason: Optional[str] = Field(default=None, description="Rationale for pick")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    @classmethod
    def get(cls, task_id: str):
        """Get task from database with explicit connection handling"""
        from backend.data.postgresql.unified_db import read_draft_task
        
        logger.info(f"[DraftTask.get] Loading task {task_id} from PostgreSQL RDS")
        
        try:
            fields = read_draft_task(task_id)
            if not fields:
                logger.warning(f"[DraftTask.get] Task {task_id} not found in database")
                return None
            
            logger.info(f"[DraftTask.get] ✓ Found task {task_id} with status: {fields.get('status')}")
            return cls(**fields)
        except Exception as e:
            logger.error(f"[DraftTask.get] Error loading task {task_id}: {e}", exc_info=True)
            return None

    def save(self):
        """Save task to database with explicit connection handling and verification"""
        from backend.data.postgresql.unified_db import write_draft_task, read_draft_task
        
        try:
            data = self.model_dump(by_alias=True)
            
            logger.info(f"[DraftTask.save] Saving task {self.task_id} with status: {self.status}")
            
            # Write to database
            write_draft_task(self.task_id, data)
            
            # CRITICAL: Verify the write succeeded by reading it back
            verify = read_draft_task(self.task_id)
            if verify:
                logger.info(f"[DraftTask.save] ✓ Task {self.task_id} verified in database")
            else:
                logger.error(f"[DraftTask.save] ✗ Task {self.task_id} NOT FOUND after save!")
                raise Exception(f"Failed to verify task {self.task_id} in database")
                
        except Exception as e:
            logger.error(f"[DraftTask.save] Error saving task {self.task_id}: {e}", exc_info=True)
            raise

    @classmethod
    def create(cls, task_id: str, draft_id: str, team_name: str, player_name: str, round: int, pick: int):
        """Create a new task and ensure it's saved"""
        logger.info(f"[DraftTask.create] Creating task {task_id} for {player_name}")
        
        task = cls(
            task_id=task_id,
            status="processing",
            message=f"Starting draft for {player_name}...",
            player_name=player_name,
            team_name=team_name,
            draft_id=draft_id,
            round=round,
            pick=pick
        )
        
        # Save and verify
        task.save()
        
        # Double-check it exists
        verify = cls.get(task_id)
        if not verify:
            raise Exception(f"Task {task_id} not found immediately after creation!")
        
        logger.info(f"[DraftTask.create] ✓ Task {task_id} created and verified")
        return task

    def update_status(self, status: str, message: str = "", **kwargs):
        """Update task status"""
        logger.info(f"[DraftTask.update_status] Task {self.task_id}: {self.status} -> {status}")
        
        self.status = status
        self.message = message
        
        # Update any additional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.save()

    def mark_completed(self, player_id: int, player_name: str, reason: str):
        """Mark task as completed"""
        self.update_status(
            status="completed",
            message=f"Successfully drafted {player_name}",
            player_id=player_id,
            player_name=player_name,
            reason=reason
        )

    def mark_error(self, error: str):
        """Mark task as errored"""
        self.update_status(
            status="error",
            message="Draft pick failed",
            error=error
        )