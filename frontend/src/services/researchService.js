import { API_BASE_URL } from '../constants/draftConstants';
class ResearchService {
    async generateResearch() {
      const url = `${API_BASE_URL}/v1/research`;
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      });
  
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to generate research: ${response.statusText} - ${errorText}`);
      }
  
      return await response.json();
    }
  }
  
  export default new ResearchService();