import { useState } from 'react';
import draftService  from '../services/draftService';

export const useDraftDetails = () => {
  const [selectedDraft, setSelectedDraft] = useState(null);
  const [draftData, setDraftData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchDraftDetails = async (draftId) => {
    try {
      setLoading(true);
      setError('');
      const data = await draftService.getDraft(draftId);
      setDraftData(data);
      setSelectedDraft(draftId);
    } catch (err) {
      setError(`Failed to load draft details: ${err.message}`);
      setDraftData(null);
      setSelectedDraft(null);
    } finally {
      setLoading(false);
    }
  };

  const clearSelection = () => {
    setSelectedDraft(null);
    setDraftData(null);
    setError('');
  };

  return {
    selectedDraft,
    draftData,
    loading,
    error,
    fetchDraftDetails,
    clearSelection
  };
};