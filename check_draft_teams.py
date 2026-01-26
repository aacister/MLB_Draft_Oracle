
#!/usr/bin/env python3
"""
Script to check what teams exist in a draft
"""
import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.models.draft import Draft
from dotenv import load_dotenv

load_dotenv()

async def check_draft_teams(draft_id: str):
    print(f"Checking draft: {draft_id}")
    print("=" * 60)
    
    try:
        # Load draft
        draft = await Draft.get(draft_id.lower())
        
        print(f"\nDraft ID: {draft.id}")
        print(f"Draft Name: {draft.name}")
        print(f"Number of Teams: {len(draft.teams.teams)}")
        print(f"Current Round: {draft.current_round}")
        print(f"Current Pick: {draft.current_pick}")
        print(f"Is Complete: {draft.is_complete}")
        
        print("\n" + "=" * 60)
        print("TEAMS IN DRAFT:")
        print("=" * 60)
        
        for i, team in enumerate(draft.teams.teams, 1):
            print(f"\n{i}. Team Name: {team.name}")
            print(f"   Strategy: {team.strategy[:80]}...")
            print(f"   Roster filled: {sum(1 for v in team.roster.values() if v is not None)}/{len(team.roster)}")
            print(f"   Players drafted: {len(team.drafted_players)}")
            
            if team.roster:
                print(f"   Roster:")
                for pos, player in team.roster.items():
                    if player:
                        print(f"     {pos}: {player.name}")
                    else:
                        print(f"     {pos}: [EMPTY]")
        
        print("\n" + "=" * 60)
        print("DRAFT ORDER FOR ROUND 3:")
        print("=" * 60)
        
        draft_order = draft.get_draft_order(3)
        for i, team in enumerate(draft_order, 1):
            pick_number = ((3 - 1) * len(draft.teams.teams)) + i
            print(f"Pick {pick_number}: {team.name}")
        
        print("\n" + "=" * 60)
        print("TEAM FOR PICK 6 (Round 3):")
        print("=" * 60)
        
        team_for_pick = draft.get_team_for_pick(3, 6)
        print(f"Team that should draft at R3, P6: {team_for_pick.name}")
        
        print("\n✓ Draft loaded successfully!")
        
    except Exception as e:
        print(f"\n✗ Error loading draft: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    draft_id = sys.argv[1] if len(sys.argv) > 1 else "63e5a3b0-a9c6-4051-b14d-2e222adc6979"
    asyncio.run(check_draft_teams(draft_id))