import { useState } from 'react';
import researchService from '../services/researchService';

export const useResearch = () => {
  const [researching, setResearching] = useState(false);
  const [error, setError] = useState('');

  const generateResearch = async () => {
    try {
      setResearching(true);
      setError('');
      const result = await researchService.generateResearch();
      return result;
    } catch (err) {
      setError(`Failed to generate research: ${err.message}`);
      throw err;
    } finally {
      setResearching(false);
    }
  };

  return {
    researching,
    error,
    generateResearch
  };
};