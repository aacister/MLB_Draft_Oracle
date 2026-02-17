"""
backend/data/s3_history.py

S3 Draft History Archival Utility
Saves completed drafts to S3 for RAG indexing
"""

import json
import boto3
from datetime import datetime
from typing import Dict, List, Optional
import os
import logging

logger = logging.getLogger(__name__)

# S3 client
s3 = boto3.client('s3', region_name='us-east-2')

# Configuration
MEMORY_BUCKET = os.environ.get('S3_MEMORY_BUCKET', 'mlbdraftoracle-memory-425865275846')
DRAFT_HISTORY_PREFIX = 'source_data/historical_drafts/'


async def save_draft_to_s3(
    draft_id: str,
    draft_picks: List,
    teams: List,
    metadata: Optional[Dict] = None
) -> Dict:
    """
    Save current draft state to S3 for RAG indexing.
    Called after EVERY pick to provide real-time context to agents.
    
    Args:
        draft_id: Unique draft identifier
        draft_picks: List of DraftHistory items
        teams: List of Team objects
        metadata: Optional additional metadata
        
    Returns:
        Dict with S3 save result
    """
    
    logger.info(f"📦 Saving draft {draft_id} to S3 (incremental update)...")
    
    try:
        # 1. Format draft data
        draft_data = format_draft_for_rag(draft_id, draft_picks, teams, metadata)
        
        # 2. Use FIXED filename (overwrite on each pick for real-time updates)
        # This ensures agents always read the latest state
        s3_key = f"{DRAFT_HISTORY_PREFIX}{draft_id}_current.json"
        
        # 3. Upload to S3 (overwrites previous version)
        timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
        s3.put_object(
            Bucket=MEMORY_BUCKET,
            Key=s3_key,
            Body=json.dumps(draft_data, indent=2, default=str),
            ContentType='application/json',
            Metadata={
                'draft-id': draft_id,
                'last-updated': timestamp,
                'total-picks': str(draft_data.get('total_picks', 0)),
                'total-rounds': str(draft_data.get('total_rounds', 0)),
                'is-complete': str(draft_data.get('is_complete', False))
            }
        )
        
        s3_location = f"s3://{MEMORY_BUCKET}/{s3_key}"
        logger.info(f"✅ Draft state saved to: {s3_location}")
        logger.info(f"   Total picks: {draft_data.get('total_picks', 0)}")
        
        return {
            'success': True,
            'bucket': MEMORY_BUCKET,
            'key': s3_key,
            'location': s3_location,
            'total_picks': draft_data['total_picks']
        }
        
    except Exception as e:
        logger.error(f"❌ Error saving draft history to S3: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def format_draft_for_rag(
    draft_id: str,
    draft_picks: List,
    teams: List,
    metadata: Optional[Dict] = None
) -> Dict:
    """
    Format draft data for RAG indexing with position information.
    
    Args:
        draft_id: Draft identifier
        draft_picks: List of draft pick objects (DraftHistoryItem)
        teams: List of team objects
        metadata: Optional metadata
        
    Returns:
        Formatted draft data ready for S3 and RAG
    """
    
    # Build team strategy map and roster info
    team_strategies = {}
    formatted_teams = []
    
    for team in teams:
        # Handle both Team objects and dicts
        team_name = team.name if hasattr(team, 'name') else team.get('name')
        team_strategy = team.strategy if hasattr(team, 'strategy') else team.get('strategy')
        team_roster = team.roster if hasattr(team, 'roster') else team.get('roster', {})
        
        team_strategies[team_name] = team_strategy
        
        # Extract filled positions and needed positions
        filled_positions = []
        needed_positions = []
        
        if isinstance(team_roster, dict):
            for pos, player in team_roster.items():
                if player is not None:
                    filled_positions.append({
                        'position': pos,
                        'player': player.name if hasattr(player, 'name') else player.get('name', 'Unknown')
                    })
                else:
                    needed_positions.append(pos)
        
        formatted_teams.append({
            'name': team_name,
            'strategy': team_strategy,
            'filled_positions': filled_positions,
            'needed_positions': needed_positions,
            'roster_complete': len(needed_positions) == 0
        })
    
    # Format each pick with position information
    formatted_picks = []
    
    for pick in draft_picks:
        # Handle both DraftHistoryItem objects and dicts
        if hasattr(pick, 'round'):
            # It's a DraftHistoryItem object
            team_name = pick.team
            strategy = team_strategies.get(team_name, 'Unknown')
            player_name = pick.selection if pick.selection else None
            
            # Try to find position from team roster
            position = None
            team_obj = next((t for t in teams if (t.name if hasattr(t, 'name') else t.get('name')) == team_name), None)
            if team_obj and player_name:
                roster = team_obj.roster if hasattr(team_obj, 'roster') else team_obj.get('roster', {})
                # Find position by matching player name in roster
                if isinstance(roster, dict):
                    for pos, player in roster.items():
                        if player and (player.name if hasattr(player, 'name') else player.get('name')) == player_name:
                            position = pos
                            break
            
            formatted_pick = {
                'draft_id': draft_id,
                'round': pick.round,
                'pick': pick.pick,
                'team_name': team_name,
                'strategy': strategy,
                'player_name': player_name,
                'position': position,  # ✨ NEW: Position drafted
                'rationale': pick.rationale if pick.rationale else '',
                'timestamp': str(datetime.utcnow())
            }
        else:
            # It's a dict
            team_name = pick.get('team', pick.get('team_name'))
            strategy = team_strategies.get(team_name, 'Unknown')
            player_name = pick.get('selection', pick.get('player_name'))
            
            # Try to extract position from pick data
            position = pick.get('position')
            
            formatted_pick = {
                'draft_id': draft_id,
                'round': pick.get('round'),
                'pick': pick.get('pick'),
                'team_name': team_name,
                'strategy': strategy,
                'player_name': player_name,
                'position': position,  # ✨ NEW: Position drafted
                'rationale': pick.get('rationale', ''),
                'timestamp': str(datetime.utcnow())
            }
        
        # Only include picks that have been made (player_name exists)
        if player_name:
            formatted_picks.append(formatted_pick)
    
    # Calculate summary stats
    total_picks = len(formatted_picks)
    total_rounds = max([p['round'] for p in formatted_picks], default=0)
    completed_picks = len([p for p in formatted_picks if p['player_name']])
    
    # Compile draft summary
    draft_summary = {
        'draft_id': draft_id,
        'last_updated': datetime.utcnow().isoformat(),
        'total_picks': total_picks,
        'completed_picks': completed_picks,
        'total_rounds': total_rounds,
        'is_complete': metadata.get('is_complete', False) if metadata else False,
        'teams': formatted_teams,
        'picks': formatted_picks,
        'metadata': metadata or {}
    }
    
    return draft_summary