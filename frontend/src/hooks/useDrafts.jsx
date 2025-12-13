import { useState, useEffect } from 'react';
import draftService from '../services/draftService';
import playerService from '../services/playerService';

export const useDrafts = () => {
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchDrafts = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await draftService.getAllDrafts();
      setDrafts(data);
    } catch (err) {
      setError(`Failed to load drafts: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const createPlayerPool = async () => {
    try {
      setError('');
      return await playerService.getPlayerPool();
      
    }
    catch(err) {
      setError(`Failed to create player pool: ${err.message}`);
      throw err;
    }
  }

  const createDraft = async () => {
    try {
      setError('');
      const newDraft = await draftService.getDraft();
      await fetchDrafts(); // Refresh the list
      return newDraft;
    } catch (err) {
      setError(`Failed to create draft: ${err.message}`);
      throw err;
    } 
  };

  const draftPlayer = async (draft_id, team_name, round_num, current_pick) => {
    try{
      setError('');
      await draftService.selectPlayer(draft_id, team_name, round_num, current_pick);
    } catch (err) {
      setError(`Failed to draft player: ${err.message}`);
      throw err;
    }
  };

  useEffect(() => {
    fetchDrafts();
  }, []);

  return {
    drafts,
    loading,
    error,
    fetchDrafts,
    createDraft,
    createPlayerPool,
    draftPlayer
  };
};