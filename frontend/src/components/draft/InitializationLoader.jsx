import React from 'react';
import { Clock, CheckCircle } from 'lucide-react';

const InitializationLoader = ({ loadingPlayerPool, loadingDrafts, playerPoolLoaded }) => {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="text-center bg-white rounded-lg shadow-lg p-8 max-w-md">
        <div className="space-y-6">
          {/* Player Pool Status */}
          <div className="flex items-center justify-between py-3 px-4 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              {loadingPlayerPool ? (
                <Clock className="w-5 h-5 animate-spin text-blue-600" />
              ) : (
                <CheckCircle className="w-5 h-5 text-green-600" />
              )}
              <span className={`text-sm font-medium ${
                loadingPlayerPool ? 'text-blue-600' : 'text-green-600'
              }`}>
                {loadingPlayerPool ? 'Loading player pool...' : 'Player pool loaded'}
              </span>
            </div>
          </div>

          {/* Drafts Status */}
          {playerPoolLoaded && (
            <div className="flex items-center justify-between py-3 px-4 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-3">
                {loadingDrafts ? (
                  <Clock className="w-5 h-5 animate-spin text-blue-600" />
                ) : (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                )}
                <span className={`text-sm font-medium ${
                  loadingDrafts ? 'text-blue-600' : 'text-green-600'
                }`}>
                  {loadingDrafts ? 'Loading drafts...' : 'Drafts loaded'}
                </span>
              </div>
            </div>
          )}

          {/* Progress Message */}
          <div className="text-xs text-gray-500 mt-4">
            {loadingPlayerPool && (
              <p>Initializing player database...</p>
            )}
            {!loadingPlayerPool && loadingDrafts && (
              <p>Loading your draft history...</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InitializationLoader;