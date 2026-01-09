import { useState, useEffect } from 'react';
import draftService from '../services/draftService';
import playerService from '../services/playerService';

export const useDrafts = () => {
  const [drafts, setDrafts] = useState([]);
  const [playerPool, setPlayerPool] = useState(null);
  const [loadingPlayerPool, setLoadingPlayerPool] = useState(true);
  const [loadingDrafts, setLoadingDrafts] = useState(false);
  const [error, setError] = useState('');
  const [initializationComplete, setInitializationComplete] = useState(false);

  const fetchDrafts = async () => {
    try {
      setLoadingDrafts(true);
      setError('');
      const data = await draftService.getAllDrafts();
      setDrafts(data);
    } catch (err) {
      setError(`Failed to load drafts: ${err.message}`);
    } finally {
      setLoadingDrafts(false);
    }
  };

  const initializePlayerPool = async () => {
    try {
      setLoadingPlayerPool(true);
      setError('');
      
      // Check if player pool exists in database
      const checkResult = await playerService.checkPlayerPool();
      
      if (checkResult.exists && checkResult.pool_id) {
        console.log('Player pool exists, loading...');
        // Load existing player pool
        const pool = await playerService.getPlayerPool(checkResult.pool_id);
        setPlayerPool(pool);
      } else {
        console.log('No player pool found, creating new one...');
        // Create new player pool
        const pool = await playerService.getPlayerPool();
        setPlayerPool(pool);
      }
      
      return true;
    } catch (err) {
      setError(`Failed to initialize player pool: ${err.message}`);
      return false;
    } finally {
      setLoadingPlayerPool(false);
    }
  };

  const createDraft = async () => {
    try {
      setError('');
      
      // Ensure player pool is loaded
      if (!playerPool) {
        throw new Error('Player pool not loaded');
      }
      
      const newDraft = await draftService.getDraft();
      await fetchDrafts();
      return newDraft;
    } catch (err) {
      setError(`Failed to create draft: ${err.message}`);
      throw err;
    }
  };

  const draftPlayerAsync = async (draft_id, team_name, round_num, current_pick) => {
    try {
      setError('');
      
      // Start the async draft
      const result = await draftService.selectPlayerAsync(
        draft_id,
        team_name,
        round_num,
        current_pick
      );
      
      console.log('Draft pick started:', result);
      
      // Poll for completion
      const pollInterval = 2000; // Poll every 2 seconds
      const maxAttempts = 60; // Maximum 2 minutes (60 * 2s)
      let attempts = 0;
      
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        
        const status = await draftService.getPickStatus(
          draft_id,
          round_num,
          current_pick
        );
        
        console.log(`Poll attempt ${attempts + 1}:`, status);
        
        if (status.status === 'completed') {
          console.log('Draft pick completed:', status.message);
          return status;
        }
        
        if (status.status === 'error') {
          throw new Error(status.error || 'Draft pick failed');
        }
        
        attempts++;
      }
      
      throw new Error('Draft pick timed out after 2 minutes');
      
    } catch (err) {
      setError(`Failed to draft player: ${err.message}`);
      throw err;
    }
  };

  const draftPlayer = async (draft_id, team_name, round_num, current_pick) => {
    try {
      setError('');
      await draftService.selectPlayer(draft_id, team_name, round_num, current_pick);
    } catch (err) {
      setError(`Failed to draft player: ${err.message}`);
      throw err;
    }
  };

  const resumeDraft = async (draft_id) => {
    try {
      setError('');
      const response = await draftService.resumeDraft(draft_id);
      return response;
    } catch (err) {
      setError(`Failed to resume draft: ${err.message}`);
      throw err;
    }
  };

  // Initialize on mount - sequence: player pool first, then drafts
  useEffect(() => {
    const initialize = async () => {
      const success = await initializePlayerPool();
      if (success) {
        await fetchDrafts();
      }
      setInitializationComplete(true);
    };
    
    initialize();
  }, []);

  return {
    drafts,
    playerPool,
    loadingPlayerPool,
    loadingDrafts,
    loading: loadingPlayerPool || loadingDrafts,
    error,
    initializationComplete,
    fetchDrafts,
    createDraft,
    draftPlayer,
    draftPlayerAsync,
    resumeDraft
  };
};