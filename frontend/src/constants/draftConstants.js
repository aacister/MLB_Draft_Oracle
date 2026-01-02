const getApiBaseUrl = () => {
  return 'https://0ikbgoqbk7.execute-api.us-east-2.amazonaws.com';
  /*
    // Check if we're in Lambda environment (deployed to AWS)
    const deploymentEnv = import.meta.env.VITE_DEPLOYMENT_ENVIRONMENT;
    
    if (deploymentEnv === 'LAMBDA') {
        
      requestIdleCallback
    } else {
        return '';
    }
    */
};

export const API_BASE_URL = getApiBaseUrl();

export const POSITIONS = ['1B',  'C', 'OF', 'P'];

export const DRAFT_STATUS = {
  IN_PROGRESS: 'In Progress',
  COMPLETE: 'Complete'
};

export const TAB_CONFIG = [

  { id: 'history', label: 'Draft History', icon: 'History' },
  { id: 'teams', label: 'Team Rosters', icon: 'Users' },
  { id: 'draft', label: 'Draft Board', icon: 'List' }
];