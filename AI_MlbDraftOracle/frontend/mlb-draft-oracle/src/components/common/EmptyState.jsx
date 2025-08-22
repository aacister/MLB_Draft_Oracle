import React from 'react';
import { Trophy } from 'lucide-react';

const EmptyState = ({ 
  icon: Icon = Trophy, 
  title = "No data available", 
  description = "There's nothing to display at the moment",
  action = null 
}) => {
  return (
    <div className="text-center py-12">
      <Icon className="mx-auto h-12 w-12 text-gray-400" />
      <h3 className="mt-2 text-sm font-medium text-gray-900">{title}</h3>
      <p className="mt-1 text-sm text-gray-500">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
};

export default EmptyState;