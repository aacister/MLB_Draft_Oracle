from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.delete("/admin/cleanup-database")
async def cleanup_database():
    """
    DANGER: This endpoint completely wipes all draft data from PostgreSQL RDS.
    
    Deletes:
    - All drafts
    - All player pools
    - All players
    - All teams
    - All draft teams
    - All draft history
    - All draft tasks
    
    Use this to reset the database to a clean state.
    After calling this endpoint, the next draft creation will:
    1. Fetch fresh 2025 season players from MLB Stats API
    2. Create a new player pool
    3. Initialize new teams
    4. Start a fresh draft
    
    Returns:
        JSON response with counts of deleted records
    """
    logger.info("=" * 80)
    logger.info("DATABASE CLEANUP REQUESTED")
    logger.info("=" * 80)
    
    try:
        from backend.data.postgresql.connection import DatabaseSession
        from backend.data.postgresql.models import (
            Draft, 
            DraftHistory, 
            DraftTeam, 
            Player, 
            PlayerPool, 
            Team,
            DraftTask
        )
        
        deleted_counts = {}
        
        with DatabaseSession() as session:
            # Delete in reverse dependency order to avoid foreign key issues
            
            # 1. Delete draft tasks
            logger.info("Deleting draft tasks...")
            draft_tasks_count = session.query(DraftTask).count()
            session.query(DraftTask).delete()
            deleted_counts['draft_tasks'] = draft_tasks_count
            logger.info(f"✓ Deleted {draft_tasks_count} draft tasks")
            
            # 2. Delete draft history
            logger.info("Deleting draft history...")
            draft_history_count = session.query(DraftHistory).count()
            session.query(DraftHistory).delete()
            deleted_counts['draft_history'] = draft_history_count
            logger.info(f"✓ Deleted {draft_history_count} draft history records")
            
            # 3. Delete draft teams
            logger.info("Deleting draft teams...")
            draft_teams_count = session.query(DraftTeam).count()
            session.query(DraftTeam).delete()
            deleted_counts['draft_teams'] = draft_teams_count
            logger.info(f"✓ Deleted {draft_teams_count} draft team records")
            
            # 4. Delete teams
            logger.info("Deleting teams...")
            teams_count = session.query(Team).count()
            session.query(Team).delete()
            deleted_counts['teams'] = teams_count
            logger.info(f"✓ Deleted {teams_count} teams")
            
            # 5. Delete drafts
            logger.info("Deleting drafts...")
            drafts_count = session.query(Draft).count()
            session.query(Draft).delete()
            deleted_counts['drafts'] = drafts_count
            logger.info(f"✓ Deleted {drafts_count} drafts")
            
            # 6. Delete players
            logger.info("Deleting players...")
            players_count = session.query(Player).count()
            session.query(Player).delete()
            deleted_counts['players'] = players_count
            logger.info(f"✓ Deleted {players_count} players")
            
            # 7. Delete player pools
            logger.info("Deleting player pools...")
            player_pools_count = session.query(PlayerPool).count()
            session.query(PlayerPool).delete()
            deleted_counts['player_pools'] = player_pools_count
            logger.info(f"✓ Deleted {player_pools_count} player pools")
            
            # Commit all deletions
            session.commit()
            logger.info("✓ All deletions committed successfully")
        
        logger.info("=" * 80)
        logger.info("DATABASE CLEANUP COMPLETED")
        logger.info("=" * 80)
        
        total_deleted = sum(deleted_counts.values())
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Database cleaned successfully",
                "deleted_counts": deleted_counts,
                "total_records_deleted": total_deleted,
                "next_steps": [
                    "Next draft creation will fetch fresh 2025 season players from MLB Stats API",
                    "A new player pool will be created automatically",
                    "New teams will be initialized",
                    "All data will be fresh"
                ]
            }
        )
        
    except Exception as e:
        logger.error(f"✗ Error during database cleanup: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database cleanup failed: {str(e)}"
        )


@router.get("/admin/database-stats")
async def get_database_stats():
    """
    Get current database statistics without deleting anything.
    
    Returns counts of all records in the database.
    Useful for checking what will be deleted before cleanup.
    
    Returns:
        JSON response with counts of all database records
    """
    try:
        from backend.data.postgresql.connection import DatabaseSession
        from backend.data.postgresql.models import (
            Draft, 
            DraftHistory, 
            DraftTeam, 
            Player, 
            PlayerPool, 
            Team,
            DraftTask
        )
        
        stats = {}
        
        with DatabaseSession() as session:
            stats['drafts'] = session.query(Draft).count()
            stats['draft_history'] = session.query(DraftHistory).count()
            stats['draft_teams'] = session.query(DraftTeam).count()
            stats['teams'] = session.query(Team).count()
            stats['players'] = session.query(Player).count()
            stats['player_pools'] = session.query(PlayerPool).count()
            stats['draft_tasks'] = session.query(DraftTask).count()
        
        total_records = sum(stats.values())
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "database": "PostgreSQL RDS",
                "record_counts": stats,
                "total_records": total_records
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching database stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch database stats: {str(e)}"
        )