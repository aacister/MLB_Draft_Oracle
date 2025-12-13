import React from 'react';
import { RefreshCw } from 'lucide-react';
import CreateDraftButton from './CreateDraftButton';
import DraftStatusTracker from './DraftStatusTracker';
import AppNoteComponent from '../common/AppNote';

const Header = ({ onRefresh, onCreateDraft, loading, creatingDraft, draftStatus }) => {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="flex flex-col space-y-4 py-4">
        {/* Top row: Title and Create Draft Button */}
        <div className="flex justify-between ">
          <h1 className="text-2xl font-bold text-gray-900 mt-0">MLB Draft Oracle</h1>

          <div className="flex flex-col  mt-0">
              <AppNoteComponent />
              {draftStatus && (
              <DraftStatusTracker draftStatus={draftStatus} />
            )}
          </div>
        

          <CreateDraftButton className="mt-0"
            onClick={onCreateDraft}
            loading={creatingDraft}
          />
        </div>
     
        
      </div>
    </div>
  </header>
  );
};
export default Header;
