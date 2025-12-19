import React from 'react';
import { Clock, CheckCircle, Play } from 'lucide-react';
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

  // Draft is not complete and not running - show "In Progress"
  return (
    <div className="flex items-center gap-1 text-xs text-orange-600 mt-1">
      <Play className="w-3 h-3" />
      <span>In Progress</span>
    </div>
  );
};

export default DraftStatusBadge;