import React from 'react';
import { Clock, CheckCircle, Pause } from 'lucide-react';
import { getTeamForPick } from '../../utils/draftHelpers';

const DraftStatusBadge = ({ draft, isRunning = false, currentRound = null, currentPick = null }) => {
  // Draft is complete
  if (draft.is_complete) {
    return (
      <div className="flex items-center gap-1 text-xs text-green-600 mt-1">
        <CheckCircle className="w-3 h-3" />
        <span>Complete</span>
      </div>
    );
  }

  // Draft is running
  if (isRunning && currentRound && currentPick) {
    const draftingTeam = getTeamForPick(currentRound, currentPick, draft.draft_order || []);
    return (
      <div className="flex items-center gap-1 text-xs text-blue-600 mt-1 animate-pulse">
        <Clock className="w-3 h-3 animate-spin" />
        <span>R{currentRound} - {draftingTeam || 'Drafting...'}</span>
      </div>
    );
  }

  // Draft is paused/not running but not complete
  // Calculate next pick from draft history
  const completedPicks = draft.draft_history?.filter(h => h.selection).length || 0;
  const nextPick = completedPicks + 1;
  const numTeams = draft.draft_order?.length || 2;
  const nextRound = Math.ceil(nextPick / numTeams);
  
  if (nextPick <= draft.num_rounds * numTeams) {
    const nextTeam = getTeamForPick(nextRound, nextPick, draft.draft_order || []);
    return (
      <div className="flex items-center gap-1 text-xs text-gray-600 mt-1">
        <Pause className="w-3 h-3" />
        <span>Next: R{nextRound} - {nextTeam || 'TBD'}</span>
      </div>
    );
  }

  // Fallback
  return (
    <div className="flex items-center gap-1 text-xs text-gray-500 mt-1">
      <span>Ready</span>
    </div>
  );
};

export default DraftStatusBadge;