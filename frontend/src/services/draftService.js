import { API_BASE_URL } from '../constants/draftConstants';

class DraftService {
  async getDraft(draftId = null) {
    const url = draftId 
      ? `${API_BASE_URL}/v1/drafts/${draftId}`
      : `${API_BASE_URL}/v1/draft`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': '*/*',
        'Content-Type': 'application/json', 
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch draft: ${response.statusText}`);
    }
    return await response.json();
  }

  async getAllDrafts() {
    const url = `${API_BASE_URL}/v1/drafts`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': '*/*',
        'Content-Type': 'application/json', 
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch drafts: ${response.statusText}`);
    }
    return await response.json();
  }

  async selectPlayerAsync(draftId, teamName, round, pick) {
    /**
     *  CORRECT: Calls the API Gateway endpoint that invokes worker Lambda
     * The main Lambda (mlb-draft-oracle) handles the request and invokes
     * the worker Lambda (mlb-draft-oracle-worker) asynchronously
     */
    const url = `${API_BASE_URL}/v1/drafts/${draftId}/teams/${encodeURIComponent(teamName)}/round/${round}/pick/${pick}/select-player-async`;
    
    console.log(`[Frontend] Starting async draft pick: ${url}`);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to start player selection: ${response.statusText} - ${errorText}`);
    }

    const result = await response.json();
    console.log('[Frontend] Draft pick started:', result);
    
    return result;
  }

  async getPickStatus(draftId, round, pick) {
    /**
     *  CORRECT: This endpoint checks the draft history in PostgreSQL
     * to see if the pick has been completed by the worker Lambda
     */
    const url = `${API_BASE_URL}/v1/drafts/${draftId}/round/${round}/pick/${pick}/status`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.warn(`[Frontend] Failed to get pick status: ${response.statusText} - ${errorText}`);
      
      // Don't throw - return a default status so polling can continue
      return {
        status: 'processing',
        message: 'Checking pick status...',
        current_round: round,
        current_pick: pick
      };
    }

    return await response.json();
  }

  async waitForPickCompletion(draftId, round, pick, maxAttempts = 120, pollInterval = 2000) {
    /**
     * ✅ IMPROVED: Poll until pick is completed or timeout
     * - maxAttempts: 120 attempts (default 4 minutes total)
     * - pollInterval: 2000ms (2 seconds between checks)
     * - Provides detailed logging for debugging
     */
    console.log(`[Frontend] Waiting for pick completion: R${round} P${pick}`);
    console.log(`[Frontend] Max wait time: ${(maxAttempts * pollInterval / 1000)} seconds`);
    
    const startTime = Date.now();
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      // Wait before checking
      await new Promise(resolve => setTimeout(resolve, pollInterval));
      
      const elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
      
      try {
        const status = await this.getPickStatus(draftId, round, pick);
        
        console.log(`[Frontend] Poll attempt ${attempt + 1}/${maxAttempts} (${elapsedSeconds}s elapsed):`, status);
        
        // Check for completion
        if (status.status === 'completed') {
          console.log(`[Frontend] ✓ Pick completed after ${elapsedSeconds}s: ${status.player_name || status.message}`);
          return status;
        }
        
        // Check for error
        if (status.status === 'error') {
          console.error(`[Frontend] ✗ Pick failed after ${elapsedSeconds}s:`, status.error || status.message);
          throw new Error(status.error || status.message || 'Draft pick failed');
        }
        
        // Status is 'processing' or 'not_found' - continue polling
        if (attempt > 0 && attempt % 10 === 0) {
          console.log(`[Frontend] Still waiting... (${attempt}/${maxAttempts} attempts)`);
        }
        
      } catch (error) {
        console.error(`[Frontend] Error checking pick status (attempt ${attempt + 1}):`, error);
        
        // If we're near the end of attempts, throw the error
        if (attempt >= maxAttempts - 5) {
          throw error;
        }
        
        // Otherwise, continue polling - the status endpoint might be temporarily unavailable
        console.log('[Frontend] Continuing to poll despite error...');
      }
    }
    
    const totalTime = Math.floor((Date.now() - startTime) / 1000);
    throw new Error(`Draft pick timed out after ${totalTime} seconds (${maxAttempts} attempts)`);
  }

  async cleanupDraftTasks(draftId) {

    const url = `${API_BASE_URL}/v1/drafts/${draftId}/tasks/cleanup`;
    
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.warn(`[Frontend] Failed to cleanup tasks: ${response.statusText}`);
      // Don't throw - cleanup is optional
      return { message: 'Cleanup skipped' };
    }

    return await response.json();
  }

  async selectPlayer(draftId, teamName, round, pick) {
    /**
     *  DEPRECATED: This synchronous endpoint will timeout
     * Use selectPlayerAsync + waitForPickCompletion instead
     */
    console.warn('[Frontend] WARNING: Using deprecated synchronous selectPlayer endpoint');
    
    const url = `${API_BASE_URL}/v1/drafts/${draftId}/teams/${encodeURIComponent(teamName)}/round/${round}/pick/${pick}/select-player`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to select player: ${response.statusText}`);
    }

    return await response.json();
  }

  async resumeDraft(draftId) {

    const url = `${API_BASE_URL}/v1/drafts/${draftId}/resume`;
    
    console.log(`[Frontend] Resuming draft: ${draftId}`);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to resume draft: ${response.statusText} - ${errorText}`);
    }

    const result = await response.json();
    console.log('[Frontend] Draft resume info:', result);
    
    return result;
  }

  async getDraftHistory(draftId) {

    const url = `${API_BASE_URL}/v1/draft-history/${draftId}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch draft history: ${response.statusText}`);
    }

    return await response.json();
  }

  async getTeam(draftId, teamName) {

    const url = `${API_BASE_URL}/v1/drafts/${draftId}/teams/${encodeURIComponent(teamName)}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch team: ${response.statusText}`);
    }

    return await response.json();
  }
}

export default new DraftService();