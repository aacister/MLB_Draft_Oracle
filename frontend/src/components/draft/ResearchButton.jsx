import React from 'react';
import { Search } from 'lucide-react';

const ResearchButton = ({ onClick, loading = false, disabled = false }) => {
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className={`flex items-center h-8 px-2 py-2 border border-transparent text-sm rounded-sm shadow-sm text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 ${
        loading || disabled
          ? 'bg-gray-400 cursor-not-allowed'
          : 'bg-green-600 hover:bg-green-700'
      }`}
      title={disabled ? "Research disabled while draft is running" : "Generate research on trending MLB topics"}
    >
      <Search className="h-4 w-4 mr-2" />
      {loading ? 'Researching...' : 'Research'}
    </button>
  );
};

export default ResearchButton;