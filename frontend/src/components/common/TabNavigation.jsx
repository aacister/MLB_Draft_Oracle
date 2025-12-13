import React from 'react';

const TabNavigation = ({ tabs, activeTab, onTabChange }) => (
  
  <div className="bg-white border-b">
    <div className="max-w-7xl mx-auto px-4">
      <nav className="flex space-x-8">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  </div>
);

export default TabNavigation;