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

  async selectPlayer(draftId, teamName, round, pick) {
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
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to resume draft: ${response.statusText}`);
    }

    return await response.json();
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