import React from 'react';

const ErrorMessage = ({ error, onRetry }) => (
  <div className="flex items-center justify-center min-h-screen bg-gray-100">
    <div className="text-center text-red-600">
      <p>{error}</p>
      <button 
        onClick={onRetry}
        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Retry
      </button>
    </div>
  </div>
);

export default ErrorMessage;