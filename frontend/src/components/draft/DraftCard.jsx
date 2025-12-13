import React from 'react';
import { DRAFT_STATUS } from '../../constants/draftConstants';

const DraftCard = ({ draft, isSelected, onClick }) => {
  const handleClick = () => {
    onClick(draft.draft_id);
  };

  return (
    <div
      onClick={handleClick}
      className={`px-6 py-4 cursor-pointer transition-colors ${
        isSelected
          ? 'bg-blue-50 border-r-4 border-blue-500'
          : 'hover:bg-gray-50'
      }`}
    >
      <h3 className="text-sm font-medium text-gray-900">{draft.name}</h3>
      <p className="text-xs text-gray-500 mt-1">
        {draft.num_rounds} rounds • {draft.is_complete ? DRAFT_STATUS.COMPLETE : DRAFT_STATUS.IN_PROGRESS}
      </p>
    </div>
  );
};

export default DraftCard;