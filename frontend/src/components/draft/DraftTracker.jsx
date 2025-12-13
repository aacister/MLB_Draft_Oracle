import React, { useState } from 'react';
import Header from './DraftsHeader';
import EmptyState from '../common/EmptyState';
import LoadingSpinner from '../common/LoadingSpinner';
import DraftsList from './DraftsList';
import DraftTabs from './DraftTabs';
import TeamsTab from './TeamsTab';
import HistoryTab from './HistoryTab';
import PlayersTab from './PlayersTab';
import DraftBoardTab from './DraftBoardTab';
import { useDrafts } from '../../hooks/useDrafts';
import { useDraftDetails } from '../../hooks/useDraftDetails';
import { TAB_CONFIG } from '../../constants/draftConstants';

const DraftTracker = () => {
  const [activeTab, setActiveTab] = useState('history');
  const [creatingDraft, setCreatingDraft] = useState(false);
  const [creatingPlayerPool, setCreatingPlayerPool] = useState(false);
  const [highlightedPlayerId, setHighlightedPlayerId] = useState(null);
  const [draftStatus, setDraftStatus] = useState('');
  
  const { 
    drafts, 
    loading: draftsLoading, 
    error: draftsError, 
    fetchDrafts, 
    createDraft,
    createPlayerPool,
    draftPlayer
  } = useDrafts();
  
  const {
    selectedDraft,
    draftData,
    loading: detailsLoading,
    error: detailsError,
    fetchDraftDetails
  } = useDraftDetails();

  const handleCreateDraft = async () => {
    try {
      setCreatingDraft(true);
      clearStatus();
      // Status 1: Creating draft
      updateStatus('Creating draft and pulling player pool...');
      const newDraft = await createDraft();
      await fetchDraftDetails(newDraft.draft_id);
      // Status 2: Draft created
      updateStatus(`Draft ${newDraft.name} created ...`);
      let current_pick = 1;
      for (let roundNum = 1; roundNum <= newDraft.num_rounds; roundNum++)
     {
        var draft_order = newDraft.draft_order;
        for(let team_name of draft_order)
        {
          // Status 3: Team drafting
            updateStatus(`${team_name} is drafting ...`);
            await draftPlayer(newDraft.draft_id, team_name, roundNum, current_pick);
            await fetchDraftDetails(newDraft.draft_id);
            current_pick++;
        }
     }
     await fetchDrafts(); 
     // Status 4: Draft complete
     updateStatus(`Draft ${newDraft.name} is complete`);
    } catch (err) {
      console.error('Failed to create draft:', err);
      updateStatus(`Error: ${err.message}`);
    } finally {
      setCreatingDraft(false);
    }
  };

  const handleDraftSelect = (draftId) => {
    if (draftId === selectedDraft) return;
    fetchDraftDetails(draftId);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'teams':
        return <TeamsTab teams={draftData?.teams} setHighlightedPlayerId={setHighlightedPlayerId} setActiveTab={setActiveTab} />;
      case 'history':
        return <HistoryTab draft_history={draftData?.draft_history} />;
     // case 'draft':
     //   return <DraftBoardTab players={draftData?.player_pool?.players} />;
      case 'draft':
        return <PlayersTab players={draftData?.player_pool?.players} 
        highlightedPlayerId={highlightedPlayerId}
        setHighlightedPlayerId={setHighlightedPlayerId}
        draftHistory={draftData?.draft_history}
        />;
      default:
        return <div>Select a tab</div>;
    }
  };

  const updateStatus = (status) => {
    setDraftStatus(status);

    // Auto-clear status after 20 seconds if draft is complete
    if (status.includes('is complete')) {
      setTimeout(() => {
        clearStatus();
      }, 20000);
    }

    if (status.includes('Error:')){
      setTimeout(() => {
        clearStatus();
      }, 40000);
    }
  };

  const clearStatus = () => {
    setDraftStatus('');
  };

  const error = draftsError || detailsError;

  return (
    <div className="min-h-screen bg-gray-100">
      <Header
        onRefresh={fetchDrafts}
        onCreateDraft={handleCreateDraft}
        loading={draftsLoading}
        creatingDraft={creatingDraft}
        draftStatus={draftStatus}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
       {/* <ErrorMessage error={error} /> */}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Drafts Grid */}
          <div className="lg:col-span-1">
            <DraftsList
              drafts={drafts}
              selectedDraft={selectedDraft}
              onDraftSelect={handleDraftSelect}
              loading={draftsLoading}
            />
          </div>

          {/* Draft Details */}
        
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow">
              <DraftTabs
                tabs={TAB_CONFIG}
                activeTab={activeTab}
                onTabChange={setActiveTab}
                disabled={!selectedDraft}
              />

              <div className="p-6">
                {!selectedDraft ? (
                  <EmptyState
                    title="No draft selected"
                    description="Select a draft from the list to view details"
                  />
                ) : detailsLoading ? (
                  <LoadingSpinner message="Loading draft details..." />
                ) : (
                  <div>
                    {draftData && (
                      <div className="mb-6">
                        <h2 className="text-xl font-bold text-gray-900">
                          {draftData.name}
                        </h2>
                        <p className="text-sm text-gray-600">
                          {draftData.num_rounds} rounds •
                          {draftData.is_complete ? ' Complete' : ' In Progress'}
                        </p>
                      </div>
                    )}
                    {renderTabContent()}
                  </div>
                )}
              </div>
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
};

export default DraftTracker;