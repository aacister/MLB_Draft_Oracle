import { API_BASE_URL } from '../constants/draftConstants';

class PlayerService {
  async checkPlayerPool() {
    const url = `${API_BASE_URL}/v1/player-pool/check`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to check player pool: ${response.statusText}`);
    }

    return await response.json();
  }

  async getPlayerPool(poolId = null) {
    const url = poolId 
      ? `${API_BASE_URL}/v1/player-pools/${poolId}`
      : `${API_BASE_URL}/v1/player-pool`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch player pool: ${response.statusText}`);
    }

    return await response.json();
  }

  async getPlayer(playerId) {
    const url = `${API_BASE_URL}/v1/players/${playerId}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch player: ${response.statusText}`);
    }

    return await response.json();
  }
}

export default new PlayerService();