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
        {drafts.map((draft) => (
          <DraftCard
            key={draft.draft_id}
            draft={draft}
            isSelected={selectedDraft === draft.draft_id}
            onClick={onDraftSelect}
            onResume={onResume}
            onStop={onStop}
            isRunning={runningDraftId === draft.draft_id}
            currentRound={runningDraftId === draft.draft_id ? currentRound : null}
            currentPick={runningDraftId === draft.draft_id ? currentPick : null}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Drafts</h2>
      </div>
      {renderContent()}
    </div>
  );
};

export default DraftsList;