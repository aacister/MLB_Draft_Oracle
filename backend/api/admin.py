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


@router.get("/admin/export-draft")
async def export_draft_data():
    """
    Export complete draft data for S3 archival.
    Called by StopDraftSite Lambda before cleanup.
    
    Returns:
        Complete draft data including picks, teams, strategies
    """
    logger.info("=" * 80)
    logger.info("EXPORT DRAFT DATA REQUESTED")
    logger.info("=" * 80)
    
    try:
        from backend.data.postgresql.unified_db import read_drafts
        from backend.models.draft_history import DraftHistory
        from backend.models.draft import Draft
        
        # Get all drafts (should be 1 active draft)
        drafts = read_drafts()
        
        if not drafts or len(drafts) == 0:
            logger.warning("No drafts found in database")
            raise HTTPException(status_code=404, detail="No draft found to export")
        
        # Get the most recent draft (last in list)
        latest_draft_data = drafts[-1]
        draft_id = latest_draft_data.get('id')
        
        logger.info(f"Exporting draft: {draft_id}")
        
        # Load full draft object
        draft = await Draft.get(draft_id)
        
        # Get draft history
        history = await DraftHistory.get(draft_id)
        
        # Format teams
        formatted_teams = []
        for team in draft.teams.teams:
            formatted_teams.append({
                'name': team.name,
                'strategy': team.strategy,
                'roster': {k: v.to_dict() if v else None for k, v in team.roster.items()},
                'total_picks': len([p for p in history.items if p.team == team.name and p.selection])
            })
        
        # Format picks
        formatted_picks = []
        for item in history.items:
            if item.selection:  # Only include completed picks
                formatted_picks.append({
                    'draft_id': draft_id,
                    'round': item.round,
                    'pick': item.pick,
                    'team': item.team,
                    'selection': item.selection,
                    'rationale': item.rationale
                })
        
        # Create export data
        export_data = {
            'draft_id': draft_id,
            'name': draft.name,
            'exported_at': str(datetime.utcnow()),
            'total_picks': len(formatted_picks),
            'total_rounds': draft.num_rounds,
            'is_complete': draft.is_complete,
            'teams': formatted_teams,
            'picks': formatted_picks
        }
        
        logger.info(f"✓ Exported {len(formatted_picks)} picks from draft {draft_id}")
        logger.info("=" * 80)
        
        return JSONResponse(
            status_code=200,
            content=export_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting draft data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export draft: {str(e)}"
        )


# Import datetime for export endpoint
from datetime import datetime