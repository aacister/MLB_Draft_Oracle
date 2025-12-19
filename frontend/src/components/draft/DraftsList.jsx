import React from 'react';
import DraftCard from './DraftCard';
import LoadingSpinner from '../common/LoadingSpinner';
import EmptyState from '../common/EmptyState';

const DraftsList = ({ 
  drafts, 
  selectedDraft, 
  onDraftSelect, 
  onResume, 
  onStop,
  loading,
  runningDraftId = null,
  currentRound = null,
  currentPick = null
}) => {
  // Check if any draft is running
  const isDraftRunning = runningDraftId !== null;

  const renderContent = () => {
    if (loading && !drafts.length) {
      return <LoadingSpinner message="Loading drafts..." />;
    }

    if (!drafts.length) {
      return (
        <div className="px-6 py-4">
          <EmptyState 
            title="No drafts available"
            description="Create your first draft to get started"
          />
        </div>
      );
    }

    return (
      <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
        {drafts.map((draft) => {
          const isThisDraftRunning = runningDraftId === draft.draft_id;
          const shouldDisable = isDraftRunning && !isThisDraftRunning;
          
          return (
            <DraftCard
              key={draft.draft_id}
              draft={draft}
              isSelected={selectedDraft === draft.draft_id}
              onClick={onDraftSelect}
              onResume={onResume}
              onStop={onStop}
              isRunning={isThisDraftRunning}
              currentRound={isThisDraftRunning ? currentRound : null}
              currentPick={isThisDraftRunning ? currentPick : null}
              disabled={shouldDisable}
            />
          );
        })}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Drafts</h2>
        {isDraftRunning && (
          <p className="text-xs text-orange-600 mt-1">
            Other drafts disabled while one is running
          </p>
        )}
      </div>
      {renderContent()}
    </div>
  );
};

export default DraftsList;