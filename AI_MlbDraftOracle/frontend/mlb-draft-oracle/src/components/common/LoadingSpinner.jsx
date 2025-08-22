import React from 'react';
import { Clock } from 'lucide-react';

const LoadingSpinner = () => (
  <div className="flex items-center justify-center min-h-screen bg-gray-100">
    <div className="text-center">
      <Clock className="w-12 h-12 animate-spin mx-auto mb-4 text-blue-600" />
      <p className="text-gray-600">Loading draft data...</p>
    </div>
  </div>
);

export default LoadingSpinner;