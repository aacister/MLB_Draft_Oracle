import React from 'react';
import { Play, Square } from 'lucide-react';
import DraftStatusBadge from './DraftStatusBadge';

const DraftCard = ({ 
  draft, 
  isSelected, 
  onClick, 
  onResume, 
  onStop, 
  isRunning = false,
  currentRound = null,
  currentPick = null
}) => {
  const handleClick = (e) => {
    if (e.target.closest('.action-button')) {
      return; // Don't trigger selection when clicking action buttons
    }
    onClick(draft.draft_id);
  };

  const handleResume = (e) => {
    e.stopPropagation();
    onResume(draft.draft_id);
  };

  const handleStop = (e) => {
    e.stopPropagation();
    onStop(draft.draft_id);
  };

  const canResume = !draft.is_complete && !isRunning;
  const canStop = isRunning;

  return (
    <div
      onClick={handleClick}
      className={`px-6 py-4 cursor-pointer transition-colors ${
        isSelected
          ? 'bg-blue-50 border-r-4 border-blue-500'
          : 'hover:bg-gray-50'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 truncate">{draft.name}</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {draft.num_rounds} rounds
          </p>
          <DraftStatusBadge 
            draft={draft} 
            isRunning={isRunning}
            currentRound={currentRound}
            currentPick={currentPick}
          />
        </div>
        
        <div className="flex items-center gap-1 ml-2">
          {canResume && (
            <button
              onClick={handleResume}
              className="action-button p-1.5 text-green-600 hover:bg-green-100 rounded transition-colors"
              title="Resume draft"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          {canStop && (
            <button
              onClick={handleStop}
              className="action-button p-1.5 text-red-600 hover:bg-red-100 rounded transition-colors"
              title="Stop draft"
            >
              <Square className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default DraftCard;