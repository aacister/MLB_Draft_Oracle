import React from 'react';
import { Plus } from 'lucide-react';

const CreateDraftButton = ({ onClick, loading = false }) => {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="flex items-center h-8  px-2 py-2 border border-transparent text-sm rounded-sm shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
    >
      <Plus className="h-4 w-4 mr-2" />
      {loading ? 'Drafting...' : 'Run Draft'}
    </button>
  );
};

export default CreateDraftButton;