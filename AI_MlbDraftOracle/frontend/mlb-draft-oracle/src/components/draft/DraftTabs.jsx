import React from 'react';
import { Users, Trophy, Clock, BarChart3, History, List, PersonStanding } from 'lucide-react';

const iconMap = {
    List,
    History,
  Users,
  PersonStanding,
  //Trophy,
 // Clock,
 // BarChart3
};

const DraftTabs = ({ tabs, activeTab, onTabChange, disabled = false }) => {
  return (
    <div className="border-b border-gray-200">
      <nav className="-mb-px flex space-x-8 px-6">
        {tabs.map((tab) => {
          const Icon = iconMap[tab.icon];
          const isActive = activeTab === tab.id && !disabled;
          
          return (
            <button
              key={tab.id}
              onClick={() => !disabled && onTabChange(tab.id)}
              disabled={disabled}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center transition-colors ${
                isActive
                  ? 'border-blue-500 text-blue-600'
                  : disabled
                  ? 'border-transparent text-gray-400 cursor-not-allowed'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon className="h-4 w-4 mr-2" />
              {tab.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
};

export default DraftTabs;