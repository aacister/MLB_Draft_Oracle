import React, { useState, useRef } from 'react';
import Header from './DraftsHeader';
import EmptyState from '../common/EmptyState';
import LoadingSpinner from '../common/LoadingSpinner';
import InitializationLoader from './InitializationLoader';
import DraftsList from './DraftsList';
import DraftTabs from './DraftTabs';
import TeamsTab from './TeamsTab';
import HistoryTab from './HistoryTab';
import PlayersTab from './PlayersTab';
import { useDrafts } from '../../hooks/useDrafts';
import { useDraftDetails } from '../../hooks/useDraftDetails';
import { TAB_CONFIG } from '../../constants/draftConstants';
import { getTeamForPick } from '../../utils/draftHelpers';

const DraftTracker = () => {
  const [activeTab, setActiveTab] = useState('history');
  const [creatingDraft, setCreatingDraft] = useState(false);
  const [highlightedPlayerId, setHighlightedPlayerId] = useState(null);
  const [draftStatus, setDraftStatus] = useState('');
  const [runningDraftId, setRunningDraftId] = useState(null);
  const [currentRound, setCurrentRound] = useState(null);
  const [currentPick, setCurrentPick] = useState(null);
  const stopDraftRef = useRef(false);
  
  const { 
    drafts, 
    playerPool,
    loadingPlayerPool,
    loadingDrafts,
    error: draftsError, 
    initializationComplete,
    fetchDrafts, 
    createDraft,
    draftPlayer,
    resumeDraft
  } = useDrafts();
  
  const {
    selectedDraft,
    draftData,
    loading: detailsLoading,
    error: detailsError,
    fetchDraftDetails
  } = useDraftDetails();

  const runDraftPicks = async (draft, startRound, startPick) => {
    const numTeams = draft.draft_order.length;
    let current_pick = startPick;
    
    // Set running state
    setRunningDraftId(draft.draft_id);
    
    try {
      for (let roundNum = startRound; roundNum <= draft.num_rounds; roundNum++) {
        // Check if stop was requested
        if (stopDraftRef.current) {
          updateStatus(`Draft stopped at Round ${roundNum}, Pick ${current_pick}`);
          return;
        }
        
        const picksInRound = numTeams;
        const firstPickOfRound = ((roundNum - 1) * picksInRound) + 1;
        const lastPickOfRound = roundNum * picksInRound;
        
        for (let pickNum = Math.max(current_pick, firstPickOfRound); pickNum <= lastPickOfRound; pickNum++) {
          // Check if stop was requested
          if (stopDraftRef.current) {
            updateStatus(`Draft stopped at Round ${roundNum}, Pick ${pickNum}`);
            return;
          }
          
          const team_name = getTeamForPick(roundNum, pickNum, draft.draft_order);
          
          // Update current pick state for UI
          setCurrentRound(roundNum);
          setCurrentPick(pickNum);
          
          console.log(`Round ${roundNum}, Pick ${pickNum}: ${team_name} drafting (Pick index: ${pickNum - firstPickOfRound})`);
          updateStatus(`Round ${roundNum}, Pick ${pickNum}: ${team_name} is drafting ...`);
          
          try {
            await draftPlayer(draft.draft_id, team_name, roundNum, pickNum);
            await fetchDraftDetails(draft.draft_id);
          } catch (error) {
            console.error(`Error drafting for ${team_name}:`, error);
            updateStatus(`Error: ${error.message}`);
            throw error;
          }
          
          current_pick = pickNum + 1;
        }
      }
    } finally {
      // Clear running state
      setRunningDraftId(null);
      setCurrentRound(null);
      setCurrentPick(null);
    }
  };

  const handleCreateDraft = async () => {
    try {
      setCreatingDraft(true);
      stopDraftRef.current = false;
      clearStatus();
      
      updateStatus('Creating draft...');
      const newDraft = await createDraft();
      await fetchDraftDetails(newDraft.draft_id);
      
      updateStatus(`Draft ${newDraft.name} created ...`);
      await runDraftPicks(newDraft, 1, 1);
      
      await fetchDrafts();
      
      if (!stopDraftRef.current) {
        updateStatus(`Draft ${newDraft.name} is complete`);
      }
    } catch (err) {
      console.error('Failed to create draft:', err);
      updateStatus(`Error: ${err.message}`);
    } finally {
      setCreatingDraft(false);
      stopDraftRef.current = false;
    }
  };

  const handleResumeDraft = async (draftId) => {
    try {
      setCreatingDraft(true);
      stopDraftRef.current = false;
      clearStatus();
      
      updateStatus('Resuming draft...');
      
      await fetchDraftDetails(draftId);
      
      if (!draftData) {
        throw new Error('Failed to load draft details');
      }
      
      const resumeInfo = await resumeDraft(draftId);
      
      updateStatus(`Resuming ${draftData.name} from Round ${resumeInfo.current_round}, Pick ${resumeInfo.current_pick}...`);
      
      const nextTeam = getTeamForPick(resumeInfo.current_round, resumeInfo.current_pick, draftData.draft_order);
      
      console.log('=== Resume Draft Debug ===');
      console.log('Resume Info:', {
        round: resumeInfo.current_round,
        pick: resumeInfo.current_pick,
        nextTeam: nextTeam,
        draftOrder: draftData.draft_order,
        numTeams: draftData.draft_order.length
      });
      console.log('========================');
      
      await runDraftPicks(draftData, resumeInfo.current_round, resumeInfo.current_pick);
      
      await fetchDrafts();
      
      if (!stopDraftRef.current) {
        updateStatus(`Draft ${draftData.name} is complete`);
      }
    } catch (err) {
      console.error('Failed to resume draft:', err);
      updateStatus(`Error: ${err.message}`);
    } finally {
      setCreatingDraft(false);
      stopDraftRef.current = false;
    }
  };

  const handleStopDraft = (draftId) => {
    console.log(`Stopping draft: ${draftId}`);
    stopDraftRef.current = true;
    updateStatus('Stopping draft...');
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
      case 'draft':
        return <PlayersTab 
          players={draftData?.player_pool?.players} 
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

    if (status.includes('is complete') || status.includes('stopped')) {
      setTimeout(() => {
        clearStatus();
      }, 20000);
    }

    if (status.includes('Error:')) {
      setTimeout(() => {
        clearStatus();
      }, 40000);
    }
  };

  const clearStatus = () => {
    setDraftStatus('');
  };

  const error = draftsError || detailsError;

  if (!initializationComplete) {
    return (
      <InitializationLoader 
        loadingPlayerPool={loadingPlayerPool}
        loadingDrafts={loadingDrafts}
        playerPoolLoaded={!!playerPool}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Header
        onRefresh={fetchDrafts}
        onCreateDraft={handleCreateDraft}
        loading={loadingDrafts}
        creatingDraft={creatingDraft}
        draftStatus={draftStatus}
        playerPoolLoaded={!!playerPool}
        isDraftRunning={runningDraftId !== null}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <DraftsList
              drafts={drafts}
              selectedDraft={selectedDraft}
              onDraftSelect={handleDraftSelect}
              onResume={handleResumeDraft}
              onStop={handleStopDraft}
              loading={loadingDrafts}
              runningDraftId={runningDraftId}
              currentRound={currentRound}
              currentPick={currentPick}
            />
          </div>

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