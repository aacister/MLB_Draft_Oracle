import React from 'react';
import { Plus } from 'lucide-react';

const CreateDraftButton = ({ onClick, loading = false, disabled = false }) => {
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className={`flex items-center h-8 px-2 py-2 border border-transparent text-sm rounded-sm shadow-sm text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
        loading || disabled
          ? 'bg-gray-400 cursor-not-allowed'
          : 'bg-blue-600 hover:bg-blue-700'
      }`}
      title={disabled ? "Another draft is already running" : ""}
    >
      <Plus className="h-4 w-4 mr-2" />
      {loading ? 'Drafting...' : 'Draft'}
    </button>
  );
};

export default CreateDraftButton;