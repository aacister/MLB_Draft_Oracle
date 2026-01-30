import React from 'react';
import { RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';
import CreateDraftButton from './CreateDraftButton';
import ResearchButton from './ResearchButton';
import DraftStatusTracker from './DraftStatusTracker';
import AppNoteComponent from '../common/AppNote';

const Header = ({ 
  onRefresh, 
  onCreateDraft,
  onResearch,
  loading, 
  creatingDraft,
  researching,
  draftStatus, 
  playerPoolLoaded,
  isDraftRunning = false
}) => {
  const isStatusActive = draftStatus && !draftStatus.includes('complete') && !draftStatus.includes('Error') && !draftStatus.includes('stopped');
  
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col space-y-4 py-4">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">MLB Draft Oracle</h1>
              <div className="flex items-center gap-3 mt-1">
                {playerPoolLoaded && (
                  <div className="flex items-center text-xs text-green-600">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Player pool loaded
                  </div>
                )}
                {isStatusActive && (
                  <div className="flex items-center text-xs text-blue-600 animate-pulse">
                    <AlertCircle className="w-3 h-3 mr-1" />
                    Draft in progress
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-col mt-0">
              <AppNoteComponent />
              {draftStatus && (
                <DraftStatusTracker draftStatus={draftStatus} />
              )}
            </div>

            <div className="flex gap-2">
       {/*       <ResearchButton
                onClick={onResearch}
                loading={researching}
                disabled={isDraftRunning}
              />
*/}
              <CreateDraftButton
                onClick={onCreateDraft}
                loading={creatingDraft}
                disabled={isDraftRunning}
              />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;