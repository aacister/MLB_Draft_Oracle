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
      
      console.log(`Starting async draft for ${team_name} at R${round_num} P${current_pick}`);
      
      // Step 1: Start the async draft (returns immediately)
      const startResult = await draftService.selectPlayerAsync(
        draft_id,
        team_name,
        round_num,
        current_pick
      );
      
      console.log('Draft pick started:', startResult);
      
      // Step 2: Poll for completion using draft history
      const status = await draftService.waitForPickCompletion(
        draft_id,
        round_num,
        current_pick,
        120,  // maxAttempts (4 minutes total)
        2000  // pollInterval (2 seconds)
      );
      
      console.log('Draft pick completed:', status);
      return status;
      
    } catch (err) {
      setError(`Failed to draft player: ${err.message}`);
      throw err;
    }
  };

  const draftPlayer = async (draft_id, team_name, round_num, current_pick) => {
    /**
     * DEPRECATED: This uses the synchronous endpoint which will timeout
     * Use draftPlayerAsync instead
     */
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